# Epic Brief: FOIA Response Assistant - Epic 3 (MVP)

## Executive Summary
Building on Epic 2's multi-request management and learning capabilities, Epic 3 MVP introduces two streamlined features: intelligent document deduplication using OpenAI embeddings and basic compliance audit trails. These features focus on demonstrating efficiency gains and transparency with minimal implementation complexity.

## Features Overview

### 1. Duplicate Detection System (MVP)
Implement in-memory duplicate detection using OpenAI embeddings to identify exact and near-duplicate documents, marking them in the Finalize tab for exclusion from export while still processing all documents.

### 2. Basic Audit Trail System (MVP)
Provide simple audit logging that tracks key document interactions (classification decisions and user reviews) with CSV export capability for compliance demonstration.

## Problem Statements

### Duplication Challenges
Government document collections often contain significant duplication:
- **Exact Duplicates**: Same document appears multiple times (different filenames, locations)
- **Near Duplicates**: Minor variations (headers, footers, timestamps) on essentially identical content
- **Template Variations**: Standard forms with minor field differences
- **Version Chains**: Multiple revisions of the same document

Current system processes every document independently, leading to:
- **Wasted API Calls**: Classifying the same content multiple times
- **Increased Costs**: Unnecessary OpenAI API usage
- **Slower Processing**: Time spent on redundant documents
- **Inconsistent Results**: Same document might get different classifications
- **Review Fatigue**: Humans reviewing essentially identical content

### Compliance and Audit Requirements
FOIA processing demands complete transparency and accountability:
- **Legal Requirements**: Need to demonstrate proper review process
- **Decision Tracking**: Must document who reviewed what and when
- **Processing History**: Show all AI interactions and classifications
- **Change Tracking**: Record all modifications and overrides
- **Audit Reports**: Generate compliance documentation for oversight

Current system lacks audit capabilities:
- **No Activity Logging**: User actions aren't tracked
- **No Processing History**: AI decisions aren't recorded with timestamps
- **No Review Trail**: Can't prove which documents were reviewed
- **No Compliance Reports**: No way to generate audit documentation
- **No Session Reconstruction**: Can't replay what happened during processing

## Duplicate Detection System (MVP)

### Goals
- Detect both exact and near-duplicate documents
- Mark duplicates in Finalize tab for export exclusion
- Show clear UI feedback during embedding generation
- Maintain simple in-memory storage
- Demonstrate efficiency gains without complexity

### Core Capabilities

#### 1. **Embedding Generation**
- Use OpenAI's text-embedding-3-small API
- Generate embeddings during initial processing phase
- Show progress in status panel: "Generating embeddings... (25/50)"
- Truncate documents to 8000 characters for embedding

#### 2. **Similarity Detection**
- Fixed thresholds: 1.0 for exact match, 0.85 for near-duplicates
- Simple cosine similarity calculation
- In-memory storage using Python dict
- Content hash for exact match detection

#### 3. **Processing Behavior**
- **Process all documents** (including duplicates)
- Mark duplicates with metadata during processing
- Track "original" document for each duplicate
- No skip or inheritance - full processing for demo

#### 4. **UI Integration**
- **Intake Tab**: Show embedding generation progress
- **Finalize Tab**: 
  - Add "Duplicate Status" column
  - Show "Duplicate of: [filename]" in details
  - Uncheck duplicates by default
  - "Select All Non-Duplicates" button

### How It Works

#### Processing Flow
1. **Load all documents** into memory
2. **Embedding Generation Phase** (new):
   - Generate embeddings for all documents
   - Show progress: "Generating embeddings... (X/Y)"
   - Check for duplicates using cosine similarity
   - Mark duplicate relationships
3. **Classification Phase**:
   - Process ALL documents (including duplicates)
   - Normal classification workflow
4. **Finalize Tab**:
   - Display duplicate status
   - Allow selective export

#### Status Panel UI During Processing
```
┌─────────────────────────────────────────┐
│ Status: Generating embeddings...        │
│ Current: contract_v2.txt                │
│                                         │
│ Progress:                               │
│ [████████░░░░░░░] 50% (25/50)          │
│                                         │
│ Embeddings Generated: 25                │
│ Duplicates Found: 3                     │
│                                         │
│ Next: Document Classification           │
└─────────────────────────────────────────┘
```

