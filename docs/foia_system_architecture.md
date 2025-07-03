# RAPID RESPONSE AI - System Architecture

## Overview
RAPID RESPONSE AI is a desktop application designed to accelerate Freedom of Information Act document review using AI-powered classification and human-in-the-loop decision making.

## System Goals
- Process thousands of documents efficiently with AI assistance
- Maintain human control over final decisions
- Learn from user feedback to improve accuracy
- Ensure all processing happens locally for security
- Provide real-time visibility into processing status

## High-Level Architecture

### Application Type
- **Desktop Application** - Runs entirely on user's local machine
- **Single-User Design** - No client-server architecture in MVP
- **Offline-First** - Only external dependency is OpenAI API

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                      PyQt6 GUI Layer                        │
│  ┌──────────────┬─────────────┬──────────────────────────┐  │
│  │ Intake Tab   │ Review Tab  │ Finalize Tab             │  │
│  │              │             │                          │  │
│  └──────┬───────┴─────────────┴──────────────────────────┘  │
│         │                                                    │
│  ┌──────▼────────────────────────────────────────────────┐  │
│  │            Status Panel (Real-time Updates)           │  │
│  └──────┬────────────────────────────────────────────────┘  │
└─────────┼───────────────────────────────────────────────────┘
          │ Qt Signals
┌─────────▼───────────────────────────────────────────────────┐
│               Processing Worker (QThread)                    │
│         Manages background document processing               │
└─────────┬───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│                  LangGraph Workflow Engine                   │
│  ┌────────────┬──────────────┬────────────────────────┐    │
│  │ Document   │ AI           │ PII Detection          │    │
│  │ Loader     │ Classifier   │ (Exemptions)           │    │
│  └────────────┴──────────────┴────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                      External Services
                    ┌─────────────────┐
                    │  OpenAI API     │
                    │  (GPT-4o-mini)  │
                    └─────────────────┘
