<!-- mcp-name: io.github.SamYatesSmith/tru8 -->

# tru8-mcp

MCP server for [Tru8 Evidence Research](https://www.trueight.com) — structured evidence research tools for AI agents.

Submit a claim or URL, get back source-traced evidence organized by tier (primary/reporting/commentary) and type (data/official/news/analysis/opinion/academic), with element decomposition and relationship mapping.

## Two ways to connect

**Hosted (nothing to install).** Point any MCP client that supports remote
servers at:

```
https://api.trueight.com/mcp
```

Authenticate with your Tru8 API key, sent either as an `X-API-Key` header or
as `Authorization: Bearer`. Each request is authenticated on its own, so one
endpoint serves every user without their keys ever meeting.

**Local (this package).** Runs on your own machine over stdio, which means
your API key never leaves it. Use this if you would rather not send a
credential through anyone else's infrastructure.

Both serve the identical tools from the identical code — pick whichever suits.

## Quick Start

```bash
pip install tru8-mcp
```

Or run without installing:

```bash
uvx tru8-mcp
```

Set your API key:

```bash
export TRU8_API_KEY=tru8_sk_...
```

Create an API key at your [Tru8 dashboard](https://www.trueight.com/dashboard/settings) under Settings > Developer.

## Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tru8": {
      "command": "tru8-mcp",
      "env": {
        "TRU8_API_KEY": "tru8_sk_..."
      }
    }
  }
}
```

### Cline / Cursor

Add to your MCP settings:

```json
{
  "mcpServers": {
    "tru8": {
      "command": "uvx",
      "args": ["tru8-mcp"],
      "env": {
        "TRU8_API_KEY": "tru8_sk_..."
      }
    }
  }
}
```

### From source

```bash
git clone https://github.com/SamYatesSmith/tru8-mcp.git
cd tru8-mcp
pip install -e .
tru8-mcp
```

## Tools

| Tool | Description | Typical time |
|------|-------------|-------------|
| `tru8_check` | Evidence research for a claim or article URL | 15-120s |
| `tru8_get_result` | Retrieve completed check with computed analytics | <1s |
| `tru8_get_result_raw` | Retrieve raw check data without computed analytics | <1s |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TRU8_API_KEY` | Yes | API key (`tru8_sk_...`). Create at dashboard > Settings > Developer. |
| `TRU8_API_URL` | No | API base URL. Default: `https://api.trueight.com` |

## Security

Store API keys in environment variables or a secrets manager. Never hardcode keys in source code. If a key is compromised, revoke it immediately at your dashboard.
