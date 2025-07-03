# Technical Design Document: FOIA Response Assistant - Epic 3

## Overview

This technical design document details the implementation approach for Epic 3 of the FOIA Response Assistant. Epic 3 introduces two key features to enhance the system's efficiency and compliance capabilities:

1. **Duplicate Detection System**: Identifies and marks duplicate documents using OpenAI embeddings
2. **Basic Audit Trail System**: Provides compliance logging and audit export functionality

## Architecture Overview

### System Integration Points

Epic 3 features integrate into the existing architecture at several key points:

```
┌─────────────────────────────────────────────────────────────┐
│                      PyQt6 GUI Layer                        │
│  ┌──────────────┬────────────┬────────────┬──────────────┬─────────┐
│  │ Requests Tab │ Intake Tab │ Review Tab │ Finalize Tab │Audit Tab│
│  │              │            │            │  (Enhanced)  │  (New)  │
│  └──────┬───────┴────────────┴────────────┴──────────────┴─────────┘
│         │                                                    
│  ┌──────▼────────────────────────────────────────────────┐  
│  │            Status Panel (Enhanced with Embedding Progress)│  
│  └──────┬────────────────────────────────────────────────┘  
└─────────┼───────────────────────────────────────────────────┘
          │ Qt Signals
┌─────────▼───────────────────────────────────────────────────┐
│               Request Management Layer                       │
│  ┌──────────────┬────────────────┬──────────────────────┬────────────┐
│  │Request Manager│ Document Store  │ Feedback Manager    │Audit Manager│
│  │(CRUD Ops)    │ (Request Docs)  │ (User Corrections)  │   (New)    │
│  └──────────────┴────────────────┴──────────────────────┴────────────┘
└─────────┬───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│         Processing Worker (QThread) - Enhanced               │
│         + Embedding Generation Phase                         │
│         + Duplicate Detection Logic                          │
└─────────┬───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│            Parallel Document Processor - Enhanced            │
│  ┌─────────────┬─────────────┬─────────────────────────┬────────────┐
│  │ Worker Pool │ Task Queue  │ Progress Aggregation    │Embedding   │
│  │ (4 workers) │ Distribution│ & Rate Calculation      │Store (New) │
│  └─────────────┴─────────────┴─────────────────────────┴────────────┘
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
                    │  + Embeddings   │
                    └─────────────────┘
```

## Feature 1: Duplicate Detection System

### Design Goals

- Detect exact and near-duplicate documents efficiently
- Maintain request isolation (no cross-request contamination)
- Provide clear UI feedback during embedding generation
- Enable selective export of non-duplicate documents
- Minimal performance impact on existing workflow

### Core Components

#### 1. EmbeddingStore Class

```python
from typing import Dict, List, Tuple, Optional
import numpy as np
import hashlib

class EmbeddingStore:
    """In-memory storage for document embeddings with duplicate detection."""
    
    def __init__(self):
        # Store embeddings by request_id -> filename -> embedding
        self._embeddings: Dict[str, Dict[str, List[float]]] = {}
        self._hashes: Dict[str, Dict[str, str]] = {}
        self._processed_order: Dict[str, List[str]] = {}
    
    def add_embedding(self, request_id: str, filename: str, 
                     embedding: List[float], content_hash: str) -> None:
        """Store an embedding for a document."""
        if request_id not in self._embeddings:
            self._embeddings[request_id] = {}
            self._hashes[request_id] = {}
            self._processed_order[request_id] = []
        
        self._embeddings[request_id][filename] = embedding
        self._hashes[request_id][filename] = content_hash
        self._processed_order[request_id].append(filename)
    
    def find_exact_duplicate(self, request_id: str, content_hash: str) -> Optional[str]:
        """Find exact duplicate by content hash."""
        for filename, stored_hash in self._hashes.get(request_id, {}).items():
            if stored_hash == content_hash:
                return filename
        return None
    
    def find_similar(self, request_id: str, embedding: List[float], 
                    threshold: float = 0.85) -> List[Tuple[str, float]]:
        """Find similar documents using cosine similarity."""
        similar = []
        for filename, stored_embedding in self._embeddings.get(request_id, {}).items():
            similarity = self._cosine_similarity(embedding, stored_embedding)
            if similarity >= threshold:
                similar.append((filename, similarity))
        return sorted(similar, key=lambda x: x[1], reverse=True)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1_array = np.array(vec1)
        vec2_array = np.array(vec2)
        
        dot_product = np.dot(vec1_array, vec2_array)
        norm1 = np.linalg.norm(vec1_array)
        norm2 = np.linalg.norm(vec2_array)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def clear_request(self, request_id: str) -> None:
        """Clear all embeddings for a specific request."""
        self._embeddings.pop(request_id, None)
        self._hashes.pop(request_id, None)
        self._processed_order.pop(request_id, None)
```