```

## Technical Stack

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
  - Document list maintained in IntakeTab
  - Statistics tracked in ProcessingWorker
  - Review queue maintained in ReviewTab
  - Processed documents stored in FinalizeTab
  - No SQLite implementation yet
- **JSON** - Format for OpenAI API responses and data passing
- **CSV** - Export format for document metadata and exemption logs

## Architecture Patterns

### Threading Model
- **Main Thread**: PyQt6 GUI event loop
- **Worker Thread**: ProcessingWorker (QThread) for document processing
- **Communication**: Qt signals/slots for thread-safe updates
  - `progress_updated(current, total)` - Progress tracking
  - `document_processing(filename)` - Current file indicator
  - `document_processed(Document)` - Completed document data
  - `stats_updated(responsive, non_responsive, uncertain)` - Statistics
  - `processing_complete()` - Batch completion signal
  - `error_occurred(str)` - Error propagation
  - `documents_processed(list[Document])` - Documents ready for review
- **Tab Communication Signals**:
  - `folder_selected(Path)` - Folder selection from IntakeTab
  - `processing_started()` - Clear all tabs when reprocessing
  - `review_completed(Document)` - Document decision made
  - `all_documents_reviewed()` - Enable finalize actions

### Processing Pipeline
1. User selects folder and enters FOIA request in Intake tab
2. ProcessingWorker thread spawned with document list
3. Documents processed sequentially through LangGraph
4. Each document result emitted via Qt signal
5. GUI updates in real-time with progress and results
6. Statistics accumulated and displayed
7. On completion, documents sent to Review tab queue
8. User reviews each document with AI recommendations
9. Human decisions captured and stored in Document objects
10. Reviewed documents sent to Finalize tab
11. User can export documents or generate FOIA response package

### Error Handling Strategy
- Graceful degradation on errors
- Failed classifications marked as "uncertain"
- Errors logged to activity panel
- Processing continues despite individual failures

## Data Model

### Core Data Structures

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

@dataclass
class ProcessedDocument:
    document: Document
    review_timestamp: datetime
    processing_time: float  # seconds
    flagged_for_review: bool = False

class Classification(str, Enum):
    RESPONSIVE = "responsive"
    NON_RESPONSIVE = "non_responsive"
    UNCERTAIN = "uncertain"

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

### State Management
- Document state flows through LangGraph nodes
- Each node can read and modify state
- Final state converted to Document dataclass
- No persistent storage between sessions

## LangGraph Workflow Design

### Workflow Architecture
```python
workflow = StateGraph(DocumentState)
workflow.add_node("load_document", load_document)
workflow.add_node("classify", classify_document)
workflow.add_node("detect_exemptions", detect_exemptions)
workflow.set_entry_point("load_document")
workflow.add_edge("load_document", "classify")
workflow.add_edge("classify", "detect_exemptions")
workflow.add_edge("detect_exemptions", END)
```

### Node Implementations

1. **Document Loading** (`load_document`)
   - Validates file exists and is readable
   - Loads content if not already provided
   - Returns error state on failure
   
2. **Classification** (`classify_document`)
   - Uses ChatOpenAI with JSON response format
   - Classifies as: responsive, non_responsive, or uncertain
   - Provides confidence score (0-1) and justification
   - Falls back to "uncertain" on errors
   
3. **Exemption Detection** (`detect_exemptions`)
   - Regex-based detection of PII (only for responsive documents)
   - Detects SSNs (XXX-XX-XXXX format)
   - Detects phone numbers (multiple US formats)
   - Detects email addresses (excluding government domains)
   - Marks with FOIA exemption code "b6"
   - Records position information for highlighting
   - Validates and warns about overlapping exemptions

### Export and Package Generation

4. **Document Export** (Finalize Tab)
   - Export selected or all documents
   - Supports CSV and JSON formats
   - Includes metadata and review decisions
   
5. **FOIA Package Generation**
   - Copies responsive documents to package folder
   - Generates exemption log CSV
   - Creates processing summary report
   - Provides cover letter template

## User Interface Design

### Tabbed Interface Structure
- **Intake Tab**
  - Folder selection browser
  - FOIA request text input
  - Real-time status panel
  - Process button and controls
  - 40/60 split layout (configuration/status)
- **Review Tab**
  - Document viewer with PII highlighting
  - AI classification display with confidence
  - Decision controls (Approve/Override)
  - Keyboard shortcuts (Space, R, N, U)
  - Review queue navigation
  - 40/60 split layout (document/decision)
  - Previous/Next navigation buttons
- **Finalize Tab**
  - Document table with search and filtering
  - Statistics bar showing totals and agreement rate
  - Document viewer with decision information
  - Export options (CSV, JSON, Excel*, PDF*)
  - Generate FOIA Package functionality
  - Flag for review capability
  - 60/40 split layout (document list/viewer)

### Status Panel Components
- Progress bar with current/total documents
- Statistics cards (Responsive/Non-Responsive/Uncertain)
- Activity log with timestamps
- Current processing filename indicator

## Code Quality and Standards
- **Constants Management**
  - All UI dimensions and styling in `constants.py`
  - Button styles defined as constants
  - Layout margins and spacing standardized
- **Utility Functions**
  - Statistics calculation extracted to `utils/statistics.py`
  - Style factory functions in `gui/styles.py`
- **Type Safety**
  - Classification enum for document types
  - Type hints throughout codebase
  - Dataclasses for structured data
- **Code Organization**
  - Methods broken down to single responsibility
  - Consistent naming conventions
  - Clear separation of UI and business logic

## Security Considerations
- All processing happens locally
- Only external API call is to OpenAI
- No data persistence between sessions
- No authentication layer (local desktop app)
- API key stored in local .env file

## Performance Characteristics
- Sequential document processing (no parallelization)
- ~2-5 seconds per document (depends on API latency)
- Memory usage proportional to document count
- No caching between sessions

## File System Integration
- **Flat directory processing** - No nested folders in MVP
- **File discovery**: `Path(folder).glob("*.txt")`
- **Supported formats**: Plain text files only (.txt)
- **Encoding**: UTF-8 with error handling

## Development Infrastructure

### Code Quality Tools
- **Black** - Code formatter (line length: 88)
- **Ruff** - Linter with strict rules
- **mypy** - Static type checker with strict settings

### Testing Strategy
- Manual testing only in MVP
- Test documents in `sample_docs/`
- Future: pytest for unit tests

## Deployment Architecture
- **Development**: Run from source with virtual environment
- **Future**: PyInstaller for single executable
- **Platform Support**: Windows/Mac/Linux compatible
- **No installer**: Simple executable distribution

## Project Structure
```
src/
├── main.py                 # Application entry point
├── constants.py           # Centralized constants
├── config.py             # Model configuration
├── gui/
│   ├── main_window.py    # Main application window
│   ├── styles.py         # Centralized styling & UI helpers
│   ├── tabs/
│   │   ├── intake_tab.py    # Document intake and processing
│   │   ├── review_tab.py    # Document review interface
│   │   └── finalize_tab.py  # Export and package generation
│   └── widgets/
│       ├── status_panel.py
│       ├── document_viewer.py  # PII highlighting viewer
│       └── decision_panel.py   # Review decision UI
├── langgraph/
│   ├── state.py          # DocumentState TypedDict
│   ├── workflow.py       # Workflow compilation
│   └── nodes/
│       ├── classifier.py
│       ├── document_loader.py
│       └── exemption_detector.py
├── models/
│   ├── document.py       # Document dataclass
│   └── classification.py # Classification enum
├── processing/
│   └── worker.py         # Background processing thread
└── utils/
    ├── error_handling.py # Standardized error responses
    └── statistics.py     # Document statistics calculations
