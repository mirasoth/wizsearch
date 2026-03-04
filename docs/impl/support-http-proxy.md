# Support HTTP Proxy for All wizsearch Engines

## Background

wizsearch wraps multiple search engine backends. When deployed behind a corporate firewall or in a region with restricted internet access, all outbound HTTP/HTTPS traffic must be routed through a proxy. This document designs and records how proxy support is added consistently across every engine.

### Reference: tarzi (thirdparty) Proxy Implementation

The embedded `tarzi` Rust library already implements proxy support as the canonical reference:

- **Config field**: `FetcherConfig.proxy: Option<String>` in `src/config.rs`
- **Env-var resolution**: `get_proxy_from_env_or_config()` in `src/config.rs` checks env vars in priority order:
  1. `HTTPS_PROXY`
  2. `HTTP_PROXY`
  3. `https_proxy`
  4. `http_proxy`
  5. Falls back to `config.fetcher.proxy`
- **Application**: `WebFetcher::from_config()` calls this function and injects the resolved proxy into the `reqwest::Client` builder.
- **TOML config**: `proxy = "http://..."` under `[fetcher]` section.

wizsearch's Python layer follows the same conventions.

---

## Design Goals

1. **Env-var first, case-insensitive**: Support `HTTPS_PROXY`, `HTTP_PROXY`, `https_proxy`, `http_proxy` (checked in that priority order).
2. **Explicit config override**: Every engine config accepts an optional `proxy: Optional[str]` field that takes precedence over env vars is absent — env vars are checked when proxy is `None`.
3. **Single utility function**: `get_proxy_from_env(config_proxy)` in `wizsearch/base.py` encapsulates the resolution logic, mirroring tarzi's `get_proxy_from_env_or_config`.
4. **No breaking changes**: All proxy fields default to `None`; existing code without proxy config continues to work unchanged.

---

## Proxy Resolution Priority

```
explicit config.proxy
    └─ if None → HTTPS_PROXY env var
           └─ if unset → HTTP_PROXY env var
                  └─ if unset → https_proxy env var
                         └─ if unset → http_proxy env var
                                └─ if unset → None (no proxy)
```

---

## Engine-by-Engine Design

### 1. Tarzi-based engines (Baidu, Bing, Brave, Google, WeChat)

**Files**: `base_tarzi_search.py`, `baidu_search.py`, `bing_search.py`, `brave_search.py`, `google_search.py`, `wechat_search.py`

**Mechanism**: tarzi's Rust core already reads `HTTPS_PROXY`/`HTTP_PROXY` env vars automatically inside `WebFetcher::from_config()`. The Python layer only needs to surface an explicit `proxy` field so users can pass a proxy programmatically; it gets injected into the TOML config string as `[fetcher] proxy = "..."`.

**Changes**:
- Add `proxy: Optional[str] = None` to `TarziSearchConfig` and all per-engine configs.
- In `TarziSearch.__init__`, resolve effective proxy via `get_proxy_from_env(config.proxy)` and conditionally add `proxy = "..."` line to the TOML string.
- Each engine config class gains the same `proxy` field and forwards it to `TarziSearchConfig`.

### 2. DuckDuckGo

**File**: `duckduckgo_search.py`

**Mechanism**: `DDGS(proxy=...)` accepts an explicit proxy. The config already has `proxy: Optional[str]` but does not auto-read env vars.

**Changes**:
- In `DuckDuckGoSearch.__init__`, resolve proxy via `get_proxy_from_env(config.proxy)` and update `config.proxy` before creating the `DDGS` client.

### 3. SearxNG

**File**: `searxng_search.py`

**Mechanism**: Makes raw HTTP calls via `requests` (sync) and `aiohttp` (async). Neither client auto-reads proxy env vars unless explicitly configured.

**Changes**:
- Add `proxy: Optional[str] = None` to `SearxNGSearchConfig`.
- Resolve proxy via `get_proxy_from_env(config.proxy)` in `__init__`, store as `self._proxy`.
- Pass `proxies={"http": proxy, "https": proxy}` to `requests.get()`.
- Pass `proxy=proxy` to `aiohttp` `session.get()`.

### 4. Tavily

**File**: `tavily_search.py`

**Mechanism**: `langchain_tavily.TavilySearch` uses `httpx` internally. httpx reads proxy from env vars by default (`trust_env=True`). Therefore:
- Setting `HTTPS_PROXY`/`HTTP_PROXY` env vars **already works** for Tavily without code changes.
- For explicit programmatic proxy, we resolve it via `get_proxy_from_env(config.proxy)` and set the env var before tool initialization (only if not already set).