#### Finalize Tab Display
```
[ ] contract_v1.txt      Responsive       Original
[ ] contract_v2.txt      Responsive       Duplicate of: contract_v1.txt
[✓] invoice.txt          Non-responsive   Original  
[ ] contract_final.txt   Responsive       Duplicate of: contract_v1.txt

[Select All Non-Duplicates] [Export Selected]
```

### Technical Architecture (MVP)

#### Simple In-Memory Storage
```python
class EmbeddingStore:
    def __init__(self):
        # Store embeddings by request_id -> filename -> embedding
        self._embeddings: dict[str, dict[str, list[float]]] = {}
        self._hashes: dict[str, dict[str, str]] = {}
    
    def add_embedding(self, request_id: str, filename: str, 
                     embedding: list[float], content_hash: str):
        if request_id not in self._embeddings:
            self._embeddings[request_id] = {}
            self._hashes[request_id] = {}
        
        self._embeddings[request_id][filename] = embedding
        self._hashes[request_id][filename] = content_hash
    
    def find_similar(self, request_id: str, embedding: list[float], 
                    threshold: float = 0.85) -> list[tuple[str, float]]:
        similar = []
        for filename, stored_embedding in self._embeddings.get(request_id, {}).items():
            similarity = cosine_similarity(embedding, stored_embedding)
            if similarity >= threshold:
                similar.append((filename, similarity))
        return sorted(similar, key=lambda x: x[1], reverse=True)

# Enhanced Document Model
@dataclass
class Document:
    # Existing fields...
    is_duplicate: bool = False
    duplicate_of: str | None = None  # Original document filename
    similarity_score: float | None = None
    content_hash: str | None = None
```

#### Processing Integration
```python
# In ProcessingWorker
def process_documents(self, documents: list[Path], request_id: str):
    # Phase 1: Generate embeddings
    embedding_store = EmbeddingStore()
    
    for idx, doc_path in enumerate(documents):
        self.status_updated.emit("Generating embeddings...")
        self.progress_updated.emit(idx, len(documents))
        
        content = doc_path.read_text()
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Generate embedding
        embedding = self.generate_embedding(content)
        
        # Check for duplicates
        similar = embedding_store.find_similar(request_id, embedding)
        
        # Store document with duplicate info
        doc = Document(
            filename=doc_path.name,
            content=content,
            content_hash=content_hash
        )
        
        if similar and similar[0][1] >= 0.85:
            doc.is_duplicate = True
            doc.duplicate_of = similar[0][0]
            doc.similarity_score = similar[0][1]
        
        embedding_store.add_embedding(request_id, doc_path.name, embedding, content_hash)
        
    # Phase 2: Normal classification (process all documents)
    self.status_updated.emit("Classifying documents...")
    # ... existing classification logic
```

### Implementation Details (MVP)

#### 1. **OpenAI Embedding Generation**
```python
from openai import OpenAI

client = OpenAI()

def generate_embedding(self, content: str) -> list[float]:
    # Truncate to ~8k chars (about 2k tokens)
    truncated = content[:8000]
    
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=truncated
        )
        return response.data[0].embedding
    except Exception as e:
        self.error_occurred.emit(f"Embedding error: {str(e)}")
        return []
```

#### 2. **Cosine Similarity Calculation**
```python
import numpy as np

def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)
```

#### 3. **Finalize Tab Updates**
```python
# Add to document table
self.table.setHorizontalHeaderLabels([
    "Select", "Filename", "Classification", "Duplicate Status", "Decision"
])

# Populate duplicate status
if document.is_duplicate:
    status_item = QTableWidgetItem(f"Duplicate of: {document.duplicate_of}")
    status_item.setForeground(QColor("#666666"))  # Gray text
else:
    status_item = QTableWidgetItem("Original")

# Default checkbox state
checkbox = QCheckBox()
checkbox.setChecked(not document.is_duplicate)  # Uncheck duplicates

# Select All Non-Duplicates button
def select_non_duplicates(self):
    for row in range(self.table.rowCount()):
        doc = self.documents[row]
        checkbox = self.table.cellWidget(row, 0)
        checkbox.setChecked(not doc.is_duplicate)
```

### User Interface Changes (MVP)

