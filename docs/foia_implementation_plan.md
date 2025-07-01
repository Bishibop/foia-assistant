# FOIA Response Assistant - Phased Implementation Plan

## Overview
This plan breaks down the FOIA Response Assistant into independently testable phases. Each phase builds on the previous one and can be manually tested before proceeding.

---

## Phase 0: Environment Setup and Sample Data ✅ COMPLETE

### Goal
Set up development environment and create sample documents for testing.

### User Stories
- As a developer, I want a properly configured Python environment
- As a developer, I want sample FOIA documents to test with

### Deliverables
1. **Python environment** with all dependencies
2. **Sample documents** including:
   - 5-10 clearly responsive documents (mentioning "Project Blue Sky")
   - 5-10 clearly non-responsive documents
   - 5-10 ambiguous documents (edge cases)
   - Documents with PII (fake phone numbers, SSNs)
3. **Project structure** initialized

### Setup Steps
```bash
# 1. Create project directory
mkdir foia-assistant && cd foia-assistant

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install pyqt6 langgraph langchain langchain-openai python-dotenv

# 4. Set environment variable
export OPENAI_API_KEY="your-key-here"
```

### Sample Document Creation
Create `sample_docs/` with files like:
- `email_project_blue_sky_update.txt` (responsive)
- `email_lunch_plans.txt` (non-responsive)
- `memo_sky_initiative.txt` (ambiguous - unclear if same project)
- `employee_directory.txt` (contains phone numbers, SSNs)

### Test Scenario
- Verify Python 3.11+ installed
- Confirm all packages install correctly
- Check sample documents are readable

---

## Phase 1: Basic Document Processing with LangGraph ✅ COMPLETE

### Goal
Create a working LangGraph workflow that can classify documents without any GUI.

### User Stories
- As a developer, I want to run a script that processes a folder of documents and prints classifications to console
- As a developer, I want to see the AI's reasoning for each classification

### Deliverables
1. **LangGraph workflow** with these nodes:
   - Document loader node
   - Classification node (calls OpenAI)
   - Exemption detection node
   - Output formatter node
2. **Basic data model** (`Document` class)
3. **Command-line script** to test the workflow

### System Design
```python
# Core components needed:
- models/document.py - Document dataclass
- langgraph/state.py - DocumentState definition
- langgraph/nodes.py - Individual processing nodes
- langgraph/workflow.py - Main graph construction
- test_langgraph.py - CLI script to test
```

### LangGraph Workflow Details

**State Schema:**
```python
class DocumentState(TypedDict):
    filename: str
    content: str
    foia_request: str
    classification: Optional[str]  # "responsive", "non_responsive", "uncertain"
    confidence: Optional[float]
    justification: Optional[str]
    exemptions: Optional[List[Dict]]
```

**Node Specifications:**

1. **Load Document Node**
   - Reads file content from disk
   - Populates state with content

2. **Classification Node**
   - Prompt: "Given FOIA request: '{request}', classify this document as responsive, non_responsive, or uncertain. Explain your reasoning."
   - Parses response for classification and justification
   - Calculates confidence score

3. **Exemption Detection Node**
   - Only runs if document is responsive
   - Uses regex for basic PII (SSN: XXX-XX-XXXX, Phone: XXX-XXX-XXXX)
   - Future: OpenAI call for complex exemptions

4. **Output Formatter Node**
   - Formats results for console display

### Test Scenario
```bash
python test_langgraph.py --folder ./sample_docs --request "All emails about Project Blue Sky"
# Should output classifications for each document to console
```

---

## Phase 1.5: Code Quality Setup

### Goal
Set up linting and formatting tools to ensure consistent code quality before GUI development.

### User Stories
- As a developer, I want automatic code formatting to maintain consistency
- As a developer, I want linting to catch common errors and style issues
- As a developer, I want clear code style guidelines

### Deliverables
1. **pyproject.toml** with tool configurations
2. **Black** formatter setup
3. **Ruff** linter setup
4. **Development dependencies** file
5. Optional: **Pre-commit hooks**

### Configuration
```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py310']

[tool.ruff]
line-length = 88
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line length handled by Black
```

### Setup Steps
```bash
# Install development tools
pip install black ruff

# Format all code
black src/ test_langgraph.py

# Run linter
ruff check src/ test_langgraph.py
```

### Test Scenario
- Run Black on all Python files
- Run Ruff to check for issues
- Verify no major style violations
- Ensure consistent formatting

---

## Phase 2: Basic PyQt6 Application Shell

### Goal
Create the tabbed GUI structure without connecting to LangGraph.

### User Stories
- As a user, I want to see a desktop application with tabs for different functions
- As a user, I want to select a folder and enter a FOIA request

### Deliverables
1. **Main window** with tab structure
2. **Processing tab** with folder selection and request input
3. **Review tab** placeholder
4. **Processed tab** placeholder
5. **Basic styling** with Fusion theme

### System Design
```python
# Components needed:
- main.py - Application entry point
- gui/main_window.py - Main window with tabs
- gui/processing_tab.py - Folder selection, request input
- gui/review_tab.py - Empty placeholder
- gui/processed_tab.py - Empty placeholder
```

### Project Structure Note
PyQt6 doesn't have a default project initializer. We'll use this structure:
```
foia-assistant/
├── src/
│   ├── main.py
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   └── tabs/
│   ├── langgraph/
│   └── models/
├── sample_docs/
└── requirements.txt
```