#### 2. Enhanced Document Model

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Document:
    # Existing fields
    filename: str
    content: str
    classification: Optional[str] = None
    confidence: Optional[float] = None
    justification: Optional[str] = None
    exemptions: List[Dict[str, Any]] = field(default_factory=list)
    human_decision: Optional[str] = None
    human_feedback: Optional[str] = None
    
    # New duplicate detection fields
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    similarity_score: Optional[float] = None
    content_hash: Optional[str] = None
    embedding_generated: bool = False
```

#### 3. Embedding Generation Service

```python
import os
from openai import OpenAI
from typing import List, Optional

class EmbeddingService:
    """Service for generating document embeddings using OpenAI."""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "text-embedding-3-small"
        self.max_chars = 8000  # ~2000 tokens
    
    def generate_embedding(self, content: str) -> Optional[List[float]]:
        """Generate embedding for document content."""
        # Truncate content to avoid token limits
        truncated_content = content[:self.max_chars]
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=truncated_content
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding generation error: {str(e)}")
            return None
    
    def generate_content_hash(self, content: str) -> str:
        """Generate SHA-256 hash of content for exact duplicate detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
```

### Processing Workflow Integration

#### Enhanced ProcessingWorker

```python
from PyQt6.QtCore import pyqtSignal

class ProcessingWorker(QThread):
    # New signals for embedding progress
    embedding_progress = pyqtSignal(int, int)  # current, total
    duplicates_found = pyqtSignal(int)  # count
    
    def __init__(self, documents: List[Path], request_id: str, 
                 embedding_store: EmbeddingStore, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.documents = documents
        self.request_id = request_id
        self.embedding_store = embedding_store
        self.embedding_service = EmbeddingService()
    
    def run(self):
        """Enhanced run method with embedding generation phase."""
        try:
            # Phase 1: Generate embeddings and detect duplicates
            self._generate_embeddings_phase()
            
            # Phase 2: Process documents (including duplicates)
            self._process_documents_phase()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.processing_complete.emit()
    
    def _generate_embeddings_phase(self):
        """Generate embeddings for all documents and mark duplicates."""
        duplicate_count = 0
        
        for idx, doc_path in enumerate(self.documents):
            # Update progress
            self.status_updated.emit(f"Generating embeddings... ({idx+1}/{len(self.documents)})")
            self.embedding_progress.emit(idx + 1, len(self.documents))
            
            # Load content
            content = doc_path.read_text(encoding='utf-8')
            content_hash = self.embedding_service.generate_content_hash(content)
            
            # Check for exact duplicate first
            exact_match = self.embedding_store.find_exact_duplicate(
                self.request_id, content_hash
            )
            
            if exact_match:
                # Mark as exact duplicate
                doc = Document(
                    filename=doc_path.name,
                    content=content,
                    content_hash=content_hash,
                    is_duplicate=True,
                    duplicate_of=exact_match,
                    similarity_score=1.0
                )
                duplicate_count += 1
            else:
                # Generate embedding for similarity check
                embedding = self.embedding_service.generate_embedding(content)
                
                if embedding:
                    # Check for near-duplicates
                    similar_docs = self.embedding_store.find_similar(
                        self.request_id, embedding, threshold=0.85
                    )
                    
                    if similar_docs:
                        # Mark as near-duplicate
                        doc = Document(
                            filename=doc_path.name,
                            content=content,
                            content_hash=content_hash,
                            is_duplicate=True,
                            duplicate_of=similar_docs[0][0],
                            similarity_score=similar_docs[0][1],
                            embedding_generated=True
                        )
                        duplicate_count += 1
                    else:
                        # Original document
                        doc = Document(
                            filename=doc_path.name,
                            content=content,
                            content_hash=content_hash,
                            is_duplicate=False,
                            embedding_generated=True
                        )
                    
                    # Store embedding
                    self.embedding_store.add_embedding(
                        self.request_id, doc_path.name, embedding, content_hash
                    )
            
            # Store document metadata for processing phase
            self._document_metadata[doc_path] = doc
        
        # Emit duplicate count
        self.duplicates_found.emit(duplicate_count)
        self.status_updated.emit(f"Embeddings complete. Duplicates found: {duplicate_count}")
```

### UI Enhancements

#### Status Panel Updates

```python
class StatusPanel(QWidget):
    def __init__(self):
        super().__init__()
        # Existing initialization...
        
        # New UI elements for embedding progress
        self.embedding_progress_bar = QProgressBar()
        self.embedding_label = QLabel("Embeddings Generated: 0")
        self.duplicates_label = QLabel("Duplicates Found: 0")
        
        # Add to layout
        self.stats_layout.addWidget(self.embedding_label)
        self.stats_layout.addWidget(self.duplicates_label)
        self.progress_layout.addWidget(self.embedding_progress_bar)
    
    def update_embedding_progress(self, current: int, total: int):
        """Update embedding generation progress."""
        self.embedding_progress_bar.setMaximum(total)
        self.embedding_progress_bar.setValue(current)
        self.embedding_label.setText(f"Embeddings Generated: {current}")
    
    def update_duplicate_count(self, count: int):
        """Update duplicate count display."""
        self.duplicates_label.setText(f"Duplicates Found: {count}")
```

#### Enhanced Finalize Tab

```python
class FinalizeTab(QWidget):
    def __init__(self, document_store: DocumentStore, audit_manager: AuditManager):
        super().__init__()
        self.document_store = document_store
        self.audit_manager = audit_manager
        self._setup_ui()
    
    def _setup_ui(self):
        # Enhanced table headers
        self.table.setHorizontalHeaderLabels([
            "Select", "Filename", "Classification", "Duplicate Status", "Decision"
        ])
        
        # New button for duplicate selection
        self.select_non_duplicates_btn = QPushButton("Select All Non-Duplicates")
        self.select_non_duplicates_btn.clicked.connect(self._select_non_duplicates)
        self.button_layout.addWidget(self.select_non_duplicates_btn)
    
    def _populate_table(self):
        """Populate table with duplicate status information."""
        documents = self.document_store.get_reviewed_documents(self.request_id)
        
        for row, doc in enumerate(documents):
            # Checkbox - unchecked by default for duplicates
            checkbox = QCheckBox()
            checkbox.setChecked(not doc.is_duplicate)
            self.table.setCellWidget(row, 0, checkbox)
            
            # Duplicate status column
            if doc.is_duplicate:
                status_text = f"Duplicate of: {doc.duplicate_of}"
                if doc.similarity_score and doc.similarity_score < 1.0:
                    status_text += f" ({doc.similarity_score:.0%} similar)"
                status_item = QTableWidgetItem(status_text)
                status_item.setForeground(QColor("#666666"))  # Gray text
            else:
                status_item = QTableWidgetItem("Original")
            
            self.table.setItem(row, 3, status_item)
    
    def _select_non_duplicates(self):
        """Select all non-duplicate documents."""
        for row in range(self.table.rowCount()):
            doc = self.documents[row]
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(not doc.is_duplicate)
```

## Feature 2: Basic Audit Trail System

### Design Goals

- Track all key document interactions for compliance
- Support filtered and full audit exports
- Minimal performance overhead
- Simple, clear audit entries
- Request-agnostic viewing (see all activity)

### Core Components

#### 1. Audit Manager

```python
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import csv
from typing import List, Optional, Dict, Any

@dataclass
class AuditEntry:
    """Represents a single audit log entry."""
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str
    document_filename: Optional[str] = None
    event_type: str  # "classify", "review", "view", "export", "error"
    details: str
    ai_result: Optional[str] = None
    user_decision: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV export."""
        return {
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'request_id': self.request_id,
            'document': self.document_filename or '',
            'event': self.event_type,
            'details': self.details,
            'ai_result': self.ai_result or '',
            'user_decision': self.user_decision or ''
        }

