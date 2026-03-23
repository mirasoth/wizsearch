# WizSearch

[![CI](https://github.com/mirasoth/wizsearch/actions/workflows/ci.yml/badge.svg)](https://github.com/mirasoth/wizsearch/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/wizsearch.svg)](https://pypi.org/project/wizsearch/)

A unified Python library for searching across multiple search engines with a consistent interface. WizSearch enables concurrent multi-engine searches with intelligent result merging, page crawling capabilities, and optional semantic search integration.

## Features

- **Multiple Search Engines**: Baidu, Bing, Brave, DuckDuckGo, Google, Google AI, SearxNG, Serper, Tavily, WeChat (with sogou engine)
- **Unified Interface**: Single API for all search engines with consistent `SearchResult` format
- **Multi-Engine Aggregation**: Concurrent searches across multiple engines with round-robin result merging
- **Page Crawling**: Built-in web page content extraction using Crawl4AI
- **Semantic Search**: Optional vector-based semantic search with local storage and web fallback
- **Async/Await Support**: Full asynchronous API for high performance

## Installation

```bash
# Basic installation
pip install wizsearch

# With development dependencies
pip install wizsearch[dev]
```

## Quick Start

### Basic Single Engine Search

```python
import asyncio
from wizsearch import DuckDuckGoSearch, DuckDuckGoSearchConfig

async def search_example():
    # Initialize a single search engine
    config = DuckDuckGoSearchConfig(max_results=5)
    searcher = DuckDuckGoSearch(config=config)

    # Perform search
    results = await searcher.search("Python async programming")

    # Access results
    print(f"Query: {results.query}")
    print(f"Found {len(results.sources)} results\n")

    for source in results.sources:
        print(f"Title: {source.title}")
        print(f"URL: {source.url}")
        print(f"Content: {source.content[:100]}...")
        print()

asyncio.run(search_example())
```

### Multi-Engine Search with WizSearch

WizSearch automatically discovers and runs searches across multiple engines concurrently, then merges results using a round-robin approach to maintain diversity.

```python
import asyncio
from wizsearch import WizSearch, WizSearchConfig

async def multi_engine_search():
    # Auto-enable all available engines
    wizsearch = WizSearch()

    # Or configure specific engines
    config = WizSearchConfig(
        enabled_engines=["duckduckgo", "tavily", "brave"],
        max_results_per_engine=10,
        timeout=30,
        fail_silently=True  # Continue even if some engines fail
    )
    wizsearch = WizSearch(config=config)

    # Search across all enabled engines
    results = await wizsearch.search("machine learning tutorials")

    print(f"Total unique results: {len(results.sources)}")
    print(f"Response time: {results.response_time:.2f}s")

    for i, source in enumerate(results.sources[:5], 1):
        print(f"{i}. {source.title}")
        print(f"   {source.url}\n")

asyncio.run(multi_engine_search())
```

## Detailed Usage

### Available Search Engines

WizSearch supports the following search engines, each with its own configuration:

| Engine | Code Name | 🔑 API Key | Notes |
|--------|-----------|-----------|-------|
| Tavily | `tavily` | ✅ | AI-optimized search, requires `TAVILY_API_KEY` |
| Google AI | `googleai` | ✅ | Requires `GEMINI_API_KEY` |
| Serper | `serper` | ✅ | Google search API, requires `SERPER_API_KEY`, supports multiple search types (web, images, news, scholar, maps, videos, etc.) |
| DuckDuckGo | `duckduckgo` | ❌ | Free, no rate limits |
| Baidu | `baidu` | ❌ | Chinese search engine (via tarzi), runs in headless mode by default |
| WeChat | `wechat` | ❌ | WeChat article search (via tarzi), runs in headless mode by default |
| Brave | `brave` | ❌ | Browser-based scraping (via tarzi), runs in headless mode by default |
| Bing | `bing` | ❌ | Browser-based scraping, anti-bot protection (via tarzi), runs in headless mode by default |
| Google | `google` | ❌ | Browser-based scraping, anti-bot protection (via tarzi), runs in headless mode by default |
| SearxNG | `searxng` | ❌ | Self-hosted metasearch engine |

**Note**: Use the "Code Name" column values when specifying engines in `WizSearchConfig.enabled_engines`.

### Browser Mode Configuration

The browser-based search engines (Baidu, Bing, Brave, Google, and WeChat) use the tarzi library for web scraping. These engines run in **headless mode** by default, meaning no visible browser window appears during searches. This is ideal for production environments as it:

- Doesn't require a display or GUI
- Consumes fewer resources
- Runs faster than headed mode
- Is more suitable for servers and containers

#### Using Headless Mode (Default)

```python
from wizsearch import GoogleSearch, GoogleSearchConfig

# Default: runs in headless mode (no visible window)
search = GoogleSearch(config=GoogleSearchConfig())
results = await search.search("machine learning")
```

#### Using Headed Mode for Debugging

If you need to see the browser window for debugging (e.g., to check if searches are working correctly, debug anti-bot protections, or observe the scraping process), you can disable headless mode:

```python
from wizsearch import GoogleSearch, GoogleSearchConfig

# Disable headless mode to see the browser window
config = GoogleSearchConfig(headless=False)
search = GoogleSearch(config=config)
results = await search.search("machine learning")
```

#### Configuring Browser Mode in WizSearch

When using the `WizSearch` aggregator, you can control the browser mode for all tarzi-based engines:

```python
from wizsearch import WizSearch, WizSearchConfig

# All tarzi engines will use headless mode (default)
config = WizSearchConfig(
    enabled_engines=["google", "bing", "brave"],
    headless=True  # Default
)
wizsearch = WizSearch(config=config)

# Or disable headless for all tarzi engines (useful for debugging)
config = WizSearchConfig(headless=False)
wizsearch = WizSearch(config=config)
```

### Engine-Specific Examples

#### DuckDuckGo Search

```python
from wizsearch import DuckDuckGoSearch, DuckDuckGoSearchConfig

config = DuckDuckGoSearchConfig(
    max_results=10,
    region="us-en",  # Region setting
    safesearch="moderate",  # "on", "moderate", or "off"
    timelimit="m",  # Time limit: "d" (day), "w" (week), "m" (month), "y" (year)
    backend="auto"
)
searcher = DuckDuckGoSearch(config=config)
results = await searcher.search("climate change")
```

#### Tavily Search (Advanced Features)

```python
from wizsearch import TavilySearch, TavilySearchConfig
import os

# Set API key
os.environ["TAVILY_API_KEY"] = "your-api-key"

config = TavilySearchConfig(
    max_results=5,
    search_depth="advanced",  # "basic" or "advanced"
    include_domains=["arxiv.org", "scholar.google.com"],
    exclude_domains=["youtube.com"],
    include_answer=True,  # Get AI-generated answer
    include_images=True
)

searcher = TavilySearch(config=config)
results = await searcher.search(
    query="quantum computing breakthroughs",
    search_depth="advanced",
    include_domains=["nature.com", "science.org"]
)

# Access AI-generated answer
if results.answer:
    print(f"Answer: {results.answer}")

# Access images
for image_url in results.images:
    print(f"Image: {image_url}")
```

#### Google AI Search

```python
from wizsearch import GoogleAISearch
import os

# Set API key (or set GEMINI_API_KEY environment variable)
os.environ["GEMINI_API_KEY"] = "your-gemini-api-key"

searcher = GoogleAISearch()
results = await searcher.search(
    query="neural network architectures",
    num_results=5
)

# Image search
image_results = await searcher.search(
    query="data visualization examples",
    search_type="image",
    num_results=10
)
```

#### Serper Search (Google API)

Serper provides a powerful Google search API with support for multiple search types:

```python
from wizsearch import SerperSearch, SerperSearchConfig
import os

# Set API key (or set SERPER_API_KEY environment variable)
os.environ["SERPER_API_KEY"] = "your-serper-api-key"

# Web search
config = SerperSearchConfig(
    search_type="search",  # Default: web search
    max_results=10,
    gl="us",  # Country: United States
    hl="en",  # Language: English
)
searcher = SerperSearch(config=config)
results = await searcher.search("Python async programming")

# Image search
config = SerperSearchConfig(search_type="images", max_results=10)
searcher = SerperSearch(config=config)
results = await searcher.search("beautiful landscapes")

# News search
config = SerperSearchConfig(search_type="news", max_results=5)
searcher = SerperSearch(config=config)
results = await searcher.search("artificial intelligence")

# Scholar search (academic papers)
config = SerperSearchConfig(search_type="scholar", max_results=10)
searcher = SerperSearch(config=config)
results = await searcher.search("machine learning transformers")

# Other supported search types: videos, maps, places, autocomplete, lens
```

### WizSearch Configuration

```python
from wizsearch import WizSearch, WizSearchConfig

# Get all available engines
available = WizSearch.get_available_engines()
print(f"Available engines: {available}")

# Custom configuration
# Use code names from the table above (e.g., "duckduckgo", "tavily", "brave")
config = WizSearchConfig(
    enabled_engines=["duckduckgo", "tavily", "brave"],
    max_results_per_engine=10,  # Results per engine
    timeout=30,  # Timeout in seconds
    fail_silently=True,  # Don't raise if some engines fail
    headless=True  # Use headless mode for browser-based engines (default: True)
)

wizsearch = WizSearch(config=config)

# Check enabled engines
print(f"Enabled: {wizsearch.get_enabled_engines()}")

# Get configuration
print(wizsearch.get_config())

# Perform search
results = await wizsearch.search("Python best practices")
```

### Page Crawling

Extract full page content from search results using crawl4ai-powered page crawler:

```python
from wizsearch import PageCrawler

crawler = PageCrawler(
    url="https://example.com/article",
    content_format="markdown",  # "markdown", "html", or "text"
    external_links=False,
    adaptive_crawl=False,
    depth=1,
    word_count_threshold=5,
    user_agent="Mozilla/5.0...",
    wait_for=None,  # CSS selector to wait for
    screenshot=False,
    bypass_cache=False,
    only_text=True
)

# Crawl the page
content = await crawler.crawl()
print(content)
```

### Semantic Search (Advanced | Preview)

Combine web search with local vector storage for enhanced semantic search capabilities. The semantic search interface is synchronous.

```python
from wizsearch.semsearch import SemanticSearch, SemanticSearchConfig
from wizsearch import TavilySearch

# Configure semantic search
config = SemanticSearchConfig(
    vector_store_provider="weaviate",  # or "pgvector"
    collection_name="DocumentChunks",
    embedding_model="nomic-embed-text:latest",
    local_search_limit=10,
    web_search_limit=5,
    fallback_threshold=5,  # Min local results before web search
    enable_caching=True,
    cache_ttl_hours=24,
    auto_store_web_results=True  # Automatically store web results
)

# Initialize with Tavily as web search engine
web_search = TavilySearch()
semantic_search = SemanticSearch(
    web_search_engine=web_search,
    config=config
)

# Connect to vector store
semantic_search.connect()

# Perform semantic search
# First searches local vector store, falls back to web if needed
result = semantic_search.search(
    query="machine learning best practices",
    limit=10,
    force_web_search=False
)

print(f"Total results: {result.total_results}")
print(f"Local: {result.local_results}, Web: {result.web_results}")
print(f"Search time: {result.search_time:.2f}s")

# Access chunks with scores
for chunk, score in result.chunks[:5]:
    print(f"\n[{score:.3f}] {chunk.source_title}")
    print(f"Content: {chunk.content[:200]}...")

# Manually store documents
semantic_search.store_document(
    content="Your document content here...",
    source_url="https://example.com",
    source_title="Example Document",
    metadata={"category": "tutorial"}
)

# Get statistics
stats = semantic_search.get_stats()
print(stats)
```

### Working with Search Results

All search engines return a consistent `SearchResult` object:

```python
# SearchResult structure
results = await searcher.search("query")

# Basic attributes
print(results.query)           # Original query
print(results.answer)          # AI-generated answer (if available)
print(results.images)          # List of image URLs
print(results.response_time)   # Response time in seconds
print(results.raw_response)    # Raw API response

# Source items
for source in results.sources:
    print(source.url)          # URL
    print(source.title)        # Title
    print(source.content)      # Extracted content/snippet
    print(source.score)        # Relevance score (if available)
    print(source.raw_content)  # Raw content
```

### Custom Engine Registration

Register your own custom search engine:

```python
from wizsearch import WizSearch, WizSearchConfig, BaseSearch, SearchResult, SourceItem
from pydantic import BaseModel

class CustomSearchConfig(BaseModel):
    max_results: int = 10
    api_key: str = ""

class CustomSearch(BaseSearch):
    def __init__(self, config: CustomSearchConfig):
        self.config = config

    async def search(self, query: str, **kwargs) -> SearchResult:
        # Implement your search logic
        # Example: return mock results
        sources = [
            SourceItem(
                url="https://example.com",
                title="Example Result",
                content="This is example content",
                score=0.95
            )
        ]
        return SearchResult(
            query=query,
            sources=sources,
            answer=None
        )

# Register the engine
WizSearch.register_custom_engine(
    name="custom",
    engine_class=CustomSearch,
    config_class=CustomSearchConfig
)

# Use it with WizSearch
config = WizSearchConfig(enabled_engines=["custom", "duckduckgo"])
wizsearch = WizSearch(config=config)
results = await wizsearch.search("test query")
```

## Examples

Check the `examples/` directory for comprehensive examples:

- `wizsearch_demo.py` - Multi-engine search demonstrations
- `tavily_search_demo.py` - Tavily-specific features
- `google_ai_search_demo.py` - Google AI search examples
- `serper_search_demo.py` - Serper search examples with multiple search types
- `ddg_search_demo.py` - DuckDuckGo search examples
- Individual engine demos for each supported search engine

Run examples:

```bash
# Basic demo
uv run python examples/wizsearch_demo.py

# Tavily demo (requires API key)
export TAVILY_API_KEY="your-key"
uv run python examples/tavily_search_demo.py

# Serper demo (requires API key)
export SERPER_API_KEY="your-key"
uv run python examples/serper_search_demo.py
```

## API Reference

### Core Classes

- **`WizSearch`**: Multi-engine search aggregator
  - `search(query, **kwargs)`: Perform concurrent search
  - `get_available_engines()`: List all available engines
  - `get_enabled_engines()`: List enabled engines
  - `get_config()`: Get current configuration
  - `register_custom_engine(name, engine_class, config_class)`: Register custom engine

- **`WizSearchConfig`**: Configuration for WizSearch
  - `enabled_engines`: List of engine names to enable
  - `max_results_per_engine`: Max results per engine (1-50)
  - `timeout`: Request timeout in seconds (1-60)
  - `fail_silently`: Continue if engines fail (default: True)
  - `headless`: Enable headless browser mode for browser-based engines (default: True)

- **`BaseSearch`**: Abstract base class for search engines
  - `search(query, **kwargs)`: Async search method

- **`SearchResult`**: Unified search result format
  - `query`: Original query string
  - `answer`: AI-generated answer (optional)
  - `images`: List of image URLs
  - `sources`: List of `SourceItem` objects
  - `response_time`: Response time in seconds
  - `raw_response`: Raw API response

- **`SourceItem`**: Individual search result
  - `url`: Result URL
  - `title`: Result title
  - `content`: Extracted content/snippet
  - `score`: Relevance score (optional)
  - `raw_content`: Raw content (optional)

- **`PageCrawler`**: Web page content crawler
  - `crawl()`: Async crawl method

- **`SemanticSearch`**: Semantic search with vector storage
  - `connect()`: Connect to vector store
  - `search(query, limit, force_web_search, filters)`: Semantic search
  - `store_document(content, source_url, source_title, metadata)`: Store document
  - `get_stats()`: Get system statistics
  - `clear_cache()`: Clear query cache

## Environment Variables

Some search engines require API keys set as environment variables:

```bash
# Tavily (required for TavilySearch)
export TAVILY_API_KEY="your-tavily-api-key"

# Google AI (required for GoogleAISearch)
export GEMINI_API_KEY="your-gemini-api-key"

# Serper (required for SerperSearch)
export SERPER_API_KEY="your-serper-api-key"
```

## Development

```bash
# Clone repository
git clone https://github.com/mirasoth/wizsearch.git
cd wizsearch

# Install development dependencies
pip install -e ".[dev]"

# Run tests
make test

# Run linting
make lint

# Format code
make format
```

## Architecture

```
┌─────────────────┐
│   WizSearch     │  Multi-engine orchestrator
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│Engine 1│ │Engine 2│  Individual search engines
└────────┘ └────────┘
    │         │
    └────┬────┘
         ▼
   ┌──────────┐
   │  Merger  │  Round-robin result merging
   └──────────┘
         │
         ▼
  ┌─────────────┐
  │SearchResult │  Unified result format
  └─────────────┘
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **Homepage**: https://github.com/mirasoth/wizsearch
- **PyPI**: https://pypi.org/project/wizsearch/
- **Issues**: https://github.com/mirasoth/wizsearch/issues
