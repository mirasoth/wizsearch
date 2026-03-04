import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import aiohttp
import dotenv
import requests
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import override

from ..base import BaseSearch, SearchResult, SourceItem, get_proxy_from_env

dotenv.load_dotenv()

logger = logging.getLogger(__file__)


def _get_default_params() -> dict:
    """Get default parameters for SearxNG API requests."""
    return {"language": "en", "format": "json"}


class SearxNGResults(dict):
    """Dict-like wrapper around SearxNG API results."""

    _data: str = ""

    def __init__(self, data: str):
        """Take a raw result from SearxNG and make it into a dict-like object."""
        json_data = json.loads(data)
        super().__init__(json_data)
        self.__dict__ = self

    def __str__(self) -> str:
        """Text representation of SearxNG result."""
        return self._data

    @property
    def results(self) -> Any:
        """Silence mypy for accessing this field."""
        return self.get("results", [])

    @property
    def answers(self) -> Any:
        """Helper accessor on the json result."""
        return self.get("answers", [])


class SearxNGSearchConfig(BaseModel):
    """Configuration for SearxNG Search."""

    searx_host: str = Field(
        default_factory=lambda: os.getenv("SEARX_HOST", ""),
        description="SearxNG host URL (e.g., 'http://localhost:8080')",
    )
    unsecure: bool = Field(default=False, description="Disable SSL verification")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Custom headers for requests")
    engines: Optional[List[str]] = Field(default_factory=list, description="List of engines to use for search")
    categories: Optional[List[str]] = Field(default_factory=list, description="List of categories to use for search")
    query_suffix: Optional[str] = Field(default="", description="Suffix to append to queries")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of results to return")
    timeout: int = Field(default=30, ge=1, le=60, description="Request timeout in seconds")
    proxy: Optional[str] = Field(
        default=None,
        description="Proxy URL (e.g., http://proxy:port). Falls back to HTTPS_PROXY/HTTP_PROXY env vars if not set.",
    )

    model_config = ConfigDict(extra="forbid")


class SearxNGSearchError(Exception):
    """Base exception for SearxNG Search errors."""