class AuditManager:
    """Manages audit trail logging and export."""
    
    def __init__(self):
        self._entries: List[AuditEntry] = []
    
    def log_classification(self, filename: str, result: str, 
                         confidence: float, request_id: str) -> None:
        """Log an AI classification event."""
        entry = AuditEntry(
            request_id=request_id,
            document_filename=filename,
            event_type="classify",
            ai_result=result,
            details=f"AI Classification - Confidence: {confidence:.2f}"
        )
        self._entries.append(entry)
    
    def log_review(self, filename: str, ai_result: str, 
                  user_decision: str, request_id: str) -> None:
        """Log a user review decision."""
        override = ai_result != user_decision
        details = f"User Review - {'Override' if override else 'Approved'}"
        
        entry = AuditEntry(
            request_id=request_id,
            document_filename=filename,
            event_type="review",
            ai_result=ai_result,
            user_decision=user_decision,
            details=details
        )
        self._entries.append(entry)
    
    def log_view(self, filename: str, tab_name: str, request_id: str) -> None:
        """Log a document view event."""
        entry = AuditEntry(
            request_id=request_id,
            document_filename=filename,
            event_type="view",
            details=f"Document viewed in {tab_name}"
        )
        self._entries.append(entry)
    
    def log_export(self, format: str, document_count: int, 
                  request_id: str, selected_files: Optional[List[str]] = None) -> None:
        """Log an export event."""
        details = f"Export {format} - {document_count} documents"
        if selected_files:
            details += f" (Selected: {', '.join(selected_files[:3])}"
            if len(selected_files) > 3:
                details += f" and {len(selected_files) - 3} more"
            details += ")"
        
        entry = AuditEntry(
            request_id=request_id,
            event_type="export",
            details=details
        )
        self._entries.append(entry)
    
    def log_error(self, filename: Optional[str], error_message: str, 
                 request_id: str) -> None:
        """Log an error event."""
        entry = AuditEntry(
            request_id=request_id,
            document_filename=filename,
            event_type="error",
            details=f"Error: {error_message}"
        )
        self._entries.append(entry)
    
    def get_entries(self, request_id: Optional[str] = None,
                   document_filter: Optional[List[str]] = None) -> List[AuditEntry]:
        """Get audit entries with optional filtering."""
        entries = self._entries
        
        if request_id:
            entries = [e for e in entries if e.request_id == request_id]
        
        if document_filter:
            entries = [e for e in entries 
                      if e.document_filename in document_filter]
        
        return entries
    
    def export_csv(self, filepath: Path, 
                  selected_documents: Optional[List[str]] = None) -> None:
        """Export audit log to CSV file."""
        entries = self._entries
        
        if selected_documents:
            entries = [e for e in entries 
                      if not e.document_filename or 
                      e.document_filename in selected_documents]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['timestamp', 'request_id', 'document', 
                         'event', 'details', 'ai_result', 'user_decision']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for entry in entries:
                writer.writerow(entry.to_dict())
    
    def get_all_documents(self) -> List[Tuple[str, str]]:
        """Get all unique document-request pairs for filtering."""
        doc_request_pairs = set()
        for entry in self._entries:
            if entry.document_filename:
                doc_request_pairs.add((entry.document_filename, entry.request_id))
        return sorted(list(doc_request_pairs))