```

## Configuration Management
- Model selection in `config.py`
- UI constants in `constants.py`:
  - Window settings and titles
  - Button styles (primary, secondary, danger, warning, decision)
  - Layout dimensions and margins
  - Table column widths
  - UI symbols and emojis
- Styling in `gui/styles.py` (factory functions for UI elements)
- Regex patterns compiled at module level for performance
- No user-facing configuration files

## Dependencies
```toml
# Production
pyqt6 >= 6.5.0
langgraph >= 0.2.0
langchain >= 0.3.0
langchain-openai >= 0.2.0
openai >= 1.0.0
python-dotenv >= 1.0.0

# Development
black >= 25.1.0
ruff >= 0.12.0
mypy >= 1.11.0
pytest >= 8.3.0
pytest-cov >= 5.0.0
pytest-asyncio >= 0.24.0
pre-commit >= 3.5.0
```

## Current System Constraints
- **No configuration files** - Hardcoded settings except API key
- **No persistence** - Fresh start each session
- **No automated testing** - Manual testing only
- **Plain text only** - No PDF/OCR support
- **Single user** - No multi-user features
- **No authentication** - Direct file system access
- **Flat directories** - No recursive folder processing
- **Basic error handling** - Fail gracefully, no recovery
- **Limited export formats** - CSV and JSON only (Excel/PDF placeholders)

## Key Features

### Document Processing
- Batch processing of text documents
- AI-powered classification with confidence scores
- Automatic PII detection and exemption marking
- Real-time progress tracking

### Review Workflow
- Sequential document review with AI recommendations
- Override capabilities with feedback capture
- Keyboard shortcuts for efficiency
- Visual highlighting of detected PII

### Export and Package Generation
- Multiple export formats (CSV, JSON)
- FOIA response package generation
- Exemption log creation
- Processing summary reports
- Cover letter templates

### User Experience
- Drag-and-drop folder selection
- Real-time statistics and progress
- Search and filter capabilities
- Responsive split-pane layouts
- Platform-specific file manager integration