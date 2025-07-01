# FOIA Response Assistant

An AI-powered document classification tool for FOIA (Freedom of Information Act) officers to efficiently process document requests.

## Overview

This application uses LangGraph and OpenAI to automatically classify documents as responsive, non-responsive, or uncertain based on FOIA requests. It includes PII detection for exemptions and learns from human feedback to improve classifications over time.

## Requirements

- Python 3.11 or higher
- OpenAI API key

## Setup

1. Clone the repository and navigate to the project directory:
   ```bash
   cd foia-assistant
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   make install-dev
   # or manually:
   pip install -e ".[dev]"
   ```

4. Set up your OpenAI API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

## Usage

### Running the Document Processor

Process documents from the sample folder:
```bash
python test_langgraph.py --folder ./sample_docs --request "All emails about Project Blue Sky"
```

### Development Workflow

Run code quality checks:
```bash
make check  # Runs formatting, linting, and type checking
```

Individual commands:
```bash
make format      # Format code with Black
make lint        # Lint with Ruff
make type-check  # Type check with mypy
```

## Project Structure

```
foia-assistant/
├── src/
│   ├── langgraph/       # LangGraph workflow components
│   ├── models/          # Data models
│   └── gui/             # PyQt6 GUI (Phase 2+)
├── sample_docs/         # Test documents
├── docs/                # Project documentation
├── pyproject.toml       # Project configuration
└── Makefile            # Development commands
```

## Development Status

- ✅ Phase 0: Environment Setup
- ✅ Phase 1: LangGraph Workflow
- ✅ Phase 1.5: Code Quality Setup
- ⏳ Phase 2: PyQt6 GUI (Next)

See [docs/foia_implementation_plan.md](docs/foia_implementation_plan.md) for the full development roadmap.

## Testing

Run the test script to verify the workflow:
```bash
make test
```

This will process the sample documents and display classification results.

## Contributing

1. Ensure all code passes quality checks: `make check`
2. Follow the existing code style and conventions
3. Add type hints to all new functions
4. Update tests for new functionality