from typing import Optional

from pydantic import BaseModel, Field

from .base_tarzi_search import TarziSearch, TarziSearchConfig


class BingSearchConfig(BaseModel):
    max_results: int = Field(default=10, description="Maximum number of results to return")
    timeout: int = Field(default=15, description="Timeout in seconds")
    web_driver: str = Field(default="chromedriver", description="Web driver to use")
    headless: bool = Field(default=False, description="If enable headless browser")
    output_format: str = Field(default="markdown", description="Output format (html|markdown|json|yaml)")
    proxy: Optional[str] = Field(
        default=None,
        description="Proxy URL (e.g., http://proxy:port). Falls back to HTTPS_PROXY/HTTP_PROXY env vars if not set.",
    )


class BingSearch(TarziSearch):
    def __init__(self, config: BingSearchConfig):
        # Convert BingSearchConfig to TarziSearchConfig with bing engine
        tarzi_config = TarziSearchConfig(
            search_engine="bing",
            max_results=config.max_results,
            timeout=config.timeout,
            web_driver=config.web_driver,
            headless=config.headless,
            output_format=config.output_format,
            proxy=config.proxy,
        )
        super().__init__(tarzi_config)
