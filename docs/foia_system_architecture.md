# RAPID RESPONSE AI - System Architecture

## Overview
RAPID RESPONSE AI is a desktop application designed to accelerate Freedom of Information Act document review using AI-powered classification and human-in-the-loop decision making. The system features multi-request management, parallel processing for 4x performance improvement, intelligent feedback-based learning, and comprehensive export capabilities.

## System Goals
- Process thousands of documents efficiently with AI assistance (4x faster with parallel processing)
- Maintain human control over final decisions
- Learn from user feedback to improve accuracy through pattern recognition
- Support document deduplication to reduce review burden
- Ensure all processing happens locally for security
- Provide real-time visibility into processing status
- Manage multiple concurrent FOIA requests with isolated document stores

## High-Level Architecture

### Application Type
- **Desktop Application** - Runs entirely on user's local machine
- **Single-User Design** - No client-server architecture in MVP
- **Offline-First** - Only external dependency is OpenAI API

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                      PyQt6 GUI Layer                        │
│  ┌──────────────┬────────────┬────────────┬──────────────┐  │
│  │ Requests Tab │ Intake Tab │ Review Tab │ Finalize Tab │  │
│  │              │            │            │              │  │
│  └──────┬───────┴────────────┴────────────┴──────────────┘  │
│         │                                                    │
│  ┌──────▼────────────────────────────────────────────────┐  │
│  │            Status Panel (Real-time Updates)           │  │
│  └──────┬────────────────────────────────────────────────┘  │
└─────────┼───────────────────────────────────────────────────┘
          │ Qt Signals
┌─────────▼───────────────────────────────────────────────────┐
│               Request Management Layer                       │
│  ┌──────────────┬────────────────┬──────────────────────┐  │
│  │Request Manager│ Document Store  │ Feedback Manager    │  │
│  │(CRUD Ops)    │ (Request Docs)  │ (Pattern Learning)  │  │
│  └──────────────┴────────────────┴──────────────────────┘  │
└─────────┬───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│               Processing Worker (QThread)                    │
│         Manages background document processing               │
└─────────┬───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│            Parallel Document Processor                       │
│  ┌─────────────┬─────────────┬─────────────────────────┐   │
│  │ Worker Pool │ Task Queue  │ Progress Aggregation    │   │
│  │ (4 workers) │ Distribution│ & Rate Calculation      │   │
│  └─────────────┴─────────────┴─────────────────────────┘   │
└─────────┬───────────────────────────────────────────────────┘
          │ (multiprocessing)
┌─────────▼───────────────────────────────────────────────────┐
│                  LangGraph Workflow Engine                   │
│  ┌────────────┬──────────────┬────────────────────────┐    │
│  │ Document   │ AI           │ PII Detection          │    │
│  │ Loader     │ Classifier   │ (Exemptions)           │    │
│  │            │ (w/Feedback) │                        │    │
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

### Export Libraries
- **openpyxl** - Excel file generation
  - Creates XLSX files with multiple sheets
  - Supports cell styling and formatting
  - Auto-adjusts column widths
- **reportlab** - PDF generation
  - Professional report formatting
  - Table layouts with styling
  - Page management and flowables

### AI/Embedding Libraries (Planned)
- **text-embedding-ada-002** - Document embeddings for deduplication
  - Semantic similarity detection
  - Near-duplicate identification
  - Content-based clustering

### Data Storage
- **In-Memory Only** - No persistence in current implementation
  - Multiple FOIA requests managed by RequestManager
  - Documents isolated by request in DocumentStore
  - Document list maintained per request
  - Statistics tracked per request
  - Review queue scoped to active request
  - Processed documents stored per request
  - Feedback stored per request for learning
  - No SQLite implementation yet
- **JSON** - Format for OpenAI API responses and data passing
- **CSV/JSON/Excel/PDF** - Multiple export formats for document metadata and reports

## Architecture Patterns

