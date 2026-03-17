#!/usr/bin/env python3
"""
SearxNG Search Demo

This script demonstrates how to use the SearxNG search functionality
with the WizSearch interface.

Prerequisites:
- A running SearxNG instance (see docker-compose.yml for setup)
- Set SEARX_HOST environment variable or provide it directly

Usage:
    # Using environment variable
    export SEARX_HOST="http://localhost:8888"
    uv run python examples/searxng_search_demo.py

    # Or modify the config in the script below
"""

import asyncio
import os

from wizsearch import SearxNGSearch, SearxNGSearchConfig
from wizsearch.engines.searxng_search import SearxNGSearchError


async def demo_basic_search():
    """Demonstrate basic SearxNG search functionality."""
    print("=== Basic SearxNG Search Demo ===")

    try:
        # Initialize with custom configuration for better timeout
        config = SearxNGSearchConfig()
        search = SearxNGSearch(config=config)

        # Perform a basic search
        query = "artificial intelligence latest developments"
        print(f"\nSearching for: '{query}'")

        result = await search.search(query)

        print(f"Response time: {result.response_time:.2f}s")
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
        print(f"SearxNG search error: {e}")


async def demo_search_with_parameters():
    """Demonstrate search with various parameters."""
    print("\n=== Search Parameters Demo ===")

    try:
        config = SearxNGSearchConfig()
        search = SearxNGSearch(config=config)

        # Search with specific engines and categories
        query = "python programming tutorials"
        print(f"\nSearching for: '{query}' with specific parameters")

        result = await search.search(
            query,
            # Use all available engines instead of specific ones
            # engines=["stackoverflow", "github"],
            categories=["it"],
            # query_suffix="site:github.com OR site:stackoverflow.com"
        )

        print(f"Response time: {result.response_time:.2f}s")
        print(f"Number of sources: {len(result.sources)}")

        print("\nResults:")
        for i, source in enumerate(result.sources[:3], 1):
            print(f"\n{i}. {source.title}")
            print(f"   URL: {source.url}")

    except SearxNGSearchError as e:
        print(f"SearxNG search error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def demo_async_search():
    """Demonstrate async SearxNG search functionality."""
    print("\n=== Async Search Demo ===")

    try:
        config = SearxNGSearchConfig()
        search = SearxNGSearch(config=config)

        # Perform multiple async searches
        queries = ["climate change solutions", "renewable energy technologies", "electric vehicle adoption"]

        print(f"\nPerforming {len(queries)} async searches...")

        # Run searches concurrently
        tasks = [search.search(query) for query in queries]
        results = await asyncio.gather(*tasks)

        for query, result in zip(queries, results):
            print(f"Response time: {result.response_time:.2f}s")
            print(f"Sources found: {len(result.sources)}")
            if result.sources:
                print(f"Top result: {result.sources[0].title}")

    except SearxNGSearchError as e:
        print(f"SearxNG search error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def main():
    """Run all demos."""
    print("SearxNG Search Demo")
    print("==================")

    # Check if SearxNG host is configured
    searx_host = os.getenv("SEARX_HOST")
    if not searx_host:
        print("\n⚠️  Warning: SEARX_HOST environment variable not set!")
        print("   Please set it to your SearxNG instance URL, e.g.:")
        print("   export SEARX_HOST='http://localhost:8888'")
        print("\n   You can start a local SearxNG instance using:")
        print("   docker-compose up searxng")
        print("\n   Proceeding with demos (some may fail)...")
    else:
        print(f"\n✅ Using SearxNG host: {searx_host}")

    # Run async demos
    await demo_basic_search()
    await demo_search_with_parameters()
    await demo_async_search()

    print("\n" + "=" * 50)
    print("Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
