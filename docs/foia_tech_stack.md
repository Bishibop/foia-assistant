# FOIA Response Assistant - Tech Stack Document

## Overview
A desktop application for accelerating FOIA document review using AI-powered classification and human-in-the-loop learning.

## Core Technologies

### Language & Runtime
- **Python 3.11+** - Primary language for entire application
- **Virtual Environment** - Standard venv for dependency isolation

### GUI Framework
- **PyQt6** - Desktop application framework
  - Native OS appearance
  - Tabbed interface support
  - Built-in threading for background tasks
  - Qt Style Sheets for minimal styling

### AI/ML Stack
- **LangGraph** - Workflow orchestration
  - Document processing pipeline
  - Human-in-the-loop integration (planned)
  - State management via TypedDict
  - Cached workflow compilation with `@lru_cache`
- **LangChain** - LLM integration layer
  - OpenAI API connection via ChatOpenAI
  - JSON output parsing with Pydantic models
  - Structured prompt templates
- **OpenAI API** - Language model (MVP)
  - GPT-4o-mini for document classification (configurable)
  - API key via environment variable: `OPENAI_API_KEY`
  - JSON response format enforced

### Data Storage
- **In-Memory Only** - No persistence in current implementation
  - Document list maintained in ProcessingTab
  - Statistics tracked in ProcessingWorker
  - No SQLite implementation yet
- **JSON** - Format for OpenAI API responses and data passing

### Architecture Patterns
- **Single Process Application** - No client-server split
- **Multi-threaded**
  - Main thread: PyQt6 GUI
  - Background thread: ProcessingWorker (QThread) for LangGraph processing
- **Communication**: Qt signals/slots between threads
  - progress_updated, document_processing, document_processed signals
  - stats_updated for real-time statistics
- **Sequential Processing** - Documents processed one at a time

### User Interface
- **Tabbed Interface**:
  - **Processing Tab**: Implemented with real-time status panel
    - Folder selection and FOIA request input
    - Progress bar and activity log
    - Classification statistics display
  - **Review Tab**: Placeholder (Phase 4)
  - **Processed Tab**: Placeholder (Phase 6)
  - **Export Tab**: Not implemented

### Data Model
```python
@dataclass
class Document:
    filename: str
    content: str
    classification: str | None  # "responsive", "non_responsive", "uncertain"
    confidence: float | None
    justification: str | None
    exemptions: list[dict[str, Any]]  # [{"text": "555-1234", "type": "phone", "exemption_code": "b6", "start": 100, "end": 108}]
    human_decision: str | None = None
    human_feedback: str | None = None

class DocumentState(TypedDict):
    filename: str
    content: str
    foia_request: str
    classification: str | None
    confidence: float | None
    justification: str | None
    exemptions: list[dict] | None
    human_decision: str | None
    human_feedback: str | None
    patterns_learned: list[str] | None
    error: str | None
```

### File System Handling
- **Flat directory processing** - No nested folders in MVP
- **File discovery**: `Path(folder).glob("*.txt")`
- **Supported formats**: Plain text files only (.txt)

### Development Tools
- **pip** - Package management
- **git** - Version control  
- **Code Quality Tools**:
  - **Black** - Code formatter (line length: 88)
  - **Ruff** - Linter with strict rules (E, F, I, N, W, UP, B, C4, DTZ, T10, RUF, ANN, D, SIM)
  - **mypy** - Static type checker with strict settings
- **Logging** - Not implemented (debug prints removed)

### Deployment
- **PyInstaller** - Single executable creation (future)
- **Platform**: Windows/Mac/Linux compatible

## MVP Constraints
- **No configuration files** - Hardcoded settings except API key
- **No persistence** - Fresh start each session
- **No automated testing** - Manual testing only
- **Plain text only** - No PDF/OCR support
- **Single user** - No multi-user features
- **No authentication** - Direct file system access
- **Flat directories** - No recursive folder processing
- **Basic error handling** - Fail gracefully, no recovery

## Dependencies
```
# Production
pyqt6>=6.5.0
langgraph>=0.2.0
langchain>=0.3.0
langchain-openai>=0.2.0
openai>=1.0.0
python-dotenv>=1.0.0

# Development (optional)
black>=25.1.0
ruff>=0.12.0
mypy>=1.11.0
pytest>=8.3.0
pytest-cov>=5.0.0
pytest-asyncio>=0.24.0
pre-commit>=3.5.0
```

## Architecture Flow
```
User → ProcessingTab → ProcessingWorker (QThread) → LangGraph Workflow → OpenAI API
           ↑                                               ↓
           ←───────── Qt Signals (progress, results) ←─────┘
```

## Project Structure
```
src/
├── main.py                 # Application entry point
├── constants.py           # Centralized constants
├── config.py             # Model configuration
├── gui/
│   ├── main_window.py    # Main application window
│   ├── styles.py         # Centralized styling
│   ├── tabs/
│   │   ├── processing_tab.py
│   │   ├── review_tab.py
│   │   └── processed_tab.py
│   └── widgets/
│       └── status_panel.py
├── langgraph/
│   ├── state.py          # DocumentState TypedDict
│   ├── workflow.py       # Workflow compilation
│   └── nodes/
│       ├── classifier.py
│       ├── document_loader.py
│       └── exemption_detector.py
├── models/
│   └── document.py       # Document dataclass
├── processing/
│   └── worker.py         # Background processing thread
└── utils/
    └── error_handling.py # Standardized error responses
```

## Environment Setup
```bash
# Required environment variable (in .env file)
OPENAI_API_KEY=your-api-key-here

# The application loads .env automatically
```

## LangGraph Workflow (Implemented)
1. **Document Loading** (`load_document` node)
   - Validates file exists and is readable
   - Loads content if not already provided
   - Returns error state on failure
   
2. **Classification** (`classify_document` node)
   - Uses ChatOpenAI with JSON response format
   - Classifies as: responsive, non_responsive, or uncertain
   - Provides confidence score and justification
   - Falls back to "uncertain" on errors
   
3. **Exemption Detection** (`detect_exemptions` node)
   - Regex-based detection of PII
   - Detects SSNs (XXX-XX-XXXX format)
   - Detects phone numbers (XXX-XXX-XXXX format)
   - Marks with FOIA exemption code "b6"
   
4. **Human Review Integration** (Not implemented - Phase 4)
5. **Learning from Feedback** (Not implemented - Phase 5)
6. **Batch Processing** (Not implemented - processes sequentially)

## Future Considerations (Post-MVP)
- Local LLM support (Ollama)
- PDF processing capability
- Persistent learning data
- Configuration management
- Multi-user support
- Advanced exemption detection
- Recursive directory processing
- Robust error recovery