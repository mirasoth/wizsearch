#!/usr/bin/env python3
"""
Bing Search Demo
"""

import asyncio

from wizsearch import BingSearch, BingSearchConfig


async def demo_headless_search():
    """Demonstrate Bing search in headless mode (default)."""
    print("=== Headless Search Demo (Default) ===")
    print("Running in headless mode - no visible browser window\n")

    try:
        # Initialize with default configuration (headless=True)
        search = BingSearch(config=BingSearchConfig())

        # Perform a basic search
        query = "甲骨文 星际之门"
        result = await search.search(query)

        print(f"Number of sources: {len(result.sources)}")

        if result.answer:
            print(f"\nDirect answer: {result.answer}")

        print("\nTop 5 results:")
        for i, source in enumerate(result.sources[:5], 1):
            print(f"\n{i}. {source.title}")
            print(f"   URL: {source.url}")
            if source.content:
                content = source.content[:200] + "..." if len(source.content) > 200 else source.content
                print(f"   Content: {content}")

    except Exception as e:
        print(f"Bing search error: {e}")


async def demo_headed_search():
    """Demonstrate Bing search with visible browser window (for debugging)."""
    print("\n=== Headed Search Demo (Debug Mode) ===")
    print("Running with visible browser window - useful for debugging\n")

    try:
        # Initialize with headless=False for debugging
        search = BingSearch(config=BingSearchConfig(headless=False))

        # Perform a basic search
        query = "Python async programming"
        result = await search.search(query)

        print(f"Number of sources: {len(result.sources)}")
        print("\nTop 3 results:")
        for i, source in enumerate(result.sources[:3], 1):
            print(f"\n{i}. {source.title}")
            print(f"   URL: {source.url}")

    except Exception as e:
        print(f"Bing search error: {e}")


async def demo_async_search():
    """Demonstrate async Bing search functionality."""
    print("\n=== Async Search Demo ===")

    try:
        search = BingSearch(config=BingSearchConfig())

        # Perform multiple async searches
        queries = ["climate change solutions", "renewable energy technologies"]

        print(f"\nPerforming {len(queries)} async searches...")

        # Run searches concurrently
        tasks = [search.search(query) for query in queries]
        results = await asyncio.gather(*tasks)

        for _, result in zip(queries, results):
            print(f"Sources found: {len(result.sources)}")
            if result.sources:
                print(f"Top result: {result.sources[0].title}")

    except Exception as e:
        print(f"Bing search error: {e}")


async def main():
    """Run all demos."""
    print("Bing Search Demo")
    print("==================")

    # Run demos
    await demo_headless_search()
    await demo_async_search()
    # Uncomment to see headed mode (browser window will appear)
    # await demo_headed_search()

    print("\n" + "=" * 50)
    print("Demo completed!")
    print("\nTip: Uncomment demo_headed_search() in main() to see headed mode")


if __name__ == "__main__":
    asyncio.run(main())