### Threading Model
- **Main Thread**: PyQt6 GUI event loop
- **Worker Thread**: ProcessingWorker (QThread) for document processing
- **Worker Processes**: ParallelDocumentProcessor spawns up to 4 worker processes
- **Communication**: 
  - Qt signals/slots for thread-safe GUI updates
  - Multiprocessing queues for inter-process communication
  - Progress aggregation from multiple workers
- **Signals**:
  - `progress_updated(current, total)` - Progress tracking
  - `document_processing(filename)` - Current file indicator
  - `document_processed(Document)` - Completed document data
  - `stats_updated(responsive, non_responsive, uncertain)` - Statistics
  - `processing_complete()` - Batch completion signal
  - `error_occurred(str)` - Error propagation
  - `documents_processed(list[Document])` - Documents ready for review
  - `processing_rate_updated(float)` - Documents per minute
  - `worker_count_updated(int)` - Active worker processes
- **Tab Communication Signals**:
  - `folder_selected(Path)` - Folder selection from IntakeTab
  - `processing_started()` - Clear all tabs when reprocessing
  - `review_completed(Document)` - Document decision made
  - `all_documents_reviewed()` - Enable finalize actions
  - `request_switched()` - Active request changed in RequestManager
  - `request_created(FOIARequest)` - New request created
  - `request_updated(FOIARequest)` - Request details modified
  - `request_deleted(str)` - Request removed from system
  - `reprocess_requested()` - User wants to reprocess with feedback

### Processing Pipeline
1. User creates or selects FOIA request in Requests tab
2. User selects folder for document processing in Intake tab
3. ProcessingWorker thread spawned with document list and active request ID
4. For batches >3 documents, ParallelDocumentProcessor creates worker pool
5. Documents distributed to workers via task queue
6. Each worker process:
   - Creates its own LangGraph workflow instance
   - Receives feedback_examples if reprocessing
   - Processes documents through the workflow
   - Returns results via result queue
7. Progress aggregated and emitted via Qt signals
8. GUI updates in real-time with progress, rate, and worker count
9. Statistics accumulated per request and displayed
10. On completion, documents stored in DocumentStore for the request
11. User reviews documents in Review tab (filtered by active request)
12. Human decisions captured and stored in Document objects
13. Corrections automatically captured in FeedbackManager
14. User can reprocess unreviewed documents with feedback
15. Reviewed documents available in Finalize tab (filtered by active request)
16. User can export documents (CSV, JSON, Excel, PDF) or generate FOIA response package per request

### Error Handling Strategy
- Graceful degradation on errors
- Failed classifications marked as "uncertain"
- Errors logged to activity panel
- Processing continues despite individual failures

## Data Model

### Core Data Structures

```python
@dataclass
class FOIARequest:
    """Represents a single FOIA request being processed"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    foia_request_text: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    deadline: datetime | None = None
    status: str = "draft"  # draft, processing, review, complete
    
    # Statistics
    total_documents: int = 0
    processed_documents: int = 0
    responsive_count: int = 0
    non_responsive_count: int = 0
    uncertain_count: int = 0
    
    # Document associations (in-memory only)
    document_folder: Path | None = None
    processed_document_ids: set[str] = field(default_factory=set)
    reviewed_document_ids: set[str] = field(default_factory=set)

@dataclass
class Document:
    filename: str
    content: str
    classification: str | None  # "responsive", "non_responsive", "uncertain", "duplicate"
    confidence: float | None
    justification: str | None
    exemptions: list[dict[str, Any]]  # [{"text": "555-1234", "type": "phone", "exemption_code": "b6", "start": 100, "end": 108}]
    human_decision: str | None = None
    human_feedback: str | None = None
    
    # Duplicate detection fields (for deduplication feature)
    is_duplicate: bool = False
    duplicate_of: str | None = None  # Filename of the primary document
    similarity_score: float | None = None  # Cosine similarity score
    content_hash: str | None = None  # SHA-256 hash for exact duplicates
    embedding_generated: bool = False  # Whether embedding was created

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

@dataclass
class ProcessingTask:
    """Represents a document processing task for parallel workers"""
    document_path: Path
    foia_request: str
    task_id: int
    feedback_examples: list[dict] | None = None
    embedding_metadata: Document | None = None  # Pre-computed duplicate info

@dataclass
class ProcessingResult:
    """Represents the result of a document processing task"""
    task_id: int
    document: Document | None = None
    error: str | None = None
    processing_time: float = 0.0

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
    feedback_examples: list[dict] | None  # Previous corrections for few-shot learning
    error: str | None

@dataclass  
class FeedbackEntry:
    """Represents a single user correction to an AI classification."""
    document_id: str
    request_id: str
    original_classification: str
    human_decision: str
    original_confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    document_snippet: str = ""  # First 200 chars of document
    correction_reason: str = ""
```