#### 1. **Intake Tab - Status Panel Update**
No new controls - just updated status messages during processing:
- "Generating embeddings... (25/50)"
- "Embeddings complete. Duplicates found: 3"

#### 2. **Finalize Tab - Main Changes**
- Add "Duplicate Status" column to table
- Uncheck duplicates by default
- Add "Select All Non-Duplicates" button
- Show duplicate relationship in details

#### 3. **No Changes To**
- Review Tab (no duplicate indicators)
- No configuration options
- No threshold controls

### Performance Characteristics (MVP)

#### Processing Time
- **Embedding Generation**: +1-2s per document (acceptable)
- **Similarity Check**: <100ms per document
- **Overall Impact**: Slightly slower but identifies duplicates

#### API Costs
- **Embedding Cost**: ~$0.02 per 1000 documents
- **No savings in MVP** (still process all documents)
- **Future savings** when skip processing implemented

#### Storage Requirements
- **In-memory only**: ~6KB per document for embeddings
- **No persistence**: Cleared when switching requests
- **Simple dict storage**: Minimal overhead

### Success Metrics
- Detect 95%+ of exact duplicates
- Identify 80%+ of near-duplicates (templates, versions)
- Reduce processing time by 30-50% on typical document sets
- Save $50-100 in API costs per 1000 documents
- Zero false positives on duplicate detection
- Maintain sub-second similarity search performance

### Risk Mitigation

#### Privacy & Security
- All processing remains local
- Embeddings don't leave the system
- Request isolation maintained
- No embedding persistence by default

#### Performance
- Lazy embedding generation
- Batch processing for efficiency
- Configurable similarity thresholds
- Graceful degradation if vector DB fails

#### Accuracy
- Conservative default thresholds
- Human review for near-duplicates
- Clear duplicate indicators
- Ability to ungroup documents

### Demo Scenarios

#### Scenario 1: Email Thread Deduplication
- Upload folder with 50 emails (many quoted/forwarded)
- System detects 30 near-duplicates
- Groups related emails together
- Reduces review time from 50 to 20 documents

#### Scenario 2: Contract Versions
- Process folder with contract_v1.txt through contract_v15.txt
- System identifies version chain
- Allows reviewing only latest version
- Shows version relationships

#### Scenario 3: Form Submissions
- 200 similar forms with different field values
- System detects template pattern
- Groups forms for batch review
- Applies consistent classification

### Future Enhancements
- Cross-request duplicate detection (with permissions)
- Persistent embedding storage
- Custom similarity metrics
- Template learning and extraction
- Fuzzy matching for scanned documents
- Multi-language duplicate detection

## Basic Audit Trail System (MVP)

### Goals
- Track key document interactions for compliance
- Simple CSV export for audit documentation
- Minimal performance impact
- Focus on classification and review decisions

### Core Capabilities

#### 1. **Key Event Logging Only**
Track only essential events:
- **LLM Processing**: Classification result for each document
- **Document Views**: When user opens a document in any tab
- **Exports**: When documents are exported (format, count)
- **Errors**: Classification failures (if any)

#### 2. **Simple Audit Entry**
```python
@dataclass
class AuditEntry:
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str
    document_filename: str | None
    event_type: str  # "classify", "review", "error"
    details: str  # Simple text description
    ai_result: str | None  # For classification events
    user_decision: str | None  # For review events
```

#### 3. **Audit Tab Interface (MVP)**

Two-panel layout similar to Finalize tab:

**Left Panel - Document List**:
- Checkbox list of all documents across ALL requests
- Shows document name and request ID
- Allows multi-selection for filtered export

**Right Panel - Audit Trail**:
- Read-only chronological event log
- Shows events from ALL requests (not filtered)
- Newest events at bottom
- Format: `Time | Request | Document | Event | Details`

**Export Control**:
- Single dynamic button in top-right
- "Export Audit" when no selection
- "Export Audit (n)" when documents selected

### Technical Implementation (MVP)