```

#### 2. Audit Tab Implementation

```python
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QSplitter, QListWidget, 
                             QTextEdit, QCheckBox, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal

class AuditTab(QWidget):
    """Tab for viewing and exporting audit trails."""
    
    export_requested = pyqtSignal(list)  # List of selected documents
    
    def __init__(self, audit_manager: AuditManager):
        super().__init__()
        self.audit_manager = audit_manager
        self.selected_documents = []
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the audit tab UI."""
        layout = QVBoxLayout(self)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        # Dynamic export button
        self.export_button = QPushButton("Export Audit")
        self.export_button.clicked.connect(self._export_audit)
        controls_layout.addStretch()
        controls_layout.addWidget(self.export_button)
        
        layout.addLayout(controls_layout)
        
        # Main content - splitter with document list and audit trail
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Document list
        self.document_list = QListWidget()
        self.document_list.itemChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._create_document_panel())
        
        # Right panel - Audit trail
        self.audit_display = QTextEdit()
        self.audit_display.setReadOnly(True)
        splitter.addWidget(self._create_audit_panel())
        
        # Set splitter proportions (30/70)
        splitter.setSizes([300, 700])
        
        layout.addWidget(splitter)
    
    def _create_document_panel(self) -> QWidget:
        """Create the document selection panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Header
        header = QLabel("Documents")
        header.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(header)
        
        # Document list with checkboxes
        layout.addWidget(self.document_list)
        
        return panel
    
    def _create_audit_panel(self) -> QWidget:
        """Create the audit trail display panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Header
        header = QLabel("Audit Trail")
        header.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(header)
        
        # Audit display
        layout.addWidget(self.audit_display)
        
        return panel
    
    def refresh(self):
        """Refresh the audit display."""
        # Populate document list
        self._populate_document_list()
        
        # Display all audit entries
        self._display_audit_entries()
    
    def _populate_document_list(self):
        """Populate the document list with checkboxes."""
        self.document_list.clear()
        
        # Get all unique document-request pairs
        doc_pairs = self.audit_manager.get_all_documents()
        
        for filename, request_id in doc_pairs:
            # Create checkbox item
            item = QListWidgetItem(f"{filename} (Request: {request_id})")
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, filename)
            self.document_list.addItem(item)
    
    def _display_audit_entries(self, document_filter: Optional[List[str]] = None):
        """Display audit entries in the text area."""
        entries = self.audit_manager.get_entries(document_filter=document_filter)
        
        # Clear display
        self.audit_display.clear()
        
        # Format and display entries
        for entry in entries:
            # Format: Time | Request | Document | Event | Details
            line = f"{entry.timestamp.strftime('%H:%M:%S')} | "
            line += f"{entry.request_id} | "
            line += f"{entry.document_filename or 'N/A'} | "
            line += f"{entry.event_type.upper()} | "
            line += entry.details
            
            if entry.ai_result:
                line += f" | AI: {entry.ai_result}"
            if entry.user_decision:
                line += f" | User: {entry.user_decision}"
            
            self.audit_display.append(line)
    
    def _on_selection_changed(self, item: QListWidgetItem):
        """Handle document selection changes."""
        # Update selected documents list
        self.selected_documents = []
        
        for i in range(self.document_list.count()):
            list_item = self.document_list.item(i)
            if list_item.checkState() == Qt.CheckState.Checked:
                filename = list_item.data(Qt.ItemDataRole.UserRole)
                self.selected_documents.append(filename)
        
        # Update export button text
        if self.selected_documents:
            self.export_button.setText(f"Export Audit ({len(self.selected_documents)})")
        else:
            self.export_button.setText("Export Audit")
        
        # Update audit display to show only selected documents
        if self.selected_documents:
            self._display_audit_entries(document_filter=self.selected_documents)
        else:
            self._display_audit_entries()
    
    def _export_audit(self):
        """Handle export button click."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Audit Log",
            "audit_log.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            self.audit_manager.export_csv(
                Path(file_path),
                selected_documents=self.selected_documents if self.selected_documents else None
            )
            QMessageBox.information(self, "Export Complete", 
                                  f"Audit log exported to {file_path}")