### State Management
- **Request Management**: RequestManager handles CRUD operations and active request
- **Document Isolation**: DocumentStore maintains request-scoped document collections
- **Document Processing**: Document state flows through LangGraph nodes
- Each node can read and modify state
- Final state converted to Document dataclass
- Documents associated with active request via DocumentStore
- **Learning Feedback**: FeedbackManager tracks user corrections per request
  - Stores original vs corrected classifications
  - Captures document snippets for context
  - Provides pattern analysis for reprocessing
- **Duplicate Tracking**: Document state includes duplicate detection metadata
- No persistent storage between sessions

## LangGraph Workflow Design

### Learning Feedback System

The system implements a learning mechanism to improve classification accuracy based on user corrections:

1. **Feedback Capture** - When users override AI classifications during review, the system automatically captures:
   - Original AI classification and confidence
   - Human-corrected classification
   - Document snippet (first 200 chars) for context
   - Request-scoped feedback storage

2. **Feedback Application** - During reprocessing:
   - Previous corrections are injected into classification prompts as few-shot examples
   - AI receives detailed context about patterns to look for
   - Emphasis on content similarity rather than just document type
   - Pattern matching focuses on keywords, topics, and project names

3. **Reprocessing Workflow**:
   - User clicks "Reprocess Unreviewed with Feedback" in Review tab
   - Only unreviewed documents are reprocessed (reviewed documents retained)
   - All feedback examples included in every classification
   - No confirmation dialog for immediate processing
   - Filename pattern analysis helps AI understand document organization
   - Content pattern extraction identifies key topics and terms
   - Pattern-based learning applies corrections to similar documents

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
   - Classifies as: responsive, non_responsive, uncertain, or duplicate
   - Provides confidence score (0-1) and justification
   - Falls back to "uncertain" on errors
   - Accepts feedback_examples in state for few-shot learning
   - Enhanced prompts during reprocessing with feedback context
   - Pattern matching based on content similarity and filename patterns
   - Intelligent pattern recognition:
     - Filename prefix analysis (email_, memo_, report_)
     - Content keyword extraction from corrections
     - Unanimous pattern detection (100% same correction)
     - Priority-based classification rules
   
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
- **Requests Tab** (New)
  - Request list table with name, deadline, status, progress
  - Active request indicator with radio button
  - Details panel for viewing/editing request
  - Create/Delete request functionality
  - Active request display in header
  - Auto-creates 5 default requests on startup
- **Intake Tab**
  - Folder selection browser
  - Active request display (top-right)
  - Real-time status panel
  - Process button and controls
  - 40/60 split layout (configuration/status)
  - Validates active request has FOIA text
- **Review Tab**
  - Document viewer with PII highlighting
  - AI classification display with confidence
  - Decision controls (Approve/Override)
  - Keyboard shortcuts (Space, R, N, U)
  - Review queue filtered by active request
  - Active request display (top-right)
  - 40/60 split layout (document/decision)
  - Previous/Next navigation buttons
  - Automatic feedback capture on overrides
  - "Reprocess Unreviewed with Feedback" button
  - Feedback statistics display (count, patterns)
  - Override non-duplicate functionality (D key)
  - Reclassification for documents marked as duplicates
