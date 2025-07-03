# Epic Brief: FOIA Response Assistant - Epic 2

## Executive Summary
Building on the MVP's core document classification capabilities, Epic 2 enhances the FOIA Response Assistant with intelligent learning, multi-request management, parallel processing, and automated redaction. This epic focuses on four critical capabilities that demonstrate the system's value, scalability, performance, and security.

## Features Overview

### 1. Learning & Feedback System with Reprocessing
Enable the system to learn from human decisions within a session, demonstrating immediate accuracy improvements through in-memory feedback.

### 2. Multi-Request Management  
Provide centralized management of multiple FOIA requests, allowing agencies to handle their full workload efficiently.

### 3. Parallel Document Processing
Accelerate document processing by utilizing multiple CPU cores, reducing processing time by up to 75%.

### 4. Automated Redaction Application
Complete the exemption workflow by actually removing sensitive information from exported documents, ensuring PII is properly redacted in FOIA response packages.

## Problem Statement
The MVP demonstrates AI-assisted FOIA processing but lacks:
- **Memory**: No learning from corrections, even within the same batch
- **Scale**: Can only handle one request at a time
- **Speed**: Sequential processing underutilizes modern multi-core CPUs
- **Feedback Loop**: No way to improve results based on user expertise
- **Security Gap**: Detected exemptions are only flagged, not actually redacted from exports

## Feature 1: Learning & Feedback System (Demo Version)

### Goals
- Demonstrate how user feedback improves AI accuracy
- Show immediate benefits within a single session
- Enable reprocessing with accumulated feedback
- Keep implementation simple for proof-of-concept

### Core Capabilities
- **In-Memory Feedback Storage**: Capture overrides during current session
- **Few-Shot Learning**: Include recent overrides as examples in prompts
- **Reprocessing**: Re-classify documents using accumulated feedback
- **Transparent Learning**: Show which examples influenced decisions

### How It Works
1. **Initial Processing**: AI classifies documents normally
2. **User Reviews**: Human overrides incorrect classifications with reasoning
3. **Feedback Accumulation**: System stores overrides in memory
4. **Reprocessing**: User can re-run remaining documents with feedback
5. **Improved Results**: Similar documents benefit from prior corrections

### Technical Approach
- Simple in-memory list of override examples
- Include last 3-5 relevant overrides in prompts
- No database or persistence (demo only)
- Clear feedback attribution in UI

### Demo Scenario
- Process folder of 50 documents
- User reviews first 10, corrects 3-4 mistakes
- Click "Reprocess with Feedback" button
- Remaining 40 documents show improved accuracy
- Clear demonstration of learning value

### Success Metrics
- Visible accuracy improvement after reprocessing
- <1 second additional processing time
- User can see which feedback influenced decisions

## Feature 2: Multi-Request Management

### Goals
- Handle multiple concurrent FOIA requests
- Provide visibility into request workload
- Enable easy switching between requests
- Track per-request progress and feedback

### Core Capabilities
- **Requests Tab**: New leftmost tab showing all FOIA requests
- **Request Creation**: Add new FOIA requests with basic info
- **Active Request Selection**: Choose which request to work on
- **Progress Tracking**: Real-time status per request
- **Feedback History**: View all overrides/corrections per request

### User Workflow
1. User opens app to Requests tab
2. Creates or selects a FOIA request
3. Clicks "Open Request" to make it active
4. All other tabs now operate within that request's context
5. Feedback stays isolated to each request
6. Can switch between requests anytime

### Technical Approach
- In-memory request list and active request state
- Each request maintains its own document lists
- UI state management for active request switching
- Simple request metadata (name, deadline, status)

### Success Metrics
- Support 10+ concurrent requests without performance degradation
- <5 seconds to switch between request contexts
- Zero data leakage between requests

## Feature 3: Parallel Document Processing

### Goals
- Dramatically reduce document processing time
- Better utilize modern multi-core processors
- Maintain UI responsiveness during processing
- Scale processing with available hardware

### Core Capabilities
- **Multi-Process Architecture**: Use 4 parallel worker processes
- **Smart Work Distribution**: Balance document load across workers
- **Real-Time Progress**: Aggregate progress from all workers
- **Graceful Degradation**: Handle worker failures without losing data
- **Performance Monitoring**: Show processing speed and worker status

### How It Works
1. **Document Queue**: Split documents into batches for workers
2. **Worker Pool**: Spawn 4 processes with separate LangGraph instances
3. **Parallel Processing**: Each worker processes documents independently
4. **Result Aggregation**: Collect and merge results in main thread
5. **Progress Updates**: Show combined progress in real-time

### Technical Approach
```python
from concurrent.futures import ProcessPoolExecutor, as_completed

def process_batch(documents: list[Document]) -> list[Document]:
    # Each worker gets its own LangGraph instance
    workflow = create_workflow()
    results = []
    for doc in documents:
        result = workflow.run(doc)
        results.append(result)
    return results

# Main processing logic
with ProcessPoolExecutor(max_workers=4) as executor:
    # Submit batches to workers
    futures = []
    for batch in document_batches:
        future = executor.submit(process_batch, batch)
        futures.append(future)
    
    # Collect results as they complete
    for future in as_completed(futures):
        results = future.result()
        update_progress()
```

