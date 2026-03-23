"""
Production-level Serper Search wrapper with enhanced functionality.

This module provides a polished, production-ready wrapper around the Serper API
(https://google.serper.dev) with proper error handling, logging, configuration
management, and integration with the existing search infrastructure. Supports
multiple search types including web, images, news, scholar, maps, videos, and more.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import override

from ..base import BaseSearch, SearchResult, get_proxy_from_env

logger = logging.getLogger(__name__)

SERPER_BASE_URL = "https://google.serper.dev"


class SerperSearchError(Exception):
    """Custom exception for Serper Search wrapper errors."""


class SerperSearchConfig(BaseModel):
    """Configuration for Serper Search wrapper."""

    api_key: Optional[str] = Field(None, description="Serper API key (falls back to SERPER_API_KEY env var)")
    search_type: str = Field(
        default="search",
        description="Search type: 'search' (web), 'images', 'news', 'scholar', 'maps', 'videos', 'autocomplete', 'lens', 'places'",
    )
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    gl: Optional[str] = Field(None, description="Country code for search (e.g., 'us')")
    hl: Optional[str] = Field(None, description="Language code for search (e.g., 'en')")
    proxy: Optional[str] = Field(
        None,
        description="Proxy URL (e.g., http://proxy:port). Falls back to HTTPS_PROXY/HTTP_PROXY env vars.",
    )
    timeout: int = Field(default=30, ge=1, le=120, description="Request timeout in seconds")

    model_config = ConfigDict(extra="forbid")


class SerperSearch(BaseSearch):
    """
    Production-level wrapper for Serper API.

    This class provides a robust interface to Serper API with:
    - Support for multiple search types (web, images, news, scholar, etc.)
    - Comprehensive error handling and logging
    - Configuration management
    - Response validation and processing
    - Integration with existing search infrastructure
    - Async-first design with aiohttp
    """

    # Valid search types and their endpoints
    SEARCH_TYPES = {
        "search": "search",
        "images": "images",
        "news": "news",
        "scholar": "scholar",
        "maps": "maps",
        "videos": "videos",
        "autocomplete": "autocomplete",
        "lens": "lens",
        "places": "places",
    }

    def __init__(self, config: Optional[SerperSearchConfig] = None, **kwargs):
        """
        Initialize the Serper Search wrapper.

        Args:
            config: Configuration object for the search wrapper
            **kwargs: Additional configuration parameters

        Raises:
            SerperSearchError: If API key is not provided
        """
        # Initialize configuration
        if config is None:
            config = SerperSearchConfig()

        # Override config with kwargs if provided
        if kwargs:
            config = config.model_copy(update=kwargs)

        self.config = config
        self._initialize()

    def _initialize(self) -> None:
        """Initialize the Serper search client."""
        try:
            # Resolve API key
            self.api_key = self.config.api_key or os.getenv("SERPER_API_KEY")
            if not self.api_key:
                raise SerperSearchError(
                    "Serper API key is required. Set SERPER_API_KEY environment variable " "or pass api_key in config."
                )

            # Validate search type
            if self.config.search_type not in self.SEARCH_TYPES:
                valid_types = ", ".join(self.SEARCH_TYPES.keys())
                raise SerperSearchError(f"Invalid search_type '{self.config.search_type}'. Valid types: {valid_types}")

            # Resolve proxy
            proxy = get_proxy_from_env(self.config.proxy)
            if proxy:
                os.environ.setdefault("HTTPS_PROXY", proxy)
                os.environ.setdefault("HTTP_PROXY", proxy)
                logger.debug(f"Serper: proxy configured via environment variables: {proxy}")

            logger.debug(f"Serper search initialized for type: {self.config.search_type}")

        except SerperSearchError:
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Serper search: {e}")
            raise SerperSearchError(f"Failed to initialize Serper search: {e}")

    @override
    async def search(self, query: str, **kwargs) -> SearchResult:
        """
        Perform an async search using Serper API.

        Args:
            query: Search query string (for 'lens' type, this should be an image URL)
            **kwargs: Additional search parameters

        Returns:
            SearchResult object with search results

        Raises:
            SerperSearchError: If search fails or response is invalid
        """
        if not query or not query.strip():
            raise SerperSearchError("Search query cannot be empty")

        try:
            start_time = datetime.now()
            query = query.strip()

            logger.info(f"Performing Serper {self.config.search_type} search for query: {query}")

            # Build payload
            payload: Dict[str, Any] = {"q": query, "num": self.config.max_results}
            if self.config.gl:
                payload["gl"] = self.config.gl
            if self.config.hl:
                payload["hl"] = self.config.hl

            # Special handling for lens search
            endpoint = self.SEARCH_TYPES[self.config.search_type]
            if self.config.search_type == "lens":
                payload = {"url": query, "num": self.config.max_results}
                if self.config.gl:
                    payload["gl"] = self.config.gl
                if self.config.hl:
                    payload["hl"] = self.config.hl

            # Make async request
            raw_response = await self._make_request(endpoint, payload)

            response_time = (datetime.now() - start_time).total_seconds()

            # Transform response to SearchResult model
            result = self._transform_response(raw_response, query, response_time)

            logger.info(
                f"Search completed for '{query}' in {response_time:.2f} seconds, "
                f"{len(result.sources)} results found"
            )
            return result

        except SerperSearchError:
            raise
        except Exception as e:
            logger.error(f"Serper search failed for query '{query}': {e}")
            raise SerperSearchError(f"Search failed: {e}")

    async def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make async HTTP request to Serper API.

        Args:
            endpoint: API endpoint (e.g., 'search', 'images')
            payload: Request payload

        Returns:
            JSON response as dictionary

        Raises:
            SerperSearchError: If request fails
        """
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

        timeout = aiohttp.ClientTimeout(total=self.config.timeout)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{SERPER_BASE_URL}/{endpoint}",
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        raise SerperSearchError(f"Serper API error (status {resp.status}): {text}")

                    return await resp.json()

        except aiohttp.ClientError as e:
            logger.error(f"HTTP request to Serper API failed: {e}")
            raise SerperSearchError(f"HTTP request failed: {e}")

    def _transform_response(self, raw_response: Dict[str, Any], query: str, response_time: float) -> SearchResult:
        """
        Transform Serper API response to SearchResult model.

        Args:
            raw_response: Raw response from Serper API
            query: Original search query
            response_time: Response time in seconds

        Returns:
            SearchResult object
        """
        transformed = {
            "query": query,
            "answer": None,
            "images": [],
            "sources": [],
            "response_time": response_time,
            "raw_response": raw_response,
            "follow_up_questions": None,
            "metadata": {"search_type": self.config.search_type},
        }

        # Extract answer box if available
        if "answerBox" in raw_response:
            answer_box = raw_response["answerBox"]
            if isinstance(answer_box, dict):
                # Extract answer from various answer box formats
                if "answer" in answer_box:
                    transformed["answer"] = answer_box["answer"]
                elif "snippet" in answer_box:
                    transformed["answer"] = answer_box["snippet"]
                elif "result" in answer_box:
                    transformed["answer"] = answer_box["result"]

        # Extract knowledge graph if available
        if "knowledgeGraph" in raw_response:
            kg = raw_response["knowledgeGraph"]
            if isinstance(kg, dict):
                transformed["metadata"]["knowledge_graph"] = kg
                # Use knowledge graph description as answer if available
                if not transformed["answer"] and "description" in kg:
                    transformed["answer"] = kg["description"]

        # Extract images if available (for 'images' search type or regular search)
        if "images" in raw_response:
            images = raw_response["images"]
            if isinstance(images, list):
                transformed["images"] = [
                    img.get("imageUrl") or img.get("link")
                    for img in images[:10]
                    if isinstance(img, dict) and (img.get("imageUrl") or img.get("link"))
                ]

        # Extract related searches as follow-up questions
        if "relatedSearches" in raw_response:
            related = raw_response["relatedSearches"]
            if isinstance(related, list):
                transformed["follow_up_questions"] = [
                    item.get("query") for item in related[:5] if isinstance(item, dict) and item.get("query")
                ]

        # Extract organic results (main search results)
        # Serper uses different keys for different search types
        result_key = "organic" if "organic" in raw_response else None
        if not result_key:
            # Check for other result types
            for key in ["news", "scholar", "videos", "places", "results"]:
                if key in raw_response:
                    result_key = key
                    break

        if result_key:
            results_list = raw_response[result_key]
            if isinstance(results_list, list):
                sources = []

                for idx, result_item in enumerate(results_list):
                    if not isinstance(result_item, dict):
                        continue

                    # Calculate score based on position (inverse ranking)
                    position = result_item.get("position", idx + 1)
                    score = 1.0 / (position + 1) if position else 1.0 / (idx + 2)

                    # Extract URL based on result type
                    url = result_item.get("link") or result_item.get("url") or ""

                    source_item = {
                        "url": url,
                        "title": result_item.get("title", ""),
                        "content": result_item.get("snippet", ""),
                        "score": round(score, 3),
                        "raw_content": None,
                    }

                    # For images, include image URL
                    if self.config.search_type == "images" and "imageUrl" in result_item:
                        source_item["raw_content"] = result_item["imageUrl"]

                    # For videos, include additional metadata
                    if self.config.search_type == "videos":
                        metadata = {}
                        if "channel" in result_item:
                            metadata["channel"] = result_item["channel"]
                        if "date" in result_item:
                            metadata["date"] = result_item["date"]
                        if metadata:
                            source_item["raw_content"] = str(metadata)

                    sources.append(source_item)

                transformed["sources"] = sources

        return SearchResult.model_validate(transformed)

    def get_config(self) -> dict:
        """
        Get the current configuration of the search engine.

        Returns:
            dict: Current configuration parameters (excluding sensitive data like API key)
        """
        config_dict = self.config.model_dump()
        # Mask API key for security
        config_dict["api_key"] = "***masked***"
        return config_dict
