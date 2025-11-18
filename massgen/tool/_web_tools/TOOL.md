---
name: web-tools
description: Web scraping and content extraction using Crawl4AI REST API
category: web-scraping
requires_api_keys: []
tasks:
  - "Scrape web pages and extract clean markdown content"
  - "Capture webpage screenshots for visual analysis"
  - "Generate PDFs from web pages"
  - "Execute JavaScript on web pages for dynamic content"
  - "Crawl multiple URLs for bulk content extraction"
  - "Extract structured data from HTML"
keywords: [web-scraping, crawl4ai, markdown, html, screenshot, pdf, javascript, crawler, content-extraction]
---

# Web Tools (Crawl4AI)

Custom tool wrapper for the Crawl4AI Docker container's REST API, providing powerful web scraping capabilities without MCP protocol overhead.

## Purpose

Enable agents to easily scrape and extract content from web pages using Crawl4AI's advanced features:
- Clean markdown extraction from any webpage
- Screenshot capture for visual verification
- PDF generation for archival
- JavaScript execution for dynamic content
- Multi-URL crawling for bulk operations

## When to Use This Tool

**Use web tools when:**
- Extracting article content, documentation, or blog posts
- Converting web content to clean markdown format
- Capturing visual snapshots of web pages
- Scraping data from multiple related pages
- Accessing content that requires basic JavaScript rendering

**Do NOT use for:**
- Complex browser automation workflows (use `_browser_automation` instead)
- Local website testing (use browser automation tools)
- Tasks requiring extensive JavaScript interaction
- Real-time web application testing

## Available Functions

### `crawl4ai_md(url: str, ...) -> ExecutionResult`
Extract clean markdown from a webpage.

**Example:**
```python
result = await crawl4ai_md("https://example.com/article")
# Returns: Markdown formatted content
```

### `crawl4ai_html(url: str, ...) -> ExecutionResult`
Get preprocessed HTML content.

**Example:**
```python
result = await crawl4ai_html("https://example.com")
# Returns: Cleaned HTML
```

### `crawl4ai_screenshot(url: str, output_path: str, ...) -> ExecutionResult`
Capture webpage screenshot.

**Example:**
```python
result = await crawl4ai_screenshot("https://example.com", "screenshot.png")
# Saves: screenshot.png in workspace
```

### `crawl4ai_pdf(url: str, output_path: str, ...) -> ExecutionResult`
Generate PDF from webpage.

**Example:**
```python
result = await crawl4ai_pdf("https://example.com", "page.pdf")
# Saves: page.pdf in workspace
```

### `crawl4ai_execute_js(url: str, js_code: str, ...) -> ExecutionResult`
Run JavaScript on page before scraping.

**Example:**
```python
js = "document.querySelector('.content').click();"
result = await crawl4ai_execute_js("https://example.com", js)
```

### `crawl4ai_crawl(urls: List[str], ...) -> ExecutionResult`
Crawl multiple URLs in batch.

**Example:**
```python
urls = ["https://example.com/page1", "https://example.com/page2"]
result = await crawl4ai_crawl(urls)
# Returns: Combined results from all URLs
```

### `crawl4ai_ask(question: str) -> ExecutionResult`
Query Crawl4AI library documentation.

**Example:**
```python
result = await crawl4ai_ask("How do I extract links?")
# Returns: Documentation answer
```

## Configuration

### Prerequisites

**Start Crawl4AI Docker container:**
```bash
docker pull unclecode/crawl4ai:latest
docker run -d -p 11235:11235 --name crawl4ai --shm-size=1g unclecode/crawl4ai:latest
```

**Verify it's running:**
```bash
curl http://localhost:11235/health
```

### YAML Config

Enable web tools in your config:

```yaml
custom_tools_path: "massgen/tool/_web_tools"
```

Or use the provided config:
```yaml
# massgen/configs/tools/web/crawl4ai.yaml
```

## Features

- **URL validation**: Automatically validates URLs before scraping
- **Accessibility checks**: Verifies URLs are reachable before processing
- **Error handling**: Clear error messages for connection issues, timeouts, etc.
- **Workspace integration**: Screenshots and PDFs saved to agent workspace
- **Timeout management**: Configurable timeouts for long-running operations

## Limitations

- **Requires Docker container**: Must have Crawl4AI running at `http://localhost:11235`
- **Network access only**: Cannot scrape local files or localhost sites (from container's perspective)
- **Basic JavaScript**: Not suitable for complex SPAs requiring extensive interaction
- **No session management**: Each request is independent (no cookies/auth persistence)
- **Rate limiting**: Respect website rate limits and robots.txt

## Common Use Cases

1. **Documentation scraping**: Extract clean markdown from docs sites
2. **Article archival**: Save blog posts and articles as markdown or PDF
3. **Content analysis**: Extract text for LLM analysis
4. **Visual verification**: Screenshot pages for proof or debugging
5. **Bulk data extraction**: Crawl multiple pages from same domain