```

### Integration Points

#### 1. Classifier Node Integration

```python
# In langgraph/nodes/classifier.py
def classify_document(state: DocumentState) -> DocumentState:
    """Enhanced classify node with audit logging."""
    try:
        # Existing classification logic...
        result = llm.invoke(messages)
        
        # Log to audit trail
        audit_manager = state.get('audit_manager')
        if audit_manager:
            audit_manager.log_classification(
                filename=state['filename'],
                result=result['classification'],
                confidence=result['confidence'],
                request_id=state['request_id']
            )
        
        # Update state
        state['classification'] = result['classification']
        state['confidence'] = result['confidence']
        state['justification'] = result['justification']
        
    except Exception as e:
        # Log error to audit
        if audit_manager:
            audit_manager.log_error(
                filename=state['filename'],
                error_message=str(e),
                request_id=state['request_id']
            )
        
        # Fallback to uncertain
        state['classification'] = 'uncertain'
        state['confidence'] = 0.0
        state['error'] = str(e)
    
    return state
```

#### 2. Review Tab Integration

```python
# In gui/tabs/review_tab.py
def _save_decision(self):
    """Enhanced save decision with audit logging."""
    if not self.current_document:
        return
    
    # Get decision
    decision = self._get_selected_decision()
    
    # Log to audit trail
    self.audit_manager.log_review(
        filename=self.current_document.filename,
        ai_result=self.current_document.classification,
        user_decision=decision,
        request_id=self.request_id
    )
    
    # Save decision (existing logic)
    self.current_document.human_decision = decision
    
    # Emit signal
    self.review_completed.emit(self.current_document)