### UI Enhancements
- Progress bar shows combined progress
- Status shows "Processing (4 workers active)"
- Display documents/minute processing rate
- Color-coded worker status indicators

### Demo Impact
- **Before**: 100 documents × 3 seconds = 5 minutes
- **After**: 100 documents ÷ 4 workers × 3 seconds = 1.25 minutes
- **Result**: 75% reduction in processing time

### Success Metrics
- Process 4x faster with 4 workers (linear scaling)
- No UI freezing during processing
- <10% overhead from parallelization
- Graceful handling of API rate limits

## Feature 4: Automated Redaction Application

### Goals
- Apply detected exemptions as actual redactions in exported documents
- Ensure PII is removed from FOIA response packages, not just flagged
- Complete the exemption workflow by actually removing sensitive data

### Core Capabilities
- **Redaction Engine**: Replace exempted text with "[REDACTED]" markers
- **Position-Based Processing**: Apply redactions based on stored exemption positions
- **Document Export**: Generate FOIA packages with redacted content

### How It Works
1. **Exemption Detection**: Current system identifies PII (SSN, phone, email)
2. **Redaction Processing**: Apply redactions based on exemption positions
3. **Text Replacement**: Replace sensitive text with "[REDACTED - b6]"
4. **Export Generation**: Save redacted versions in FOIA response package

### Technical Approach
```python
def get_redacted_content(self) -> str:
    """Apply redactions to document content."""
    if not self.exemptions:
        return self.content
    
    # Sort exemptions by start position (reverse order)
    sorted_exemptions = sorted(self.exemptions, 
                              key=lambda x: x['start'], 
                              reverse=True)
    
    redacted = self.content
    for exemption in sorted_exemptions:
        redaction_text = f"[REDACTED - {exemption['exemption_code']}]"
        redacted = (redacted[:exemption['start']] + 
                   redaction_text + 
                   redacted[exemption['end']:])
    
    return redacted
```

### User Workflow
1. Documents processed and exemptions detected automatically
2. User reviews exemptions in Review tab
3. User generates FOIA package in Finalize tab
4. Documents are exported with redactions applied
5. Exemption log still generated for reference

### Success Metrics
- 100% of detected PII removed from exported documents
- Redacted documents remain readable
- No performance impact on export process

## Integration Architecture

### Data Model Evolution
```python
# For Epic 2 Demo: In-memory only
class RequestManager:
    def __init__(self):
        self.requests = []  # List of Request objects
        self.active_request = None
        
class FeedbackManager:
    def __init__(self):
        self.overrides = []  # List of override examples
        
# Future consideration: SQLite tables
- requests (id, name, description, created_at, deadline, status)
- feedback (id, request_id, document_id, ai_decision, human_decision, reasoning)
```

### UI Structure
```
┌─────────────────────────────────────┐
│        Requests Tab (New)            │
│  - Request list with progress        │
│  - Create/select requests            │
│  - View feedback history             │
├─────────────────────────────────────┤
│ Requests | Intake | Review | Finalize│
│ (Other tabs scoped to active request)│
└─────────────────────────────────────┘
```

## Implementation Priorities

### Phase 1: Multi-Request Management (Days 1-3)
- Requests tab UI
- In-memory request management
- Active request switching
- Basic request CRUD operations

### Phase 2: Parallel Processing (Days 4-5)
- ProcessPoolExecutor integration
- Worker management and monitoring
- Progress aggregation from multiple workers
- Error handling and recovery

### Phase 3: Learning System (Days 6-7)
- In-memory feedback storage
- Few-shot prompt enhancement
- Reprocessing capability with feedback
- UI for showing learning attribution

### Phase 4: Automated Redaction (Days 8-9)
- Document model redaction method
- FOIA package generation updates
- Testing with various exemption patterns
- Verification of complete PII removal

## Risk Mitigation
- **Data Isolation**: Strict request-based data separation
- **Performance**: Efficient in-memory data structures and parallel processing
- **API Rate Limits**: Intelligent request throttling across workers
- **Worker Failures**: Graceful recovery and retry mechanisms
- **User Training**: Clear documentation on all new features

## Success Criteria
- Process 5+ concurrent requests efficiently
- Achieve 75% reduction in processing time with parallel workers
- Achieve 25% reduction in review time through learning
- Track all feedback and corrections per request
- Demonstrate clear improvement with reprocessing
- Support switching between requests seamlessly
- Remove 100% of detected PII from exported documents
- Maintain document readability after redactions

## Future Vision
Epic 2 lays the groundwork for:
- Persistent storage and session recovery
- Multi-user collaboration
- Advanced analytics and reporting
- Local LLM support for offline operation
- API integration with existing systems

This epic transforms the MVP into a more capable and secure system that can handle multiple requests efficiently, learn from user expertise to improve accuracy, process documents 4x faster through parallelization, and ensure proper redaction of sensitive information.