- **Finalize Tab**
  - Document table filtered by active request
  - Statistics bar showing request-specific totals
  - Document viewer with decision information
  - Export options (CSV, JSON, Excel, PDF)
  - Generate FOIA Package functionality
  - Flag for review capability
  - Active request display (top-right)
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
- **Parallel Processing**: Up to 4 concurrent worker processes
- **Automatic Optimization**: 
  - Sequential processing for ≤3 documents
  - Parallel processing for >3 documents
- **Processing Speed**: 
  - Sequential: ~2-5 seconds per document
  - Parallel: ~4x speedup for larger batches
  - Duplicate detection adds minimal overhead (~0.1s per doc)
- **Batch Distribution**: Dynamic batch sizing based on document count
- **Worker Management**: 
  - Capped at 4 workers to prevent system overload
  - Graceful fallback to sequential on worker failures
- **Memory Usage**: 
  - Base usage proportional to document count
  - Additional ~50MB per worker process
- **Real-time Monitoring**:
  - Processing rate in documents/minute
  - Active worker count display
  - Per-document progress updates
- **No caching between sessions**

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
│   │   ├── requests_tab.py  # Request management interface (new)
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
│   ├── request.py        # FOIARequest dataclass (new)
│   ├── document.py       # Document dataclass
│   ├── feedback.py       # FeedbackEntry dataclass
│   └── classification.py # Classification enum
├── processing/
│   ├── request_manager.py  # Request CRUD operations (new)
│   ├── document_store.py   # Request-scoped documents (new)
│   ├── feedback_manager.py # User correction tracking
│   ├── worker.py          # Background processing thread
│   └── parallel_worker.py  # Multiprocessing document processor
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
openpyxl >= 3.1.0
reportlab >= 4.0.0

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
- **No persistence** - Fresh start each session (all requests lost on exit)
- **No automated testing** - Manual testing only
- **Plain text only** - No PDF/OCR support
- **Single user** - No multi-user features
- **No authentication** - Direct file system access
- **Flat directories** - No recursive folder processing
- **Basic error handling** - Fail gracefully, no recovery
- **Multiple export formats** - CSV, JSON, Excel (XLSX), and PDF
- **Request isolation** - Documents cannot be shared between requests

## Key Features

### Multi-Request FOIA Management
- Concurrent support for multiple FOIA requests with isolated document processing
- Request-specific document stores prevent cross-contamination
- Visual progress tracking per request
- Request statistics and deadline management
- Active request context maintained across all tabs

### Multi-Request Management (New)
- Create and manage multiple FOIA requests simultaneously
- Switch between requests with single click
- Track progress and statistics per request
- Maintain document isolation between requests
- Edit request details (name, description, FOIA text, deadline)
- Visual progress indicators per request

### Document Processing
- Batch processing of text documents
- AI-powered classification with confidence scores
- Automatic PII detection and exemption marking
- Real-time progress tracking with docs/minute display
- Request-scoped document storage
- Parallel processing with up to 4x performance improvement
- Worker process management with automatic optimization
- Duplicate detection support (embedding infrastructure ready)

### Review Workflow
- Sequential document review with AI recommendations
- Override capabilities with automatic feedback capture
- Keyboard shortcuts for efficiency
- Visual highlighting of detected PII
- Review queue filtered by active request
- Reprocess unreviewed documents with learned feedback

### Learning Feedback System
- Automatic capture of user corrections during review
- Request-scoped feedback storage (no cross-contamination)
- Few-shot learning with previous corrections as examples
- Reprocess only unreviewed documents with feedback
- Advanced pattern recognition:
  - Filename prefix pattern analysis
  - Content keyword and topic extraction
  - Unanimous pattern detection and application
  - Smart generalization from single examples
- Real-time feedback statistics display
- Pattern-based classification priority rules

### Export and Package Generation
- Multiple export formats:
  - CSV with full metadata
  - JSON for data interchange
  - Excel (XLSX) with formatted sheets
  - PDF with professional report layout