#### 1. **Simple Audit Manager**
```python
class AuditManager:
    def __init__(self):
        self._entries: list[AuditEntry] = []
    
    def log_classification(self, filename: str, result: str, 
                         confidence: float, request_id: str):
        entry = AuditEntry(
            request_id=request_id,
            document_filename=filename,
            event_type="classify",
            ai_result=result,
            details=f"Confidence: {confidence:.2f}"
        )
        self._entries.append(entry)
    
    def log_review(self, filename: str, ai_result: str, 
                  user_decision: str, request_id: str):
        details = "Override" if ai_result != user_decision else ""
        entry = AuditEntry(
            request_id=request_id,
            document_filename=filename,
            event_type="review",
            ai_result=ai_result,
            user_decision=user_decision,
            details=details
        )
        self._entries.append(entry)
    
    def export_csv(self, filepath: Path, selected_docs: list[str] = None):
        """Export audit log to CSV, optionally filtered by documents"""
        entries = self._entries
        if selected_docs:
            entries = [e for e in entries if e.document_filename in selected_docs]
            
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'request_id', 'document', 'event', 'details'
            ])
            writer.writeheader()
            for entry in entries:
                writer.writerow({
                    'timestamp': entry.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'request_id': entry.request_id,
                    'document': entry.document_filename or '',
                    'event': entry.event_type,
                    'details': entry.details
                })
```

#### 2. **Integration Points**

**In Classifier Node**:
```python
# After classification
audit_manager.log_classification(
    filename=state['filename'],
    result=result['classification'],
    confidence=result['confidence'],
    request_id=request_id
)
```

**In Document Views**:
```python
# When document is opened in any tab
self.audit_manager.log_event(
    request_id=self.request_id,
    document_filename=document.filename,
    event_type="view",
    details=f"View: {tab_name} tab"
)
```

**In Export Functions**:
```python
# When documents are exported
self.audit_manager.log_event(
    request_id=self.request_id,
    event_type="export",
    details=f"Export: {format} ({len(documents)} docs)"
)
```

### Audit Tab Layout (MVP)
```
┌─────────────────────────────────────────────────────────┐
│ Requests | Intake | Review | Finalize | Audit          │
├─────────────────────────────────────────────────────────┤
│                                         [Export Audit]  │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐ ┌────────────────────────────┐ │
│ │ Documents           │ │ Audit Trail                │ │
│ │ ┌─────────────────┐ │ │ ┌──────────────────────┐  │ │
│ │ │□ contract.txt   │ │ │ │10:23 REQ-001         │  │ │
│ │ │  REQ-001        │ │ │ │contract.txt          │  │ │
│ │ │□ invoice.txt    │ │ │ │LLM: Responsive       │  │ │
│ │ │  REQ-001        │ │ │ │                      │  │ │
│ │ │□ memo.txt       │ │ │ │10:24 REQ-001         │  │ │
│ │ │  REQ-002        │ │ │ │contract.txt          │  │ │
│ │ └─────────────────┘ │ │ │View: Review tab      │  │ │
│ │                     │ │ │                      │  │ │
│ │                     │ │ │10:25 REQ-002         │  │ │
│ │                     │ │ │memo.txt              │  │ │
│ │                     │ │ │Export: CSV (3 docs)  │  │ │
│ └─────────────────────┘ │ └──────────────────────┘  │ │
└─────────────────────────────────────────────────────────┘
```

### Success Metrics (MVP)
- Track 100% of classifications and reviews
- CSV export working
- Minimal performance impact (<10ms per log)
- Clear override visibility

## Implementation Timeline (MVP - 1 Week)

### Days 1-3: Duplicate Detection
- Day 1: Add OpenAI embedding generation to processing workflow
- Day 1: Implement in-memory EmbeddingStore class
- Day 2: Add duplicate detection logic with cosine similarity
- Day 2: Update Document model with duplicate fields
- Day 3: Modify Finalize tab to show duplicate status and selection

### Days 4-5: Basic Audit Trail
- Day 4: Create AuditManager class with simple logging
- Day 4: Integrate audit logging into classifier and review tab
- Day 5: Create basic Audit tab with table display
- Day 5: Implement CSV export functionality

### Days 6-7: Testing & Polish
- Day 6: Test duplicate detection with various document sets
- Day 6: Verify audit logging captures all events
- Day 7: Integration testing and bug fixes
- Day 7: Documentation updates

## Conclusion
This MVP implementation of Epic 3 provides a demonstration-ready system with duplicate detection and basic audit trails. The simplified approach focuses on proving the value of these features without the complexity of a full production implementation. Both features can be expanded in future iterations based on user feedback and requirements.