class SearxNGSearch(BaseSearch):
    """
    Production-level wrapper for SearxNG Search API.

    This class provides a robust interface to SearxNG with:
    - Comprehensive error handling and logging
    - Configuration management
    - Response validation and processing
    - Integration with existing search infrastructure
    - Performance monitoring and metrics
    """

    def __init__(self, config: Optional[SearxNGSearchConfig] = None, **kwargs):
        """
        Initialize the SearxNG Search wrapper.

        Args:
            config: Configuration object for the search wrapper
            **kwargs: Additional configuration parameters
        """
        # Initialize configuration
        if config is None:
            config = SearxNGSearchConfig()

        # Override config with kwargs if provided
        if kwargs:
            config = config.model_copy(update=kwargs)

        self.config = config
        self._validate_and_setup_config()
        # Resolve proxy: env vars take priority over explicit config value
        self._proxy = get_proxy_from_env(self.config.proxy)

    def _validate_and_setup_config(self) -> None:
        """Validate and setup the configuration."""
        if not self.config.searx_host:
            raise ValueError(
                "SearxNG host is required. Set SEARX_HOST environment variable or provide searx_host parameter."
            )

        # Ensure proper URL scheme
        if not self.config.searx_host.startswith("http"):
            logger.warning(f"Missing URL scheme on host, assuming secure https://{self.config.searx_host}")
            self.config.searx_host = "https://" + self.config.searx_host
        elif self.config.searx_host.startswith("http://"):
            self.config.unsecure = True

        logger.debug(f"SearxNG Search initialized with host: {self.config.searx_host}")

    def _build_params(self, query: str, **kwargs) -> Dict[str, Any]:
        """Build parameters for SearxNG API request."""
        params = _get_default_params()
        params["q"] = query

        # Add engines if specified
        engines = kwargs.get("engines", self.config.engines)
        if engines:
            params["engines"] = ",".join(engines)

        # Add categories if specified
        categories = kwargs.get("categories", self.config.categories)
        if categories:
            params["categories"] = ",".join(categories)

        # Add query suffix
        query_suffix = kwargs.get("query_suffix", self.config.query_suffix)
        if self.config.query_suffix:
            params["q"] += " " + self.config.query_suffix
        if query_suffix:
            params["q"] += " " + query_suffix

        # Add any additional parameters
        for key, value in kwargs.items():
            if key not in ["engines", "categories", "query_suffix"]:
                params[key] = value

        return params

    def _searx_api_query(self, params: Dict[str, Any]) -> SearxNGResults:
        """Perform actual request to SearxNG API."""
        try:
            request_kwargs: Dict[str, Any] = {
                "headers": self.config.headers,
                "params": params,
                "verify": not self.config.unsecure,
                "timeout": self.config.timeout,
            }
            if self._proxy:
                request_kwargs["proxies"] = {"http": self._proxy, "https": self._proxy}

            response = requests.get(self.config.searx_host, **request_kwargs)
            response.raise_for_status()

            if not response.text.strip():
                raise SearxNGSearchError("Empty response from SearxNG API")

            return SearxNGResults(response.text)

        except requests.exceptions.Timeout:
            raise SearxNGSearchError(f"Request timeout after {self.config.timeout} seconds")
        except requests.exceptions.ConnectionError:
            raise SearxNGSearchError(f"Failed to connect to SearxNG host: {self.config.searx_host}")
        except requests.exceptions.HTTPError as e:
            raise SearxNGSearchError(f"HTTP error from SearxNG API: {e}")
        except json.JSONDecodeError as e:
            raise SearxNGSearchError(f"Invalid JSON response from SearxNG API: {e}")
        except Exception as e:
            raise SearxNGSearchError(f"Unexpected error during SearxNG API request: {e}")

    async def _asearx_api_query(self, params: Dict[str, Any]) -> SearxNGResults:
        """Perform async request to SearxNG API."""
        try:
            kwargs = {
                "headers": self.config.headers,
                "params": params,
                "timeout": aiohttp.ClientTimeout(total=self.config.timeout),
            }
            if self.config.unsecure:
                kwargs["ssl"] = False

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.config.searx_host,
                    proxy=self._proxy,
                    **kwargs,
                ) as response:
                    response.raise_for_status()
                    text = await response.text()

                    if not text.strip():
                        raise SearxNGSearchError("Empty response from SearxNG API")

                    return SearxNGResults(text)

        except asyncio.TimeoutError:
            raise SearxNGSearchError(f"Request timeout after {self.config.timeout} seconds")
        except aiohttp.ClientConnectionError:
            raise SearxNGSearchError(f"Failed to connect to SearxNG host: {self.config.searx_host}")
        except aiohttp.ClientResponseError as e:
            raise SearxNGSearchError(f"HTTP error from SearxNG API: {e}")
        except json.JSONDecodeError as e:
            raise SearxNGSearchError(f"Invalid JSON response from SearxNG API: {e}")
        except Exception as e:
            raise SearxNGSearchError(f"Unexpected error during async SearxNG API request: {e}")

    def _transform_results(self, query: str, raw_results: SearxNGResults, response_time: float) -> SearchResult:
        """Transform SearxNG results to standard SearchResult format."""
        sources = []

        for i, result in enumerate(raw_results.results[: self.config.max_results]):
            # Convert rank to a score between 0 and 1
            # Higher rank (lower number) should have higher score
            # Use a simple inverse ranking: score = 1 / (rank + 1)
            # This ensures score is between 0 and 1, with rank 0 getting score 1.0
            score = 1.0 / (i + 1)

            source = SourceItem(
                url=result.get("url", ""),
                title=result.get("title", ""),
                content=result.get("content", ""),
                score=score,
                raw_content=result.get("content", ""),
            )
            sources.append(source)

        # Use first answer if available
        answer = None
        if raw_results.answers and len(raw_results.answers) > 0:
            answer = raw_results.answers[0]

        return SearchResult(
            query=query, answer=answer, sources=sources, response_time=response_time, raw_response=dict(raw_results)
        )

    @override
    async def search(self, query: str, **kwargs) -> SearchResult:
        """
        Perform an search query using SearxNG.

        Args:
            query: The search query string
            engines: Optional list of engines to use for the query
            categories: Optional list of categories to use for the query
            query_suffix: Optional suffix to append to the query
            **kwargs: Additional search parameters

        Returns:
            SearchResult: Structured search results

        Raises:
            SearxNGSearchError: If search fails
        """
        start_time = time.time()

        try:
            logger.debug(f"Performing SearxNG search for query: {query}")

            params = self._build_params(query, **kwargs)
            raw_results = await self._asearx_api_query(params)

            response_time = time.time() - start_time

            result = self._transform_results(query, raw_results, response_time)

            logger.debug(f"SearxNG search completed in {response_time:.2f}s with {len(result.sources)} results")

            return result

        except SearxNGSearchError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in SearxNG search: {e}")
            raise SearxNGSearchError(f"Unexpected error in SearxNG search: {e}")