### Test Scenario
- Run the application
- Click through all tabs
- Select a folder using the file dialog
- Enter a FOIA request
- Verify UI is responsive and looks professional

---

## Phase 3: Connect LangGraph to Processing Tab

### Goal
Integrate Phase 1 and Phase 2 - make the Processing tab actually process documents.

### User Stories
- As a user, I want to click "Start Processing" and see real-time progress
- As a user, I want to see statistics about document classification

### Deliverables
1. **Background thread** for LangGraph processing
2. **Qt signals** for thread communication
3. **Processing status panel** showing:
   - Progress bar
   - Current document
   - Classification statistics
   - Activity log

### System Design
```python
# New/modified components:
- processing/worker.py - QThread for LangGraph
- gui/processing_tab.py - Add status panel, progress tracking
- Updated signal/slot connections in main_window.py
```

### Test Scenario
- Select folder with sample documents
- Enter FOIA request
- Click "Start Processing"
- Verify progress updates in real-time
- Verify statistics are accurate
- Ensure GUI remains responsive

---

## Phase 4: Document Review Interface

### Goal
Implement the human review interface for classified documents.

### User Stories
- As a FOIA officer, I want to review AI classifications one at a time
- As a FOIA officer, I want to see the AI's justification for each classification
- As a FOIA officer, I want to approve or override the AI's decision

### Deliverables
1. **Review tab** with:
   - Document viewer
   - AI classification and justification display
   - Approve/Override buttons
   - Exemption highlighting
2. **Review queue** management
3. **Keyboard shortcuts** for quick review

### System Design
```python
# Components needed:
- gui/review_tab.py - Full implementation
- gui/widgets/document_viewer.py - Text display widget
- gui/widgets/decision_panel.py - Classification controls
- Queue integration between processing and review
```

### Test Scenario
- Process documents (Phase 3)
- Switch to Review tab
- Review several documents
- Test approve/override functionality
- Verify keyboard shortcuts work
- Ensure queue updates properly

---

## Phase 5: Learning Integration

### Goal
Implement the feedback loop where human decisions improve AI classification.

### User Stories
- As a FOIA officer, I want the system to learn from my corrections
- As a FOIA officer, I want to see when the AI applies learned patterns

### Deliverables
1. **Learning node** in LangGraph workflow
2. **Feedback mechanism** from review decisions
3. **Pattern detection** and application
4. **Activity log** showing learning events

### System Design
```python
# New components:
- langgraph/nodes/learning_node.py - Processes feedback
- langgraph/memory.py - Stores patterns (in-memory for MVP)
- Updated workflow to include learning loop
```

### Test Scenario
- Review and override several similar documents
- Process new documents
- Verify AI applies learned patterns
- Check activity log for learning events

---

## Phase 6: Processed Documents View

### Goal
Create the Processed tab to show all reviewed documents.

### User Stories
- As a user, I want to see all documents I've reviewed
- As a user, I want to filter/search processed documents
- As a user, I want to see final classifications and exemptions

### Deliverables
1. **Processed tab** with:
   - Table/list of reviewed documents
   - Classification badges
   - Exemption indicators
   - Basic search/filter
2. **Document selection** to view details

### System Design
```python
# Components needed:
- gui/processed_tab.py - Full implementation
- gui/widgets/document_table.py - Table widget
- Integration with review decisions
```

### Test Scenario
- Review multiple documents
- Switch to Processed tab
- Verify all reviewed docs appear
- Test search/filter functionality
- Click documents to see details

---

## Phase 7: PII Detection and Exemption Marking

### Goal
Add automatic detection and manual marking of exemptions.

### User Stories
- As a FOIA officer, I want the AI to highlight potential PII
- As a FOIA officer, I want to add/remove exemption markings
- As a FOIA officer, I want to see exemptions in the processed view

### Deliverables
1. **PII detection node** in LangGraph
2. **Exemption highlighting** in document viewer
3. **Add/remove exemption** functionality
4. **Exemption display** in processed tab

### System Design
```python
# New/modified components:
- langgraph/nodes/exemption_node.py - PII detection
- gui/widgets/document_viewer.py - Add highlighting
- gui/widgets/exemption_marker.py - Manual marking tool
- Updated Document model for exemptions
```

### Test Scenario
- Process documents with PII (phone numbers, SSNs)
- Verify AI highlights them
- Manually add/remove exemptions
- Check exemptions appear in Processed tab

---

## Phase 8: Export and Polish

### Goal
Add export functionality and final UI polish.

### User Stories
- As a user, I want to export results for reporting
- As a user, I want summary statistics of my review session

### Deliverables
1. **Export tab** with:
   - Summary statistics
   - Export to JSON button
   - Session overview
2. **Polish**:
   - Error messages
   - Loading states
   - Final styling touches

### System Design
```python
# Components needed:
- gui/export_tab.py - Export interface
- export/json_exporter.py - Export logic
- Final UI polish across all components
```

### Test Scenario
- Complete full workflow
- Go to Export tab
- Verify statistics are accurate
- Export results
- Check JSON file is complete and correct

---

## Testing Checkpoints

After each phase, verify:
1. **Phase runs independently** - Can test new functionality
2. **No regressions** - Previous phases still work
3. **Manual testing passes** - All user stories fulfilled
4. **Ready for next phase** - Clean foundation to build on

## Success Criteria
- Each phase produces visible, testable results
- Application grows incrementally
- Core value (AI classification) proven early (Phase 1)
- GUI added progressively without breaking core logic