# FOIA Response Assistant

An AI-powered tool that classifies documents for FOIA (Freedom of Information Act) requests. It uses LangGraph and OpenAI to determine if documents are responsive, non-responsive, or uncertain based on a given FOIA request.

## Requirements

- Python 3.11+
- OpenAI API key

## Setup

1. Clone and enter the repository:
   ```bash
   git clone <repository-url>
   cd foia-assistant
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Configure API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

## Usage

Launch the GUI application:
```bash
source venv/bin/activate && python -m src.main
```

To test the application:
1. Click "Browse" and select the `sample_docs` folder
2. In the FOIA Request field, enter: "All emails about Project Blue Sky"
3. Click "Process Documents" to see the classification results

## Documentation

See the `docs/` folder for detailed documentation:
- [Implementation Plan](docs/foia_implementation_plan.md)
- [Problem Space Analysis](docs/foia_brainlift.md)
- [Technical Stack](docs/foia_tech_stack.md)