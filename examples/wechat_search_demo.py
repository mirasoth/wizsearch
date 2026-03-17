#!/usr/bin/env python3
"""
WeChat Search Demo
"""

import asyncio

from wizsearch import WeChatSearch, WeChatSearchConfig


async def demo_headless_search():
    """Demonstrate WeChat search in headless mode (default)."""
    print("=== Headless Search Demo (Default) ===")
    print("Running in headless mode - no visible browser window\n")

    try:
        # Initialize with default configuration (headless=True)
        search = WeChatSearch(config=WeChatSearchConfig())

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
        print(f"WeChat search error: {e}")


async def demo_headed_search():
    """Demonstrate WeChat search with visible browser window (for debugging)."""
    print("\n=== Headed Search Demo (Debug Mode) ===")
    print("Running with visible browser window - useful for debugging\n")

    try:
        # Initialize with headless=False for debugging
        search = WeChatSearch(config=WeChatSearchConfig(headless=False))

        # Perform a basic search
        query = "人工智能 技术"
        result = await search.search(query)

        print(f"Number of sources: {len(result.sources)}")
        print("\nTop 3 results:")
        for i, source in enumerate(result.sources[:3], 1):
            print(f"\n{i}. {source.title}")
            print(f"   URL: {source.url}")

    except Exception as e:
        print(f"WeChat search error: {e}")


async def main():
    """Run all demos."""
    print("WeChat Search Demo")
    print("==================")

    # Run demos
    await demo_headless_search()
    # Uncomment to see headed mode (browser window will appear)
    # await demo_headed_search()

    print("\n" + "=" * 50)
    print("Demo completed!")
    print("\nTip: Uncomment demo_headed_search() in main() to see headed mode")


if __name__ == "__main__":
    asyncio.run(main())
