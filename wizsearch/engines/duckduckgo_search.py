import asyncio
import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import override

from ..base import BaseSearch, SearchResult, SourceItem, get_proxy_from_env

try:
    from ddgs import DDGS
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import DDGS: {e}")
    raise ImportError("ddgs library not found. Please install it with: pip install ddgs") from e

logger = logging.getLogger(__name__)


class DuckDuckGoSearchError(Exception):
    """Custom exception for DuckDuckGo Search wrapper errors."""


class DuckDuckGoSearchConfig(BaseModel):
    """Configuration for DuckDuckGo Search wrapper."""

    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    region: str = Field(default="us-en", description="Region for search (e.g., us-en, uk-en, etc.)")
    safesearch: str = Field(default="moderate", pattern="^(on|moderate|off)$", description="Safe search setting")
    timelimit: Optional[str] = Field(None, description="Time limit for search (d, w, m, y)")
    backend: str = Field(default="auto", description="Backend to use for search")
    proxy: Optional[str] = Field(None, description="Proxy to use for requests")
    timeout: int = Field(default=5, ge=1, le=30, description="Request timeout in seconds")

    model_config = ConfigDict(extra="forbid")


class DuckDuckGoSearch(BaseSearch):
    """
    Production-level wrapper for DuckDuckGo Search using DDGS library.

    This class provides a robust interface to DuckDuckGo Search with:
    - Comprehensive error handling and logging
    - Configuration management
    - Response validation and processing
    - Integration with existing search infrastructure
    - Performance monitoring and metrics
    """

    def __init__(self, config: Optional[DuckDuckGoSearchConfig] = None, **kwargs):
        """
        Initialize the DuckDuckGo Search wrapper.

        Args:
            config: Configuration object for the search wrapper
            **kwargs: Additional configuration parameters
        """
        # Initialize configuration
        if config is None:
            config = DuckDuckGoSearchConfig()

        # Override config with kwargs if provided
        if kwargs:
            config = config.model_copy(update=kwargs)

        # Resolve proxy: env vars take priority over explicit config value
        resolved_proxy = get_proxy_from_env(config.proxy)
        if resolved_proxy != config.proxy:
            config = config.model_copy(update={"proxy": resolved_proxy})

        self.config = config
        self._search_client = None
        self._initialize_search_client()

    def _initialize_search_client(self) -> None:
        """Initialize the DDGS search client."""
        try:
            self._search_client = DDGS(proxy=self.config.proxy, timeout=self.config.timeout, verify=True)
            logger.debug("DuckDuckGo search client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DuckDuckGo search client: {e}")
            raise DuckDuckGoSearchError(f"Failed to initialize DuckDuckGo search client: {e}")

    def _transform_results(self, query: str, raw_results: list, response_time: float) -> SearchResult:
        """
        Transform DDGS results to SearchResult format.

        Args:
            query: Original search query
            raw_results: Raw results from DDGS
            response_time: Time taken for the search

        Returns:
            SearchResult object
        """
        sources = []
        for i, result in enumerate(raw_results):
            # Convert rank to a score between 0 and 1
            # Higher rank (lower number) should have higher score
            # Use a simple inverse ranking: score = 1 / (rank + 1)
            # This ensures score is between 0 and 1, with rank 0 getting score 1.0
            score = 1.0 / (i + 1)

            source_item = SourceItem(
                url=result.get("href", ""),
                title=result.get("title", ""),
                content=result.get("body"),
                score=score,
                raw_content=None,
            )
            sources.append(source_item)

        return SearchResult(
            query=query,
            answer=None,  # DuckDuckGo doesn't provide AI-generated answers
            images=[],  # Text search doesn't include images
            sources=sources,
            response_time=response_time,
            raw_response=raw_results,
        )

    def _search_internal(self, query: str, **kwargs) -> SearchResult:
        """
        Perform a search using DuckDuckGo.

        Args:
            query: Search query string
            **kwargs: Additional search parameters that override config

        Returns:
            SearchResult object with search results

        Raises:
            DuckDuckGoSearchError: If search fails or response is invalid
        """
        if not query or not query.strip():
            raise DuckDuckGoSearchError("Search query cannot be empty")

        try:
            start_time = datetime.now()
            query = query.strip()

            # Merge config with kwargs for this search
            search_params = {
                "region": kwargs.get("region", self.config.region),
                "safesearch": kwargs.get("safesearch", self.config.safesearch),
                "timelimit": kwargs.get("timelimit", self.config.timelimit),
                "max_results": kwargs.get("max_results", self.config.max_results),
                "backend": kwargs.get("backend", self.config.backend),
            }

            # Remove None values
            search_params = {k: v for k, v in search_params.items() if v is not None}

            raw_results = self._search_client.text(query, **search_params)

            response_time = (datetime.now() - start_time).total_seconds()

            result = self._transform_results(query, raw_results, response_time)
            logger.info(
                f"DuckDuckGo search completed in {response_time:.2f} seconds, {len(result.sources)} results found"
            )
            return result

        except Exception as e:
            logger.error(f"DuckDuckGo search failed for query '{query}': {e}")
            raise DuckDuckGoSearchError(f"Search failed: {e}")

    @override
    async def search(self, query: str, **kwargs) -> SearchResult:
        """
        Perform an async search using DuckDuckGo.

        Args:
            query: Search query string
            **kwargs: Additional search parameters that override config

        Returns:
            SearchResult object with search results

        Raises:
            DuckDuckGoSearchError: If search fails or response is invalid
        """
        if not query or not query.strip():
            raise DuckDuckGoSearchError("Search query cannot be empty")

        try:
            start_time = datetime.now()
            query = query.strip()

            # Perform search in a thread pool to avoid blocking
            logger.info(f"Performing DuckDuckGo search for query: {query}")
            loop = asyncio.get_event_loop()

            # Create a partial function with kwargs to pass to run_in_executor
            from functools import partial

            search_func = partial(self._search_internal, query, **kwargs)
            result = await loop.run_in_executor(None, search_func)

            response_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"DuckDuckGo search completed in {response_time:.2f} seconds")
            return result

        except Exception as e:
            logger.error(f"DuckDuckGo search failed for query '{query}': {e}")
            raise DuckDuckGoSearchError(f"Search failed: {e}")

    def get_config(self) -> dict:
        """
        Get the current configuration of the search engine.

        Returns:
            dict: Current configuration parameters
        """
        return self.config.model_dump()
