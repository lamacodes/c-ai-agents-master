# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python-based agent system using Firecrawl for web scraping/crawling capabilities. The project is in early development stage.

## Development Commands

### Package Management
This project uses **uv** as the package manager (not pip):

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add <package-name>

# Remove a dependency
uv remove <package-name>

# Update dependencies
uv lock --upgrade
```

### Running the Application
```bash
# Run the main script
uv run python main.py

# Or with uv's run shorthand
uv run main.py
```

## Architecture

### Technology Stack
- **Python**: 3.13
- **Package Manager**: uv
- **Key Dependencies**: firecrawl-py (web scraping/crawling)

### Project Structure
- `main.py`: Entry point for the application
- `pyproject.toml`: Project configuration and dependencies
- `uv.lock`: Locked dependency versions (managed by uv)
