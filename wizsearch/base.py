import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


def get_proxy_from_env(config_proxy: Optional[str] = None) -> Optional[str]:
    """
    Resolve proxy configuration with environment variable override.

    Mirrors tarzi's get_proxy_from_env_or_config() in src/config.rs.
    Checks environment variables in priority order, then falls back to
    the explicitly provided config_proxy value.

    Priority order:
        1. HTTPS_PROXY env var
        2. HTTP_PROXY env var
        3. https_proxy env var
        4. http_proxy env var
        5. config_proxy argument
        6. None (no proxy)

    Args:
        config_proxy: Explicit proxy URL from engine config. Used only when
                      no proxy env vars are set.

    Returns:
        Resolved proxy URL string, or None if no proxy is configured.
    """
    for env_var in ["HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"]:
        proxy = os.environ.get(env_var, "").strip()
        if proxy:
            return proxy
    return config_proxy


class SourceItem(BaseModel):
    """Individual search result from Tavily."""

    url: str = Field(..., description="URL of the search result")
    title: str = Field(..., description="Title of the search result")
    content: Optional[str] = Field(None, description="Extracted content from the page")
    score: Optional[float] = Field(None, ge=0, le=1, description="Relevance score")
    raw_content: Optional[str] = Field(None, description="Raw content from the page")

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)


class SearchResult(BaseModel):
    """Complete response from Tavily Search API."""

    query: str = Field(..., description="Original search query")
    answer: Optional[str] = Field(None, description="AI-generated answer")
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    sources: List[SourceItem] = Field(default_factory=list, description="Search results")
    response_time: Optional[float] = Field(None, description="API response time in seconds")
    raw_response: Optional[Any] = Field(
        None,
        json_schema_extra={"description": "Raw response from the web search API"},
    )
    follow_up_questions: Optional[List[str]] = Field(None, description="Suggested follow-up questions")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata about the search (e.g., engine status, debug info)"
    )

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)


class BaseSearch(ABC):
    """
    Abstract base class for web search engines.

    This class defines the interface that all search engine implementations
    must follow to ensure consistent behavior across different providers.
    """

    @abstractmethod
    async def search(self, query: str, **kwargs) -> SearchResult:
        """
        Perform an async search query.

        Args:
            query: The search query string
            **kwargs: Additional search parameters

        Returns:
            SearchResponse: Structured search results

        Raises:
            Exception: If search fails
        """
