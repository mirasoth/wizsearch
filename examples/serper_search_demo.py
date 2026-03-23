"""
Serper Search Demo

This example demonstrates how to use SerperSearch engine for web searching.
Serper API (https://google.serper.dev) supports multiple search types including
web, images, news, scholar, maps, videos, autocomplete, lens, and places.

Requirements:
- Set SERPER_API_KEY environment variable, or pass api_key parameter
- Get your API key from: https://serper.dev/
"""

import asyncio
import os

from wizsearch import SerperSearch, SerperSearchConfig


async def demo_basic_search():
    """Demonstrate basic web search using Serper API."""
    print("=" * 60)
    print("Demo 1: Basic Web Search")
    print("=" * 60)

    # Initialize with API key (can also use SERPER_API_KEY env var)
    config = SerperSearchConfig(
        api_key=os.getenv("SERPER_API_KEY"),
        search_type="search",
        max_results=5,
    )
    search = SerperSearch(config=config)

    # Perform search
    result = await search.search("Python async programming")

    print(f"Query: {result.query}")
    print(f"Response time: {result.response_time:.2f}s")
    print(f"Results found: {len(result.sources)}")
    print()

    # Display results
    for idx, source in enumerate(result.sources, 1):
        print(f"{idx}. {source.title}")
        print(f"   URL: {source.url}")
        print(f"   Score: {source.score}")
        if source.content:
            print(f"   Snippet: {source.content[:100]}...")
        print()


async def demo_news_search():
    """Demonstrate news search using Serper API."""
    print("=" * 60)
    print("Demo 2: News Search")
    print("=" * 60)

    config = SerperSearchConfig(
        api_key=os.getenv("SERPER_API_KEY"),
        search_type="news",
        max_results=5,
    )
    search = SerperSearch(config=config)

    result = await search.search("artificial intelligence")

    print(f"Query: {result.query}")
    print(f"Search type: {result.metadata.get('search_type')}")
    print(f"Results: {len(result.sources)}")
    print()

    for idx, source in enumerate(result.sources, 1):
        print(f"{idx}. {source.title}")
        print(f"   URL: {source.url}")
        if source.content:
            print(f"   {source.content[:80]}...")
        print()


async def demo_images_search():
    """Demonstrate image search using Serper API."""
    print("=" * 60)
    print("Demo 3: Image Search")
    print("=" * 60)

    config = SerperSearchConfig(
        api_key=os.getenv("SERPER_API_KEY"),
        search_type="images",
        max_results=5,
    )
    search = SerperSearch(config=config)

    result = await search.search("beautiful landscapes")

    print(f"Query: {result.query}")
    print(f"Images found: {len(result.images)}")
    print(f"Sources with metadata: {len(result.sources)}")
    print()

    # Display image URLs
    for idx, img_url in enumerate(result.images[:3], 1):
        print(f"{idx}. {img_url}")
    print()


async def demo_scholar_search():
    """Demonstrate scholar/academic search using Serper API."""
    print("=" * 60)
    print("Demo 4: Scholar Search")
    print("=" * 60)

    config = SerperSearchConfig(
        api_key=os.getenv("SERPER_API_KEY"),
        search_type="scholar",
        max_results=5,
    )
    search = SerperSearch(config=config)

    result = await search.search("machine learning transformers")

    print(f"Query: {result.query}")
    print(f"Results: {len(result.sources)}")
    print()

    for idx, source in enumerate(result.sources, 1):
        print(f"{idx}. {source.title}")
        print(f"   URL: {source.url}")
        if source.content:
            print(f"   {source.content[:80]}...")
        print()


async def demo_localized_search():
    """Demonstrate localized search with country and language settings."""
    print("=" * 60)
    print("Demo 5: Localized Search")
    print("=" * 60)

    config = SerperSearchConfig(
        api_key=os.getenv("SERPER_API_KEY"),
        search_type="search",
        max_results=5,
        gl="us",  # Country: United States
        hl="en",  # Language: English
    )
    search = SerperSearch(config=config)

    result = await search.search("best coffee shops")

    print(f"Query: {result.query}")
    print(f"Country (gl): {search.config.gl}")
    print(f"Language (hl): {search.config.hl}")
    print(f"Results: {len(result.sources)}")
    print()

    for idx, source in enumerate(result.sources, 1):
        print(f"{idx}. {source.title}")
        if source.content:
            print(f"   {source.content[:80]}...")
        print()


async def demo_with_answer_box():
    """Demonstrate search that returns answer box."""
    print("=" * 60)
    print("Demo 6: Search with Answer Box")
    print("=" * 60)

    config = SerperSearchConfig(
        api_key=os.getenv("SERPER_API_KEY"),
        search_type="search",
        max_results=3,
    )
    search = SerperSearch(config=config)

    # Query likely to trigger answer box
    result = await search.search("what is the capital of France")

    print(f"Query: {result.query}")
    if result.answer:
        print(f"Answer: {result.answer}")
    print(f"Sources: {len(result.sources)}")
    print()


async def demo_with_wizsearch():
    """Demonstrate using Serper API through WizSearch aggregator."""
    print("=" * 60)
    print("Demo 7: Using Serper API via WizSearch Aggregator")
    print("=" * 60)

    from wizsearch import WizSearch, WizSearchConfig

    # Configure WizSearch to use only Serper
    config = WizSearchConfig(
        enabled_engines=["serper"],
        max_results_per_engine=5,
    )
    wizsearch = WizSearch(config=config)

    result = await wizsearch.search("Python web scraping")

    print(f"Query: {result.query}")
    print(f"Total results: {len(result.sources)}")
    print()

    for idx, source in enumerate(result.sources, 1):
        print(f"{idx}. {source.title}")
        print(f"   URL: {source.url}")
        print()


async def main():
    """Run all demos."""
    if not os.getenv("SERPER_API_KEY"):
        print("Error: SERPER_API_KEY environment variable not set")
        print("Get your API key from: https://serper.dev/")
        print("Then run: export SERPER_API_KEY='your-api-key'")
        return

    try:
        await demo_basic_search()
        await demo_news_search()
        await demo_images_search()
        await demo_scholar_search()
        await demo_localized_search()
        await demo_with_answer_box()
        await demo_with_wizsearch()
    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
