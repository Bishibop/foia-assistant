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
  - Human-in-the-loop integration
  - State management for learning
- **LangChain** - LLM integration layer
  - OpenAI API connection
  - Prompt management
  - Document processing utilities
- **OpenAI API** - Language model (MVP)
  - GPT-4 for document classification
  - GPT-3.5-turbo for faster operations
  - API key via environment variable: `OPENAI_API_KEY`

### Data Storage
- **SQLite** - Session state only (no persistence in MVP)
  - Document queue management
  - Temporary classification storage
  - Review status tracking
- **JSON** - Format for internal data passing

### Architecture Patterns
- **Single Process Application** - No client-server split
- **Multi-threaded**
  - Main thread: PyQt6 GUI
  - Background thread: LangGraph processing
- **Communication**: Qt signals/slots between threads
- **Queue-based** document processing pipeline

### User Interface
- **Tabbed Interface**:
  - **Processing Tab**: Real-time LangGraph status and metrics
  - **Review Tab**: Document viewer with AI analysis
  - **Processed Tab**: List of completed documents with classifications
  - **Export Tab**: Export options and summary statistics

### Data Model
```python
@dataclass
class Document:
    filename: str
    content: str
    classification: str  # "responsive", "non_responsive", "uncertain"
    confidence: float
    justification: str
    exemptions: List[Dict[str, Any]]  # [{"text": "555-1234", "type": "phone", "start": 100, "end": 108}]
    human_decision: Optional[str] = None
    human_feedback: Optional[str] = None
```

### File System Handling
- **Flat directory processing** - No nested folders in MVP
- **File discovery**: `Path(folder).glob("*.txt")`
- **Supported formats**: Plain text files only (.txt)

### Development Tools
- **pip** - Package management
- **git** - Version control
- **Basic logging** - Python's built-in logging module

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
pyqt6>=6.5.0
langgraph>=0.1.0
langchain>=0.1.0
langchain-openai>=0.0.5
openai>=1.0.0
python-dotenv>=1.0.0
sqlite3 (built-in)
```

## Architecture Flow
```
User → PyQt6 GUI → Queue → LangGraph Workflow → OpenAI API
           ↑                        ↓
           ←── SQLite (temp state) ←┘
```

## Environment Setup
```bash
# Required environment variable
export OPENAI_API_KEY="your-api-key-here"
```

## LangGraph Workflow (To Be Detailed)
1. Document intake and preprocessing
2. Classification with justification
3. Exemption detection
4. Human review integration
5. Learning from feedback
6. Batch application of patterns

## Future Considerations (Post-MVP)
- Local LLM support (Ollama)
- PDF processing capability
- Persistent learning data
- Configuration management
- Multi-user support
- Advanced exemption detection
- Recursive directory processing
- Robust error recovery