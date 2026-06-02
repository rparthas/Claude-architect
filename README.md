# Claude Architect

Practice repository for the **Claude Architect** certification exam.

## Purpose

This repo contains exercises, experiments, and reference implementations used while preparing for the Anthropic Claude Architect exam. Topics covered:

- Claude API fundamentals (messages, streaming, tool use)
- Prompt engineering patterns
- Multi-turn conversation design
- Tool / function calling
- System prompt design
- Embeddings and retrieval
- Safety and responsible AI practices

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- An [Anthropic API key](https://console.anthropic.com/)

### Install

```bash
uv sync
```

### Configure API key

Copy `.env.example` to `.env` and set your key:

```bash
cp .env.example .env
# then edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### Run the API check

```bash
uv run python api_check.py
```

## Structure

```
.
├── pyproject.toml          # Project dependencies (uv)
├── README.md
├── api_check.py            # Sanity check — calls Claude and prints a response
└── claude_architect/       # Package for shared utilities (in progress)
```

## Resources

- [Anthropic Documentation](https://docs.anthropic.com)
- [Claude API Reference](https://docs.anthropic.com/en/api)
- [Anthropic Cookbook](https://github.com/anthropics/anthropic-cookbook)
- [Prompt Engineering Guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
