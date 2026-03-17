#!/usr/bin/env python3
"""
DuckDuckGo Search Demo

This example demonstrates how to use the DuckDuckGoSearch class from wizsearch
to perform web searches using the DuckDuckGo search engine.

Requirements:
- ddgs library: pip install ddgs
"""

import asyncio
import json

from wizsearch import DuckDuckGoSearch, DuckDuckGoSearchConfig, DuckDuckGoSearchError


def print_search_results(result, title: str = "Search Results"):
    """Print search results in a formatted way."""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")

    print(f"Query: {result.query}")
    print(f"Response time: {result.response_time:.2f}s")
    print(f"Number of results: {len(result.sources)}")

    if result.answer:
        print(f"Answer: {result.answer}")

    print("\nResults:")
    print("-" * 50)

    for i, source in enumerate(result.sources, 1):
        print(f"{i}. {source.title}")
        print(f"   URL: {source.url}")
        if source.content:
            # Truncate content to avoid very long output
            content = source.content[:200] + "..." if len(source.content) > 200 else source.content
            print(f"   Content: {content}")
        if source.score:
            print(f"   Score: {source.score}")
        print()


async def configured_search_example():
    """Demonstrate DuckDuckGo search with custom configuration."""
    print("\n\nConfigured DuckDuckGo Search Example")

    try:
        # Create custom configuration
        config = DuckDuckGoSearchConfig(
            max_results=5, region="us-en", safesearch="moderate", timelimit="m", backend="auto"  # Last month
        )

        # Initialize search with custom config
        search = DuckDuckGoSearch(config=config)

        # Perform search
        query = "artificial intelligence machine learning"
        result = await search.search(query)

        print_search_results(result, "Configured Search Results")

        # Print configuration
        print("\nConfiguration used:")
        config_dict = search.get_config()
        print(json.dumps(config_dict, indent=2))

    except DuckDuckGoSearchError as e:
        print(f"Search error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def search_with_parameters_example():
    """Demonstrate search with runtime parameters."""
    print("\n\nSearch with Runtime Parameters Example")

    try:
        # Initialize with basic config
        search = DuckDuckGoSearch()

        # Search with runtime parameters that override config
        query = "climate change renewable energy"
        result = await search.search(query, max_results=3, region="uk-en", safesearch="off", timelimit="w")  # Last week

        print_search_results(result, "Search with Runtime Parameters")

    except DuckDuckGoSearchError as e:
        print(f"Search error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def async_search_example():
    """Demonstrate asynchronous DuckDuckGo search."""
    print("\n\nAsync DuckDuckGo Search Example")

    try:
        # Initialize search
        search = DuckDuckGoSearch()

        # Perform multiple async searches
        queries = ["space exploration NASA", "quantum computing breakthrough", "renewable energy solar panels"]

        print(f"Performing {len(queries)} async searches...")

        # Run searches concurrently
        tasks = [search.search(query, max_results=3) for query in queries]
        results = await asyncio.gather(*tasks)

        # Print results
        for i, result in enumerate(results):
            print_search_results(result, f"Async Search {i+1}")

    except DuckDuckGoSearchError as e:
        print(f"Search error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def basic_search_example():
    """Demonstrate basic DuckDuckGo search functionality."""
    print("\n\nBasic DuckDuckGo Search Example")

    try:
        # Initialize search with default config
        search = DuckDuckGoSearch()

        # Perform a basic search
        query = "Python programming tutorial"
        result = await search.search(query, max_results=5)

        print_search_results(result, "Basic Search Results")

    except DuckDuckGoSearchError as e:
        print(f"Search error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def error_handling_example():
    """Demonstrate error handling."""
    print("\n\nError Handling Example")

    try:
        search = DuckDuckGoSearch()

        # Test with empty query
        try:
            await search.search("")
        except DuckDuckGoSearchError as e:
            print(f"✓ Caught expected error for empty query: {e}")

        # Test with very long query
        long_query = "very " * 100 + "long query"
        try:
            await search.search(long_query, max_results=1)
            print("✓ Long query handled successfully")
        except DuckDuckGoSearchError as e:
            print(f"! Error with long query: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")


async def main():
    """Run all examples."""
    print("DuckDuckGo Search Demo")
    print("=" * 50)

    # Run all async examples
    await basic_search_example()
    await configured_search_example()
    await search_with_parameters_example()
    await error_handling_example()
    await async_search_example()

    print("\n" + "=" * 50)
    print("Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
