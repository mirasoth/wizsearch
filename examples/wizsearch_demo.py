#!/usr/bin/env python3
"""
WizSearch Demo - Multi-Engine Search Integration

This example demonstrates how to use WizSearch to query multiple search engines
concurrently and merge results using round-robin deduplication.

Features demonstrated:
- Concurrent search across multiple engines
- Configurable timeout and engine selection
- Round-robin merge sort with URL deduplication
- Error handling and graceful failures
- Different configuration options

Prerequisites:
- Set up API keys for Tavily, Google AI, etc. as needed
- Install required dependencies: uv sync --extra dev

Usage:
    uv run python examples/wizsearch_demo.py
"""

import asyncio
import json
import time

from wizsearch import WizSearch, WizSearchConfig


def print_separator(title: str) -> None:
    """Print a formatted separator for demo sections."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def print_search_results(result, title: str = "Search Results") -> None:
    """Pretty print search results."""
    print(f"\n--- {title} ---")
    print(f"Query: {result.query}")
    print(f"Response Time: {result.response_time:.2f}s")
    print(f"Total Results: {len(result.sources)}")

    if result.answer:
        print(f"Answer: {result.answer}")

    print("\nTop Results:")
    for i, source in enumerate(result.sources[:5], 1):
        print(f"{i}. {source.title}")
        print(f"   URL: {source.url}")
        if source.content:
            content_preview = source.content[:100] + "..." if len(source.content) > 100 else source.content
            print(f"   Content: {content_preview}")
        if source.score:
            print(f"   Score: {source.score}")
        print()


async def demo_registry_features():
    """Demonstrate search engine registry features."""
    print_separator("Search Engine Registry Demo")

    # Show available engines
    available_engines = WizSearch.get_available_engines()
    print(f"Available engines: {available_engines}")

    # Show registry discovery
    print(f"Registry discovered {len(available_engines)} engines automatically")

    # Create WizSearch with all engines (default behavior)
    wizsearch = WizSearch()
    print(f"Auto-enabled engines: {wizsearch.get_enabled_engines()}")


async def demo_basic_search():
    """Demonstrate basic WizSearch functionality."""
    print_separator("Basic WizSearch Demo")

    # Create WizSearch with default configuration (all available engines)
    wizsearch = WizSearch()

    print(f"Auto-enabled engines: {wizsearch.get_enabled_engines()}")
    print(f"Configuration: {json.dumps(wizsearch.get_config(), indent=2)}")

    # Perform search
    query = "Python async programming best practices"
    print(f"\nSearching for: '{query}'")

    start_time = time.time()
    result = await wizsearch.search(query)
    search_time = time.time() - start_time

    print_search_results(result, "Basic Search Results")
    print(f"Total search time: {search_time:.2f}s")


async def demo_custom_configuration():
    """Demonstrate WizSearch with custom configuration."""
    print_separator("Custom Configuration Demo")

    # Create custom configuration
    config = WizSearchConfig(
        timeout=15,  # Shorter timeout
        enabled_engines=["duckduckgo", "tavily"],  # Only specific engines
        max_results_per_engine=5,  # Fewer results per engine
        fail_silently=False,  # Don't fail silently
    )

    wizsearch = WizSearch(config=config)

    print(f"Custom enabled engines: {wizsearch.get_enabled_engines()}")
    print(f"Custom configuration: {json.dumps(wizsearch.get_config(), indent=2)}")

    # Perform search
    query = "machine learning tutorials 2024"
    print(f"\nSearching for: '{query}'")

    try:
        result = await wizsearch.search(query)
        print_search_results(result, "Custom Configuration Results")
    except Exception as e:
        print(f"Search failed: {e}")


async def demo_async_search_functionality():
    """Demonstrate async search functionality with single engine."""
    print_separator("Async Search Demo (Single Engine)")

    # Create WizSearch for async demo
    config = WizSearchConfig(
        enabled_engines=["duckduckgo"], max_results_per_engine=3, timeout=10  # Use only DuckDuckGo for faster demo
    )
    wizsearch = WizSearch(config=config)

    query = "climate change solutions"
    print(f"Async search for: '{query}'")

    start_time = time.time()
    result = await wizsearch.search(query)  # Async call
    search_time = time.time() - start_time

    print_search_results(result, "Async Search Results")
    print(f"Total search time: {search_time:.2f}s")


async def demo_merge_behavior():
    """Demonstrate the round-robin merge behavior."""
    print_separator("Merge Behavior Demo")

    # Configure to use multiple engines with different result counts
    config = WizSearchConfig(enabled_engines=["duckduckgo", "tavily"], max_results_per_engine=8, timeout=20)
    wizsearch = WizSearch(config=config)

    query = "artificial intelligence news"
    print(f"Demonstrating merge behavior for: '{query}'")
    print("This will show how results are merged using round-robin from different engines")

    result = await wizsearch.search(query)

    print("\nMerged Results (showing engine source in raw_response):")
    print(f"Total unique results: {len(result.sources)}")

    # Show how results were merged
    if hasattr(result, "raw_response") and isinstance(result.raw_response, dict):
        engine_counts = {}
        for engine_name, engine_result in result.raw_response.items():
            if hasattr(engine_result, "__iter__") and not isinstance(engine_result, str):
                try:
                    engine_counts[engine_name] = len(engine_result)
                except (TypeError, AttributeError):
                    engine_counts[engine_name] = "unknown"

        print(f"Results per engine: {engine_counts}")

    # Show first few results to demonstrate round-robin
    print("\nFirst 6 results (showing round-robin merge):")
    for i, source in enumerate(result.sources[:6], 1):
        print(f"{i}. {source.title[:60]}...")
        print(f"   URL: {source.url}")


async def demo_error_handling():
    """Demonstrate error handling capabilities."""
    print_separator("Error Handling Demo")

    # Test with non-existent engine
    try:
        config = WizSearchConfig(enabled_engines=["nonexistent_engine"], fail_silently=False)
        wizsearch = WizSearch(config=config)
        await wizsearch.search("test query")
    except Exception as e:
        print(f"Expected error with non-existent engine: {e}")

    # Test with fail_silently=True
    config = WizSearchConfig(
        enabled_engines=["duckduckgo"],  # Only use DuckDuckGo
        fail_silently=True,
        timeout=1,  # Very short timeout to potentially cause timeouts
    )
    wizsearch = WizSearch(config=config)

    print("\nTesting with very short timeout (1 second):")
    result = await wizsearch.search("complex query that might timeout")
    print(f"Results even with potential timeouts: {len(result.sources)} results")


async def demo_performance_comparison():
    """Compare performance of single engine vs WizSearch."""
    print_separator("Performance Comparison")

    from wizsearch import DuckDuckGoSearch, DuckDuckGoSearchConfig

    query = "Python web frameworks comparison"

    # Test single engine
    print("Testing single engine (DuckDuckGo):")
    single_engine = DuckDuckGoSearch(DuckDuckGoSearchConfig(max_results=5))
    start_time = time.time()
    single_result = await single_engine.search(query)
    single_time = time.time() - start_time
    print(f"Single engine: {len(single_result.sources)} results in {single_time:.2f}s")

    # Test WizSearch with multiple engines
    print("\nTesting WizSearch (multiple engines):")
    config = WizSearchConfig(enabled_engines=["duckduckgo", "tavily"], max_results_per_engine=5, timeout=15)
    wizsearch = WizSearch(config=config)
    start_time = time.time()
    wiz_result = await wizsearch.search(query)
    wiz_time = time.time() - start_time
    print(f"WizSearch: {len(wiz_result.sources)} unique results in {wiz_time:.2f}s")

    print("\nComparison:")
    print(f"- Single engine: {len(single_result.sources)} results, {single_time:.2f}s")
    print(f"- WizSearch: {len(wiz_result.sources)} results, {wiz_time:.2f}s")
    print(f"- Additional unique results: {len(wiz_result.sources) - len(single_result.sources)}")


async def main():
    """Run all demo functions."""
    print("WizSearch Multi-Engine Search Demo")
    print("==================================")
    print("\nThis demo showcases WizSearch capabilities:")
    print("- Concurrent search across multiple engines")
    print("- Round-robin merge with URL deduplication")
    print("- Configurable timeouts and error handling")
    print("- Performance comparisons")

    try:
        # Run demos
        await demo_registry_features()
        await demo_basic_search()
        await demo_custom_configuration()
        await demo_async_search_functionality()
        await demo_merge_behavior()
        await demo_error_handling()
        await demo_performance_comparison()

        print_separator("Demo Complete")
        print("All demos completed successfully!")

    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        print("This might be due to missing API keys or network issues.")
        print("Check your environment variables and network connection.")


if __name__ == "__main__":
    # Set up logging
    import logging

    logging.basicConfig(level=logging.INFO)

    # Run the demo
    asyncio.run(main())