**Changes**:
- Add `proxy: Optional[str] = None` to `TavilySearchConfig`.
- In `_initialize_search_tool`, if an explicit proxy is resolved, set `os.environ["HTTPS_PROXY"]` / `os.environ["HTTP_PROXY"]` as a fallback so httpx picks them up (only sets if the env var is not already present).

### 5. Google AI Search

**File**: `google_ai_search.py`

**Mechanism**: `google.genai.Client` supports `http_options` parameter. We can pass a custom `httpx.Client` via the transport to apply proxy settings.

**Changes**:
- Add `proxy: Optional[str] = None` parameter to `GoogleAISearch.__init__`.
- Resolve proxy via `get_proxy_from_env(proxy)`.
- If proxy is set, create a custom `httpx.Client` with proxy transport and pass it to `GenAIClient` via `http_options`.

### 6. PageCrawler

**File**: `page_crawler.py`

**Mechanism**: `crawl4ai`'s `AsyncWebCrawler` accepts a `BrowserConfig` with `proxy` parameter.

**Changes**:
- Add `proxy: Optional[str] = None` parameter to `PageCrawler.__init__`.
- Resolve proxy via `get_proxy_from_env(proxy)`.
- Pass proxy to `AsyncWebCrawler(config=BrowserConfig(proxy=proxy))` when proxy is set.

---

## Utility Function

Added to `wizsearch/base.py`:

```python
def get_proxy_from_env(config_proxy: Optional[str] = None) -> Optional[str]:
    """
    Resolve proxy with environment variable override, mirroring tarzi's
    get_proxy_from_env_or_config() in src/config.rs.

    Priority order:
      1. HTTPS_PROXY env var
      2. HTTP_PROXY env var
      3. https_proxy env var
      4. http_proxy env var
      5. config_proxy argument
      6. None
    """
    for env_var in ["HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"]:
        proxy = os.environ.get(env_var, "").strip()
        if proxy:
            return proxy
    return config_proxy
```

---

## Usage Examples

### Via environment variable (recommended for deployment)

```bash
export HTTPS_PROXY=http://proxy.corp.example.com:8080
python -c "from wizsearch.engines.bing_search import BingSearch, BingSearchConfig; ..."
```

### Via explicit config

```python
from wizsearch.engines.bing_search import BingSearch, BingSearchConfig

engine = BingSearch(BingSearchConfig(proxy="http://proxy.corp.example.com:8080"))
```

```python
from wizsearch.engines.duckduckgo_search import DuckDuckGoSearch, DuckDuckGoSearchConfig

engine = DuckDuckGoSearch(DuckDuckGoSearchConfig(proxy="socks5://proxy.corp.example.com:1080"))
```

```python
from wizsearch.engines.searxng_search import SearxNGSearch, SearxNGSearchConfig

engine = SearxNGSearch(SearxNGSearchConfig(
    searx_host="http://localhost:8080",
    proxy="http://proxy.corp.example.com:8080"
))
```

---

## Affected Files

| File | Change Type |
|------|------------|
| `wizsearch/base.py` | Add `get_proxy_from_env()` utility |
| `wizsearch/engines/base_tarzi_search.py` | Add `proxy` field, inject to TOML |
| `wizsearch/engines/baidu_search.py` | Add `proxy` field, forward to TarziSearchConfig |
| `wizsearch/engines/bing_search.py` | Add `proxy` field, forward to TarziSearchConfig |
| `wizsearch/engines/brave_search.py` | Add `proxy` field, forward to TarziSearchConfig |
| `wizsearch/engines/google_search.py` | Add `proxy` field, forward to TarziSearchConfig |
| `wizsearch/engines/wechat_search.py` | Add `proxy` field, forward to TarziSearchConfig |
| `wizsearch/engines/duckduckgo_search.py` | Auto-resolve proxy from env vars |
| `wizsearch/engines/searxng_search.py` | Add `proxy` field, apply to requests/aiohttp |
| `wizsearch/engines/tavily_search.py` | Add `proxy` field, set env var for httpx |
| `wizsearch/engines/google_ai_search.py` | Add `proxy` param, apply via httpx transport |
| `wizsearch/page_crawler.py` | Add `proxy` param, pass to crawl4ai BrowserConfig |