```

#### 3. Document View Logging

```python
# In gui/widgets/document_viewer.py
def display_document(self, document: Document, tab_name: str):
    """Enhanced display with audit logging."""
    # Log view event
    if hasattr(self, 'audit_manager') and self.audit_manager:
        self.audit_manager.log_view(
            filename=document.filename,
            tab_name=tab_name,
            request_id=self.request_id
        )
    
    # Display document (existing logic)
    self._display_content(document)
```

## Testing Strategy

### Unit Tests

1. **EmbeddingStore Tests**
   - Test exact duplicate detection
   - Test similarity calculation
   - Test request isolation
   - Test threshold behavior

2. **AuditManager Tests**
   - Test event logging
   - Test filtering
   - Test CSV export
   - Test entry formatting

### Integration Tests

1. **Duplicate Detection Flow**
   - Test embedding generation
   - Test duplicate marking
   - Test UI updates
   - Test export behavior

2. **Audit Trail Flow**
   - Test classification logging
   - Test review logging
   - Test export functionality
   - Test UI refresh

### Performance Tests

1. **Embedding Performance**
   - Measure time for 100 documents
   - Test memory usage
   - Test API rate limiting

2. **Audit Performance**
   - Test with 1000+ entries
   - Measure UI responsiveness
   - Test export speed

## Security Considerations

1. **API Key Protection**
   - Continue using environment variables
   - No API keys in logs

2. **Data Isolation**
   - Request-scoped embeddings
   - No cross-request access
   - Clear on request switch

3. **Audit Integrity**
   - Immutable audit entries
   - Timestamp validation
   - No entry deletion

## Performance Optimizations

1. **Embedding Generation**
   - Batch API calls where possible
   - Cache embeddings in memory
   - Truncate content appropriately

2. **Duplicate Detection**
   - Use content hash for exact matches first
   - Efficient numpy operations
   - Lazy similarity calculation

3. **Audit Trail**
   - Paginate large audit displays
   - Efficient CSV writing
   - Minimal logging overhead

## Future Enhancements

### Duplicate Detection
- Persistent embedding storage
- Cross-request duplicate detection
- Configurable similarity thresholds
- Template extraction
- Clustering visualization

### Audit Trail
- Advanced filtering options
- Audit trail search
- PDF report generation
- Compliance report templates
- User authentication tracking

## Conclusion

This technical design provides a comprehensive implementation plan for Epic 3 features. The duplicate detection system uses OpenAI embeddings to identify redundant documents efficiently, while the audit trail system ensures complete compliance tracking. Both features integrate cleanly with the existing architecture and maintain the system's focus on local processing and user control.