- FOIA response package generation per request
- Exemption log creation
- Processing summary reports
- Cover letter templates
- Export scoped to active request
- Exports saved to ~/Documents/FOIA_Exports/

### User Experience
- Drag-and-drop folder selection
- Real-time statistics and progress
- Search and filter capabilities
- Responsive split-pane layouts
- Platform-specific file manager integration
- Consistent request context display across tabs
- Keyboard shortcuts for efficient review (Space, R, N, U, D)
- Activity logging with timestamps
- Worker status indicators
- Processing rate display (docs/minute)

## Advanced Technical Features

### Feedback-Based Learning Implementation
The system implements sophisticated pattern recognition for learning from user corrections:

1. **Filename Pattern Analysis**
   - Extracts document prefixes (email_, memo_, report_)
   - Tracks correction patterns by document type
   - Identifies unanimous patterns (100% corrections same way)
   - Applies patterns to similar documents automatically

2. **Content Pattern Extraction**
   - Analyzes corrected documents for key terms and topics
   - Uses regex to extract capitalized phrases, quoted terms
   - Identifies project names and technical terminology
   - Builds keyword lists for pattern matching

3. **Classification Priority Rules**
   - Unanimous filename patterns applied immediately
   - Content matches trigger pattern-based classification
   - Strong patterns (>80% agreement) heavily weighted
   - Fallback to standard FOIA classification for unclear cases

### Duplicate Detection Infrastructure
The system is architected to support document deduplication:

1. **Embedding Support**
   - Document model includes embedding metadata fields
   - Support for similarity scores and duplicate relationships
   - Content hashing for exact duplicate detection
   - Override functionality for false positive duplicates

2. **Processing Integration**
   - ParallelDocumentProcessor accepts embedding metadata
   - Duplicate documents tracked separately in progress
   - Classification workflow handles duplicate state
   - Review interface shows duplicate indicators

### Performance Optimizations

1. **Parallel Processing Architecture**
   - Dynamic batch sizing based on document count
   - Worker pool management with graceful degradation
   - Task queue distribution for load balancing
   - Progress aggregation from multiple workers
   - Automatic fallback to sequential for small batches

2. **Logging Optimization**
   - Reduced verbosity with strategic log placement
   - Debug-level logging for detailed tracing
   - Info-level summaries for key operations
   - Pattern analysis logged once per batch

3. **Memory Management**
   - Efficient in-memory storage with request isolation
   - Lazy loading of document content
   - Compiled regex patterns cached at module level
   - LangGraph workflow cached with @lru_cache

## Implementation Status

### Completed Features (Epic 2)
- ✅ Multi-request management system with full CRUD operations
- ✅ Request-scoped document isolation and storage
- ✅ Parallel processing with 4x performance improvement
- ✅ Feedback capture and learning system
- ✅ Pattern-based classification improvements
- ✅ Excel and PDF export capabilities
- ✅ Real-time progress monitoring with worker status
- ✅ Keyboard shortcuts for efficient review
- ✅ Reprocess with feedback functionality

### In Progress / Architecture Ready
- 🏗️ Document deduplication (embedding infrastructure in place)
- 🏗️ Duplicate override functionality (UI implemented)

### Planned Features
- 📋 Automated redaction system (Epic 2 Days 6-7)
- 📋 Persistent storage (SQLite)
- 📋 Advanced configuration options
- 📋 Batch processing improvements
- 📋 Enhanced error recovery

## Summary

RAPID RESPONSE AI represents a sophisticated FOIA document processing system that combines:
- **Performance**: 4x faster processing through parallelization
- **Intelligence**: Pattern-based learning from user feedback
- **Flexibility**: Multi-request management with isolation
- **Usability**: Intuitive UI with keyboard shortcuts
- **Extensibility**: Architecture ready for deduplication and future enhancements

The system successfully balances automation with human control, ensuring efficient document review while maintaining accuracy through continuous learning.