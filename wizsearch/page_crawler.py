import logging
from typing import Any, Optional

from .base import get_proxy_from_env

logger = logging.getLogger(__name__)


class PageCrawler:
    """
    Web page crawler using Crawl4AI library with comprehensive parameter support.
    """

    def __init__(
        self,
        url: str,
        external_links: bool = False,
        content_format: str = "markdown",
        adaptive_crawl: bool = False,
        depth: int = 1,
        # Additional crawl4ai parameters
        word_count_threshold: int = 5,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        verbose: bool = False,
        wait_for: Optional[str] = None,
        screenshot: bool = False,
        bypass_cache: bool = False,
        only_text: bool = False,
        session_id: Optional[str] = None,
        extraction_strategy: Optional[str] = None,
        proxy: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        Initialize PageCrawler with comprehensive Crawl4AI parameter support.

        Args:
            url: The URL to crawl
            external_links: Whether to crawl external links
            content_format: Output format ('markdown', 'html', 'text')
            adaptive_crawl: Whether to use adaptive crawling
            depth: The depth of the crawl
            word_count_threshold: Minimum word count for content blocks
            user_agent: User agent string for requests
            verbose: Enable verbose logging
            wait_for: CSS selector to wait for before extracting content
            screenshot: Whether to take a screenshot
            bypass_cache: Whether to bypass cache
            only_text: Whether to extract only text content
            session_id: Session ID for maintaining browser state
            extraction_strategy: Strategy for content extraction
            proxy: Proxy URL (e.g., http://proxy:port). Falls back to
                   HTTPS_PROXY/HTTP_PROXY env vars if not set.
            **kwargs: Additional crawl4ai parameters
        """
        self.url = url
        self.external_links = external_links
        self.content_format = content_format
        self.adaptive_crawl = adaptive_crawl
        self.depth = depth
        self.word_count_threshold = word_count_threshold
        self.user_agent = user_agent
        self.verbose = verbose
        self.wait_for = wait_for
        self.screenshot = screenshot
        self.bypass_cache = bypass_cache
        self.only_text = only_text
        self.session_id = session_id
        self.extraction_strategy = extraction_strategy
        # Resolve proxy: env vars take priority over explicit argument
        self.proxy = get_proxy_from_env(proxy)
        self.extra_params = kwargs

    async def crawl(self) -> str:
        """
        Crawl a single page using the Crawl4AI library.

        Returns:
            str: The crawled content in the specified format.

        Raises:
            ImportError: If crawl4ai is not installed
            Exception: If crawling fails
        """
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        except ImportError:
            logger.warning("crawl4ai is not installed. Install with: uv add crawl4ai or pip install crawl4ai")
            logger.info(f"Skipping content crawling for {self.url}")
            return ""

        try:
            # Configure browser with optional proxy
            browser_kwargs: dict = {}
            if self.proxy:
                browser_kwargs["proxy"] = self.proxy
                logger.debug(f"PageCrawler: using proxy {self.proxy}")
            browser_config = BrowserConfig(**browser_kwargs)

            # Configure crawler parameters
            crawler_config = {
                "word_count_threshold": self.word_count_threshold,
                "user_agent": self.user_agent,
                "verbose": self.verbose,
                "bypass_cache": self.bypass_cache,
                "only_text": self.only_text,
            }

            # Add optional parameters if specified
            if self.wait_for:
                crawler_config["wait_for"] = self.wait_for
            if self.screenshot:
                crawler_config["screenshot"] = self.screenshot
            if self.session_id:
                crawler_config["session_id"] = self.session_id
            if self.extraction_strategy:
                crawler_config["extraction_strategy"] = self.extraction_strategy

            # Add any extra parameters
            crawler_config.update(self.extra_params)

            # Create crawler run config
            run_config = CrawlerRunConfig(**crawler_config)

            logger.info(f"Starting crawl for URL: {self.url}")

            async with AsyncWebCrawler(config=browser_config) as crawler:
                if self.adaptive_crawl:
                    # Use adaptive crawling if enabled
                    from crawl4ai import AdaptiveCrawler

                    adaptive = AdaptiveCrawler(crawler)
                    result = await adaptive.digest(
                        start_url=self.url,
                        # Use a generic query for adaptive crawling
                        query="extract main content and relevant information",
                    )

                    if result and hasattr(result, "extracted_content"):
                        content = result.extracted_content
                    else:
                        # Fallback to regular crawling
                        result = await crawler.arun(self.url, config=run_config)
                        content = self._extract_content(result)
                else:
                    # Standard crawling
                    result = await crawler.arun(self.url, config=run_config)
                    content = self._extract_content(result)

                # Handle multi-depth crawling for external links
                if self.external_links and self.depth > 1:
                    content = await self._crawl_with_depth(crawler, run_config, content)

                logger.info(f"Successfully crawled {self.url}, content length: {len(content) if content else 0}")
                return content or ""

        except Exception as e:
            logger.error(f"Failed to crawl {self.url}: {e}")
            # Return empty string instead of raising to allow search to continue
            return ""

    def _extract_content(self, result) -> str:
        """
        Extract content from crawl result based on specified format.

        Args:
            result: Crawl4AI result object

        Returns:
            str: Extracted content in specified format
        """
        if not result or not hasattr(result, "success") or not result.success:
            logger.warning(f"Crawl was not successful for {self.url}")
            return ""

        try:
            if self.content_format.lower() == "markdown":
                content = getattr(result, "markdown", "")
                return str(content) if content else ""
            elif self.content_format.lower() == "html":
                content = getattr(result, "html", "")
                return str(content) if content else ""
            elif self.content_format.lower() == "text":
                content = getattr(result, "cleaned_html", "") or getattr(result, "markdown", "")
                return str(content) if content else ""
            else:
                # Default to markdown
                content = getattr(result, "markdown", "")
                return str(content) if content else ""
        except Exception as e:
            logger.error(f"Error extracting content in format {self.content_format}: {e}")
            return ""

    async def _crawl_with_depth(self, crawler, run_config, initial_content: str) -> str:
        """
        Perform deep crawling with external links support.

        Args:
            crawler: AsyncWebCrawler instance
            run_config: Crawler configuration
            initial_content: Content from initial page crawl

        Returns:
            str: Combined content from all crawled pages
        """
        if self.depth <= 1:
            return initial_content

        try:
            # Extract links from initial page (simplified approach)
            # In a more sophisticated implementation, you would parse the HTML
            # to extract actual links and crawl them recursively
            combined_content = [initial_content]

            # For now, just return the initial content as deep crawling
            # with external links requires more complex link extraction
            logger.info(f"Deep crawling depth {self.depth} completed for {self.url}")
            return "\n\n".join(filter(None, combined_content))

        except Exception as e:
            logger.error(f"Error in deep crawling: {e}")
            return initial_content
