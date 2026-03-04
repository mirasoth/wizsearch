import asyncio
import importlib
import inspect
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, Field

from .base import BaseSearch, SearchResult

logger = logging.getLogger(__name__)


class SearchEngineRegistry:
    """
    Registry for search engines that automatically discovers and registers
    all available search engine implementations.
    """

    _engines: Dict[str, Tuple[Type[BaseSearch], Optional[Type[BaseModel]]]] = {}
    _initialized = False

    @classmethod
    def _discover_engines(cls) -> None:
        """Automatically discover and register all search engines."""
        if cls._initialized:
            return

        # Known search engine modules and their configurations
        engine_modules = [
            ("wizsearch.engines.baidu_search", "BaiduSearch", "BaiduSearchConfig"),
            ("wizsearch.engines.brave_search", "BraveSearch", "BraveSearchConfig"),
            ("wizsearch.engines.duckduckgo_search", "DuckDuckGoSearch", "DuckDuckGoSearchConfig"),
            ("wizsearch.engines.google_ai_search", "GoogleAISearch", None),
            ("wizsearch.engines.searxng_search", "SearxNGSearch", "SearxNGSearchConfig"),
            ("wizsearch.engines.tavily_search", "TavilySearch", "TavilySearchConfig"),
            ("wizsearch.engines.wechat_search", "WeChatSearch", "WeChatSearchConfig"),
            ## Followings have strict anti-bot protection
            ("wizsearch.engines.bing_search", "BingSearch", "BingSearchConfig"),
            ("wizsearch.engines.google_search", "GoogleSearch", "GoogleSearchConfig"),
        ]

        for module_name, engine_class_name, config_class_name in engine_modules:
            try:
                module = importlib.import_module(module_name)
                engine_class = getattr(module, engine_class_name)

                # Verify it's a BaseSearch subclass
                if not (inspect.isclass(engine_class) and issubclass(engine_class, BaseSearch)):
                    logger.warning(f"{engine_class_name} is not a BaseSearch subclass")
                    continue

                # Get config class if specified
                config_class = None
                if config_class_name:
                    config_class = getattr(module, config_class_name, None)
                    if config_class and not issubclass(config_class, BaseModel):
                        logger.warning(f"{config_class_name} is not a BaseModel subclass")
                        config_class = None

                # Register the engine
                engine_key = cls._get_engine_key(engine_class_name)
                cls._engines[engine_key] = (engine_class, config_class)
                logger.debug(f"Registered search engine: {engine_key}")

            except ImportError as e:
                logger.debug(f"Could not import {module_name}: {e}")
            except AttributeError as e:
                logger.warning(f"Could not find class {engine_class_name} in {module_name}: {e}")
            except Exception as e:
                logger.error(f"Error registering engine from {module_name}: {e}")

        cls._initialized = True
        logger.info(f"Search engine registry initialized with {len(cls._engines)} engines: {list(cls._engines.keys())}")

    @classmethod
    def _get_engine_key(cls, class_name: str) -> str:
        """Convert class name to engine key (e.g., DuckDuckGoSearch -> duckduckgo)."""
        # Remove 'Search' suffix and convert to lowercase
        key = class_name.replace("Search", "").lower()

        # Handle camelCase to snake_case conversion for compound names
        import re

        key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key).lower()

        # Special cases for known engines
        key_mappings = {
            "baidu": "baidu",
            "bing": "bing",
            "brave": "brave",
            "duckduckgo": "duckduckgo",
            "google": "google",
            "googleai": "googleai",
            "searxng": "searxng",
            "tavily": "tavily",
            "wechat": "wechat",
        }

        return key_mappings.get(key, key)

    @classmethod
    def register_engine(
        cls, name: str, engine_class: Type[BaseSearch], config_class: Optional[Type[BaseModel]] = None
    ) -> None:
        """
        Manually register a search engine.

        Args:
            name: Engine name/key
            engine_class: Search engine class
            config_class: Optional configuration class
        """
        if not issubclass(engine_class, BaseSearch):
            raise ValueError(f"Engine class {engine_class} must inherit from BaseSearch")

        if config_class and not issubclass(config_class, BaseModel):
            raise ValueError(f"Config class {config_class} must inherit from BaseModel")

        cls._engines[name] = (engine_class, config_class)
        logger.info(f"Manually registered search engine: {name}")

    @classmethod
    def get_available_engines(cls) -> List[str]:
        """Get list of all available engine names."""
        cls._discover_engines()
        return list(cls._engines.keys())

    @classmethod
    def get_engine(cls, name: str) -> Optional[Tuple[Type[BaseSearch], Optional[Type[BaseModel]]]]:
        """Get engine class and config class by name."""
        cls._discover_engines()
        return cls._engines.get(name)

    @classmethod
    def create_engine(cls, name: str, max_results: int = 10, **kwargs) -> Optional[BaseSearch]:
        """
        Create an instance of the specified engine.

        Args:
            name: Engine name
            max_results: Maximum results for the engine
            **kwargs: Additional configuration parameters

        Returns:
            BaseSearch instance or None if engine not found/failed to create
        """
        engine_info = cls.get_engine(name)
        if not engine_info:
            logger.error(f"Engine '{name}' not found in registry")
            return None

        engine_class, config_class = engine_info

        try:
            if config_class:
                # Create config with max_results and any additional kwargs
                config_kwargs = {"max_results": max_results, **kwargs}

                # Filter kwargs to only include valid config fields
                config_fields = config_class.model_fields.keys()
                filtered_kwargs = {k: v for k, v in config_kwargs.items() if k in config_fields}

                config = config_class(**filtered_kwargs)
                engine = engine_class(config=config)
            else:
                # Engine doesn't use config class, pass kwargs directly
                engine = engine_class(**kwargs)

            logger.debug(f"Created engine instance: {name}")
            return engine

        except Exception as e:
            logger.error(f"Failed to create engine '{name}': {e}")
            return None


