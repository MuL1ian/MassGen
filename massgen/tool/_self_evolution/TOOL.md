---
name: self-evolution
description: GitHub issue analysis for market-driven development and feature prioritization
category: development-tools
requires_api_keys: []
tasks:
  - "Analyze GitHub issues to understand user needs"
  - "Prioritize features based on user engagement"
  - "Identify common pain points and feature requests"
  - "Drive market-driven development decisions"
  - "Extract insights from issue discussions"
keywords: [github, issues, market-analysis, feature-prioritization, self-evolution, development, user-needs]
---

# Self-Evolution Tools

Tools for analyzing user feedback and driving market-driven development by understanding what users actually need from GitHub issues and pull requests.

## Purpose

Enable agents to autonomously understand user needs and prioritize development:
- **Market analysis**: Understand what users are asking for
- **Feature prioritization**: Identify most-requested features
- **Pain point detection**: Find common user problems
- **Engagement metrics**: Analyze which issues get most attention
- **Self-evolution**: Let agents guide their own development roadmap

**Philosophy:** Instead of guessing what to build, analyze actual user feedback to drive development decisions.

## When to Use This Tool

**Use self-evolution tools when:**
- Planning next features to implement
- Understanding user pain points
- Prioritizing backlog items
- Analyzing market demand
- Identifying common feature requests
- Driving roadmap decisions with data

**Do NOT use for:**
- Real-time issue tracking (use GitHub directly)
- Writing code (use code executors)
- Modifying issues (read-only analysis)

## Available Functions

### `fetch_github_issues(repo: str, state: str = "open", labels: List[str] = None, limit: int = 50) -> AsyncGenerator[ExecutionResult, None]`

Fetch and analyze GitHub issues for market-driven insights.

**Example - Analyze open issues:**
```python
async for result in fetch_github_issues(
    repo="Leezekun/MassGen",
    state="open",
    limit=20
):
    print(result.output_blocks[0].data)
# Returns: Structured analysis of open issues
```

**Example - Filter by labels:**
```python
async for result in fetch_github_issues(
    repo="Leezekun/MassGen",
    state="open",
    labels=["enhancement", "feature-request"],
    limit=30
):
    print(result.output_blocks[0].data)
# Returns: Only enhancement/feature-request issues
```

**Example - Analyze closed issues:**
```python
async for result in fetch_github_issues(
    repo="Leezekun/MassGen",
    state="closed",
    limit=50
):
    print(result.output_blocks[0].data)
# Returns: Recently resolved issues
```

**Parameters:**
- `repo` (str): Repository in format "owner/repo" (e.g., "Leezekun/MassGen")
- `state` (str): Issue state - "open", "closed", or "all" (default: "open")
- `labels` (List[str], optional): Filter by label names (e.g., ["bug", "enhancement"])
- `limit` (int): Maximum issues to analyze (default: 50, max: 100)

**Returns (streaming):**
Yields ExecutionResult blocks containing:
- Issue titles and descriptions
- Labels and categories
- Engagement metrics (comments, reactions)
- Categorized by type (bug, enhancement, question, etc.)
- Priority indicators (based on engagement)

**Note:** GitHub API returns both issues and PRs from `/issues` endpoint. This tool automatically filters out PRs and returns only actual issues.

## Analysis Output

The tool provides structured analysis including:

### 1. Issue Summary
- Total issues found
- State distribution (open/closed)
- Label distribution
- Time range

### 2. Categorization
Groups issues by type:
- **Bugs**: Problems to fix
- **Enhancements**: Feature requests
- **Questions**: User questions/clarifications
- **Documentation**: Docs improvements
- **Other**: Uncategorized

### 3. Engagement Metrics
For each issue:
- Number of comments
- Reaction counts (👍, 👎, ❤️, etc.)
- Engagement score (weighted metric)
- Age/recency

### 4. Priority Indicators
Issues ranked by:
- User engagement (comments + reactions)
- Recency (newer issues weighted higher)
- Label importance
- Clustering (multiple users wanting same thing)

### 5. Common Patterns
Identifies:
- Frequently mentioned features
- Recurring pain points
- Common keywords
- Related issues

## Configuration

### Prerequisites

**No authentication needed for public repos:**
- Uses GitHub's public API
- No API key required for read-only access

**For private repos or higher rate limits:**
```bash
export GITHUB_TOKEN="your-github-token"
```

**Install dependencies:**
```bash
pip install aiohttp
```

### YAML Config

Enable self-evolution tools in your config:

```yaml
custom_tools_path: "massgen/tool/_self_evolution"

# Or add to tools list
tools:
  - name: fetch_github_issues
```

## Use Cases

### 1. Feature Prioritization

```python
# Analyze enhancement requests
async for result in fetch_github_issues(
    repo="your-org/your-repo",
    state="open",
    labels=["enhancement"],
    limit=50
):
    # Agent analyzes which features users want most
    pass
```

**Agent can:**
- Identify most-requested features
- Find clustering (similar requests)
- Prioritize by engagement
- Create roadmap based on data

### 2. Bug Triage

```python
# Analyze open bugs
async for result in fetch_github_issues(
    repo="your-org/your-repo",
    state="open",
    labels=["bug"],
    limit=30
):
    # Agent identifies critical bugs by engagement
    pass
```

**Agent can:**
- Find high-impact bugs
- Identify patterns in bug reports
- Prioritize fixes by user impact
- Detect recurring issues

### 3. Documentation Gaps

```python
# Find documentation-related issues
async for result in fetch_github_issues(
    repo="your-org/your-repo",
    state="all",
    labels=["documentation"],
    limit=40
):
    # Agent identifies what users find confusing
    pass
```

**Agent can:**
- Find unclear documentation
- Identify missing guides
- Understand user confusion points
- Generate doc improvement plan

### 4. Market Research

```python
# Analyze all open issues
async for result in fetch_github_issues(
    repo="competitor/repo",
    state="open",
    limit=100
):
    # Agent learns from competitor's user feedback
    pass
```

**Agent can:**
- Understand market needs
- Identify gaps in competitors
- Find opportunities
- Validate feature ideas

### 5. Self-Improvement

```python
# Analyze MassGen's own issues
async for result in fetch_github_issues(
    repo="Leezekun/MassGen",
    state="open",
    limit=50
):
    # Agent understands its own improvement areas
    pass
```

**Agent can:**
- Understand user pain points
- Prioritize its own development
- Self-evolve based on feedback
- Autonomously improve

## Self-Evolution Philosophy

**Traditional development:**
1. Developers decide features
2. Build features
3. Hope users want them

**Self-evolution approach:**
1. **Analyze** user feedback (GitHub issues)
2. **Identify** patterns and needs
3. **Prioritize** based on data
4. **Implement** what users actually want
5. **Repeat** continuously

**Key insight:** Let the market (users) guide development through their actual feedback.

## Engagement Scoring

Issues are scored based on:

**Comment count (50% weight):**
- More discussion = more important
- Indicates user investment

**Reaction count (30% weight):**
- 👍 reactions = user agreement
- ❤️ reactions = high value
- Total reactions indicate interest

**Recency (20% weight):**
- Newer issues weighted higher
- Prevents old issues dominating
- Reflects current needs

**Formula (approximate):**
```
score = (comments * 0.5) + (reactions * 0.3) + (recency_factor * 0.2)
```

## Rate Limits

**Unauthenticated:**
- 60 requests/hour to GitHub API
- Sufficient for periodic analysis

**Authenticated (with GITHUB_TOKEN):**
- 5,000 requests/hour
- Recommended for frequent use

**Best practice:**
- Cache results
- Don't fetch on every run
- Run analysis periodically (daily/weekly)

## Limitations

- **Read-only**: Cannot modify or create issues
- **Public repos only** (without authentication)
- **Rate limits**: Limited requests per hour
- **No PR analysis**: Focuses on issues, filters out PRs
- **GitHub-specific**: Only works with GitHub repositories
- **English-biased**: Analysis optimized for English content
- **No sentiment analysis**: Doesn't detect tone or sentiment
- **Max 100 issues**: API limits single fetch to 100 items

## Best Practices

**1. Focus on recent issues:**
```python
# Recent issues more relevant
state="open"  # Current user needs
```

**2. Use labels for filtering:**
```python
# Target specific categories
labels=["enhancement", "feature-request"]
```

**3. Set appropriate limits:**
```python
# Don't fetch more than needed
limit=20  # For quick analysis
limit=100  # For comprehensive review
```

**4. Analyze periodically:**
```python
# Weekly market analysis
schedule.every().week.do(analyze_issues)
```

**5. Combine with other data:**
```python
# Cross-reference with usage metrics
github_feedback = await fetch_github_issues(...)
usage_data = await get_usage_metrics(...)
# Holistic understanding
```

## Example: Autonomous Feature Planning

```python
# Agent autonomously decides what to build next

# Step 1: Fetch enhancement requests
enhancements = await fetch_github_issues(
    repo="Leezekun/MassGen",
    state="open",
    labels=["enhancement"],
    limit=50
)

# Step 2: Agent analyzes and ranks
# (LLM processes the enhancement data)

# Step 3: Agent identifies top 3 features
# Based on engagement, clustering, feasibility

# Step 4: Agent creates implementation plan
# Breaks down features into tasks

# Step 5: Agent begins implementation
# Or proposes plan to human developers

# This is self-evolution: agent guiding its own development
```

## Integration with MassGen

This tool demonstrates **self-evolution** capabilities:

**Recursive improvement:**
1. MassGen agent uses this tool
2. Analyzes MassGen's own GitHub issues
3. Identifies its own improvement areas
4. Prioritizes features users want
5. Implements improvements
6. Repeats

**Result:** Framework that improves itself based on user feedback.

## Common Issues

**Issue: Rate limit exceeded**
- Solution: Add GITHUB_TOKEN for authentication
- Or reduce fetch frequency

**Issue: No issues returned**
- Check repo name format: "owner/repo"
- Verify repo exists and is public
- Check label names are correct

**Issue: Too many PRs returned**
- Tool filters PRs automatically
- If seeing PRs, check filtering logic

**Issue: Analysis takes time**
- Normal for large limits (50-100 issues)
- Use smaller limits for faster results

## Future Enhancements

Potential additions to self-evolution tools:

1. **Pull request analysis**: Understand contribution patterns
2. **Sentiment analysis**: Detect user frustration or satisfaction
3. **Trend detection**: Identify emerging needs over time
4. **Cross-repo analysis**: Compare multiple repositories
5. **Automated responses**: Generate helpful replies to issues
6. **Feature spec generation**: Auto-create specs from issues

These enhancements would enable even more autonomous development.