class WizSearchConfig(BaseModel):
    """
    Configuration for WizSearch.
    """

    enabled_engines: Optional[List[str]] = Field(
        default=None, description="List of enabled search engines. If None, all available engines are used."
    )
    max_results_per_engine: int = Field(default=10, ge=1, le=50, description="Maximum results per engine")
    timeout: int = Field(default=30, ge=1, le=60, description="Request timeout in seconds")
    fail_silently: bool = Field(default=True, description="Continue if some engines fail")

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to set default enabled_engines if None."""
        if self.enabled_engines is None:
            # Auto-discover and enable all available engines
            self.enabled_engines = SearchEngineRegistry.get_available_engines()
            logger.info(f"Auto-enabled all available engines: {self.enabled_engines}")


class WizSearchError(Exception):
    """Custom exception for WizSearch errors."""


class WizSearch(BaseSearch):
    """
    Multi-engine search aggregator that runs searches concurrently across multiple engines
    and merges results using a round-robin approach to maintain diversity.
    """

    def __init__(self, config: Optional[WizSearchConfig] = None, **kwargs):
        """
        Initialize WizSearch with multiple search engines.

        Args:
            config: Configuration object for WizSearch
            **kwargs: Additional configuration parameters
        """
        if config is None:
            config = WizSearchConfig()

        # Override config with kwargs if provided
        if kwargs:
            config = config.model_copy(update=kwargs)

        self.config = config
        self.engines: Dict[str, BaseSearch] = {}
        self._initialize_engines()

    def _initialize_engines(self) -> None:
        """Initialize all enabled search engines using the registry."""
        for engine_name in self.config.enabled_engines:
            try:
                engine = SearchEngineRegistry.create_engine(engine_name, max_results=self.config.max_results_per_engine)

                if engine:
                    self.engines[engine_name] = engine
                    logger.debug(f"Initialized {engine_name} search engine")
                else:
                    logger.warning(f"Failed to create engine: {engine_name}")
                    if not self.config.fail_silently:
                        raise WizSearchError(f"Failed to create engine: {engine_name}")

            except Exception as e:
                logger.error(f"Failed to initialize {engine_name} engine: {e}")
                if not self.config.fail_silently:
                    raise WizSearchError(f"Failed to initialize {engine_name} engine: {e}")

    def _merge_results(self, query: str, engine_results: Dict[str, SearchResult]) -> SearchResult:
        """
        Merge search results from multiple engines using round-robin approach.

        Args:
            query: Original search query
            engine_results: Dictionary mapping engine names to their SearchResult objects

        Returns:
            SearchResult: Merged results with deduplicated URLs
        """
        if not engine_results:
            return SearchResult(query=query, sources=[])

        # Track seen URLs for deduplication
        seen_urls = set()
        merged_sources = []
        all_images = []
        combined_answers = []
        total_response_time = 0
        raw_responses = {}

        # Get maximum index across all result sets
        max_length = max(len(result.sources) for result in engine_results.values()) if engine_results else 0

        # Round-robin merge: pick index 0 from each engine, then index 1, etc.
        for index in range(max_length):
            for engine_name, search_result in engine_results.items():
                if index < len(search_result.sources):
                    source = search_result.sources[index]

                    # Skip duplicates based on URL
                    if source.url not in seen_urls and source.url:
                        seen_urls.add(source.url)
                        merged_sources.append(source)

                # Collect additional data from first iteration only
                if index == 0:
                    if search_result.images:
                        all_images.extend(search_result.images)
                    if search_result.answer:
                        combined_answers.append(f"{engine_name}: {search_result.answer}")
                    if search_result.response_time:
                        total_response_time += search_result.response_time
                    raw_responses[engine_name] = search_result.raw_response

        # Create merged result
        merged_answer = " | ".join(combined_answers) if combined_answers else None

        return SearchResult(
            query=query,
            answer=merged_answer,
            images=list(set(all_images)),  # Remove duplicate images
            sources=merged_sources,
            response_time=total_response_time,
            raw_response=raw_responses,
            follow_up_questions=None,
        )

    async def _search_engine_with_timeout(
        self, engine_name: str, engine: BaseSearch, query: str, **kwargs
    ) -> Optional[SearchResult]:
        """
        Search with a specific engine with timeout handling.

        Args:
            engine_name: Name of the search engine
            engine: Search engine instance
            query: Search query
            **kwargs: Additional search parameters

        Returns:
            SearchResult or None if timeout/error occurs
        """
        try:
            # Use asyncio.wait_for to implement timeout
            result = await asyncio.wait_for(engine.search(query, **kwargs), timeout=self.config.timeout)
            logger.info(f"{engine_name} search completed for '{query}' successfully with {len(result.sources)} results")
            return result

        except asyncio.TimeoutError:
            logger.warning(f"{engine_name} search timed out after {self.config.timeout} seconds")
            if not self.config.fail_silently:
                raise WizSearchError(f"{engine_name} search timed out")
            return None

        except Exception as e:
            logger.error(f"{engine_name} search failed: {e}")
            if not self.config.fail_silently:
                raise WizSearchError(f"{engine_name} search failed: {e}")
            return None

    async def search(self, query: str, **kwargs) -> SearchResult:
        """
        Perform a search query over all integrated engines concurrently.

        Args:
            query: Search query string
            **kwargs: Additional search parameters

        Returns:
            SearchResult: Merged results from all engines
        """
        if not query or not query.strip():
            raise WizSearchError("Search query cannot be empty")

        if not self.engines:
            raise WizSearchError("No search engines are available")

        query = query.strip()
        start_time = datetime.now()

        logger.info(f"Starting WizSearch for query: '{query}' with engines: {list(self.engines.keys())}")

        # Create concurrent search tasks
        search_tasks = []
        for engine_name, engine in self.engines.items():
            task = self._search_engine_with_timeout(engine_name, engine, query, **kwargs)
            search_tasks.append((engine_name, task))

        # Wait for all searches to complete
        results = await asyncio.gather(*[task for _, task in search_tasks], return_exceptions=True)

        # Process results
        engine_results = {}
        for (engine_name, _), result in zip(search_tasks, results):
            if isinstance(result, Exception):
                logger.error(f"Exception in {engine_name}: {result}")
                if not self.config.fail_silently:
                    raise WizSearchError(f"Search failed in {engine_name}: {result}")
            elif result is not None:
                engine_results[engine_name] = result

        # Merge results
        merged_result = self._merge_results(query, engine_results)

        total_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"WizSearch completed for '{query}' in {total_time:.2f} seconds. "
            f"Successful engines: {len(engine_results)}/{len(self.engines)}. "
            f"Total unique results: {len(merged_result.sources)}"
        )

        # Update response time to reflect total WizSearch time
        merged_result.response_time = total_time

        return merged_result

    def get_config(self) -> dict:
        """
        Get the current configuration of WizSearch.

        Returns:
            dict: Current configuration parameters
        """
        return self.config.model_dump()

    def get_enabled_engines(self) -> List[str]:
        """
        Get list of currently enabled and initialized engines.

        Returns:
            List[str]: Names of enabled engines
        """
        return list(self.engines.keys())

    @staticmethod
    def get_available_engines() -> List[str]:
        """
        Get list of all available engines that can be used.

        Returns:
            List[str]: Names of all available engines
        """
        return SearchEngineRegistry.get_available_engines()

    @staticmethod
    def register_custom_engine(
        name: str, engine_class: Type[BaseSearch], config_class: Optional[Type[BaseModel]] = None
    ) -> None:
        """
        Register a custom search engine.

        Args:
            name: Engine name/key
            engine_class: Search engine class that inherits from BaseSearch
            config_class: Optional configuration class that inherits from BaseModel
        """
        SearchEngineRegistry.register_engine(name, engine_class, config_class)
