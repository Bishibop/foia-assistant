# Epic 2 Technical Design Document
## RAPID RESPONSE AI - Advanced Features Implementation

### Version 1.0
### Date: January 2025

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Feature 1: Multi-Request Management](#feature-1-multi-request-management)
3. [Feature 2: Parallel Document Processing](#feature-2-parallel-document-processing)
4. [Feature 3: Learning & Feedback System](#feature-3-learning--feedback-system)
5. [Feature 4: Automated Redaction Application](#feature-4-automated-redaction-application)
6. [Integration Architecture](#integration-architecture)
7. [Migration Strategy](#migration-strategy)
8. [Testing Strategy](#testing-strategy)
9. [Performance Considerations](#performance-considerations)
10. [Security Considerations](#security-considerations)

---

## Executive Summary

Epic 2 introduces four major enhancements to the RAPID RESPONSE AI system:

1. **Multi-Request Management** - Support for handling multiple concurrent FOIA requests with isolated processing contexts
2. **Parallel Document Processing** - 4x performance improvement through parallel worker processes
3. **Learning & Feedback System** - In-session learning from user corrections to improve classification accuracy
4. **Automated Redaction Application** - Apply detected PII redactions to exported documents

These features maintain the existing security model (all processing local, no data persistence) while significantly improving throughput and accuracy.

---

## Feature 1: Multi-Request Management

### Overview
Enable users to manage multiple FOIA requests within a single application session, with each request maintaining its own document set, processing state, and review decisions.

### Data Model

```python
# src/models/request.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

@dataclass
class FOIARequest:
    """Represents a single FOIA request being processed"""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    foia_request_text: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    status: str = "draft"  # draft, processing, review, complete
    
    # Statistics
    total_documents: int = 0
    processed_documents: int = 0
    responsive_count: int = 0
    non_responsive_count: int = 0
    uncertain_count: int = 0
    
    # Document associations (in-memory only)
    document_folder: Optional[Path] = None
    processed_document_ids: set[str] = field(default_factory=set)
    reviewed_document_ids: set[str] = field(default_factory=set)
```

### Request Manager

```python
# src/processing/request_manager.py
from typing import Dict, List, Optional
from models.request import FOIARequest

class RequestManager:
    """Manages multiple FOIA requests in memory"""
    
    def __init__(self):
        self._requests: Dict[str, FOIARequest] = {}
        self._active_request_id: Optional[str] = None
        
    def create_request(self, name: str, description: str = "") -> FOIARequest:
        """Create a new FOIA request"""
        request = FOIARequest(name=name, description=description)
        self._requests[request.id] = request
        if not self._active_request_id:
            self._active_request_id = request.id
        return request
        
    def get_request(self, request_id: str) -> Optional[FOIARequest]:
        """Retrieve a specific request"""
        return self._requests.get(request_id)
        
    def get_active_request(self) -> Optional[FOIARequest]:
        """Get the currently active request"""
        if self._active_request_id:
            return self._requests.get(self._active_request_id)
        return None
        
    def set_active_request(self, request_id: str) -> bool:
        """Set the active request"""
        if request_id in self._requests:
            self._active_request_id = request_id
            return True
        return False
        
    def list_requests(self) -> List[FOIARequest]:
        """List all requests sorted by creation date"""
        return sorted(self._requests.values(), 
                     key=lambda r: r.created_at, 
                     reverse=True)
        
    def delete_request(self, request_id: str) -> bool:
        """Delete a request and its associated data"""
        if request_id in self._requests:
            del self._requests[request_id]
            if self._active_request_id == request_id:
                # Set next available request as active
                if self._requests:
                    self._active_request_id = next(iter(self._requests))
                else:
                    self._active_request_id = None
            return True
        return False
```

### UI Design - Requests Tab

```python
# src/gui/tabs/requests_tab.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QTableWidget, QSplitter)
from PyQt6.QtCore import pyqtSignal, Qt

class RequestsTab(QWidget):
    """Tab for managing multiple FOIA requests"""
    
    # Signals
    request_created = pyqtSignal(str)  # request_id
    request_selected = pyqtSignal(str)  # request_id
    request_deleted = pyqtSignal(str)  # request_id
    
    def __init__(self, request_manager: RequestManager):
        super().__init__()
        self.request_manager = request_manager
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.new_button = QPushButton("New Request")
        self.edit_button = QPushButton("Edit")
        self.delete_button = QPushButton("Delete")
        self.set_active_button = QPushButton("Set Active")
        
        button_layout.addWidget(self.new_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.set_active_button)
        button_layout.addStretch()
        
        # Request table
        self.request_table = QTableWidget()
        self.request_table.setColumnCount(6)
        self.request_table.setHorizontalHeaderLabels([
            "Active", "Name", "Status", "Documents", 
            "Created", "Deadline"
        ])
        
        # Details panel
        self.details_panel = RequestDetailsPanel()
        
        # Splitter layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.request_table)
        splitter.addWidget(self.details_panel)
        splitter.setSizes([400, 600])
        
        layout.addLayout(button_layout)
        layout.addWidget(splitter)
```

### Integration Points

1. **MainWindow Integration**
   - Add RequestsTab as the first tab
   - Pass RequestManager instance to all tabs
   - Update tab switching to respect active request context

2. **IntakeTab Integration**
   - Scope document processing to active request
   - Update statistics in active request
   - Store document associations with request

3. **ReviewTab Integration**
   - Filter review queue by active request
   - Update request progress on review completion

4. **FinalizeTab Integration**
   - Export documents for active request only
   - Generate request-specific packages

---

## Feature 2: Parallel Document Processing

### Overview
Implement parallel document processing using Python's multiprocessing to achieve 4x performance improvement. Documents are distributed among worker processes that each maintain their own LangGraph instance.

### Architecture

```python
# src/processing/parallel_worker.py
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any, Callable
from dataclasses import dataclass
from queue import Queue
import os

@dataclass
class WorkerResult:
    """Result from a worker process"""
    document_id: str
    success: bool
    document: Optional[Document] = None
    error: Optional[str] = None
    processing_time: float = 0.0

class ParallelDocumentProcessor:
    """Manages parallel document processing using multiple workers"""
    
    def __init__(self, num_workers: int = 4):
        self.num_workers = min(num_workers, mp.cpu_count())
        self.progress_queue = mp.Queue()
        
    def process_documents(
        self, 
        documents: List[Path],
        foia_request: str,
        progress_callback: Callable[[int, int], None],
        feedback_examples: List[Dict[str, Any]] = None
    ) -> List[Document]:
        """Process documents in parallel"""
        
        # Split documents into batches
        batches = self._create_batches(documents)
        
        # Create shared progress tracking
        progress_counter = mp.Value('i', 0)
        total_docs = len(documents)
        
        results = []
        
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit batch jobs
            future_to_batch = {
                executor.submit(
                    process_document_batch,
                    batch,
                    foia_request,
                    feedback_examples,
                    progress_counter,
                    total_docs,
                    worker_id
                ): batch
                for worker_id, batch in enumerate(batches)
            }
            
            # Monitor progress
            progress_monitor = executor.submit(
                self._monitor_progress,
                progress_counter,
                total_docs,
                progress_callback
            )
            
            # Collect results
            for future in as_completed(future_to_batch):
                batch_results = future.result()
                results.extend(batch_results)
                
        return results
        
    def _create_batches(self, documents: List[Path]) -> List[List[Path]]:
        """Distribute documents evenly among workers"""
        batch_size = len(documents) // self.num_workers
        batches = []
        
        for i in range(self.num_workers):
            start = i * batch_size
            if i == self.num_workers - 1:
                # Last worker gets remaining documents
                batch = documents[start:]
            else:
                batch = documents[start:start + batch_size]
            if batch:  # Only add non-empty batches
                batches.append(batch)
                
        return batches
        
    def _monitor_progress(
        self,
        counter: mp.Value,
        total: int,
        callback: Callable[[int, int], None]
    ):
        """Monitor and report progress from all workers"""
        last_value = 0
        while True:
            with counter.get_lock():
                current = counter.value
            if current != last_value:
                callback(current, total)
                last_value = current
            if current >= total:
                break
            time.sleep(0.1)

# Worker process function
def process_document_batch(
    documents: List[Path],
    foia_request: str,
    feedback_examples: List[Dict[str, Any]],
    progress_counter: mp.Value,
    total_docs: int,
    worker_id: int
) -> List[Document]:
    """Process a batch of documents in a worker process"""
    
    # Initialize LangGraph workflow for this worker
    # Each worker gets its own instance to avoid conflicts
    from langgraph.workflow import get_workflow
    workflow = get_workflow()
    
    # Set OpenAI API key from environment
    os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
    
    results = []
    
    for doc_path in documents:
        try:
            # Process document through workflow
            state = {
                "filename": str(doc_path),
                "foia_request": foia_request,
                "feedback_examples": feedback_examples or []
            }
            
            result = workflow.invoke(state)
            
            # Convert to Document object
            document = Document(
                filename=result["filename"],
                content=result.get("content", ""),
                classification=result.get("classification"),
                confidence=result.get("confidence"),
                justification=result.get("justification"),
                exemptions=result.get("exemptions", [])
            )
            
            results.append(document)
            
        except Exception as e:
            # Create error document
            document = Document(
                filename=str(doc_path),
                content="",
                classification="uncertain",
                confidence=0.0,
                justification=f"Processing error: {str(e)}",
                exemptions=[]
            )
            results.append(document)
            
        finally:
            # Update progress
            with progress_counter.get_lock():
                progress_counter.value += 1
                
    return results
```

### Modified Processing Worker

```python
# src/processing/worker.py (modifications)
class ProcessingWorker(QThread):
    """Background worker for document processing"""
    
    def __init__(self, documents: list[Path], foia_request: str,
                 request_id: str, feedback_manager: FeedbackManager = None):
        super().__init__()
        self.documents = documents
        self.foia_request = foia_request
        self.request_id = request_id
        self.feedback_manager = feedback_manager
        self._stop_requested = False
        
        # Initialize parallel processor
        self.parallel_processor = ParallelDocumentProcessor(num_workers=4)
        
    def run(self):
        """Process documents using parallel workers"""
        try:
            # Get feedback examples if available
            feedback_examples = []
            if self.feedback_manager:
                feedback_examples = self.feedback_manager.get_relevant_feedback(
                    self.request_id, limit=5
                )
            
            # Process documents in parallel
            start_time = time.time()
            
            processed_documents = self.parallel_processor.process_documents(
                self.documents,
                self.foia_request,
                self._progress_callback,
                feedback_examples
            )
            
            # Calculate processing rate
            elapsed_time = time.time() - start_time
            docs_per_minute = (len(self.documents) / elapsed_time) * 60
            
            # Emit results
            self.processing_rate.emit(docs_per_minute)
            self.documents_processed.emit(processed_documents)
            
        except Exception as e:
            self.error_occurred.emit(f"Processing error: {str(e)}")
        finally:
            self.processing_complete.emit()
            
    def _progress_callback(self, current: int, total: int):
        """Called by parallel processor to report progress"""
        self.progress_updated.emit(current, total)
```

### UI Updates for Parallel Processing

```python
# src/gui/widgets/status_panel.py (modifications)
class StatusPanel(QWidget):
    def update_processing_status(self, workers_active: int, docs_per_minute: float):
        """Update status to show parallel processing metrics"""
        status_text = f"Processing ({workers_active} workers active)"
        self.status_label.setText(status_text)
        
        rate_text = f"{docs_per_minute:.1f} docs/minute"
        self.rate_label.setText(rate_text)
        
        # Add worker status indicators
        self.worker_indicators.update_active_workers(workers_active)
```

---

## Feature 3: Learning & Feedback System

### Overview
Implement in-session learning where the system improves classification accuracy by learning from user corrections. Uses few-shot learning to include recent corrections in classification prompts.

### Feedback Data Model

```python
# src/processing/feedback_manager.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

@dataclass
class FeedbackEntry:
    """Represents a single piece of user feedback"""
    document_id: str
    request_id: str
    original_classification: str
    human_decision: str
    original_confidence: float
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Document characteristics for similarity matching
    document_length: int = 0
    has_attachments: bool = False
    key_phrases: List[str] = field(default_factory=list)

class FeedbackManager:
    """Manages user feedback for improving classifications"""
    
    def __init__(self):
        # Store feedback by request_id
        self._feedback: Dict[str, List[FeedbackEntry]] = defaultdict(list)
        
        # Cache for similarity calculations
        self._similarity_cache: Dict[tuple, float] = {}
        
    def add_feedback(
        self,
        document: Document,
        request_id: str,
        human_decision: str,
        reasoning: str = ""
    ) -> FeedbackEntry:
        """Record user feedback on a classification"""
        
        # Only record if human overrode AI
        if document.classification == human_decision:
            return None
            
        entry = FeedbackEntry(
            document_id=document.filename,
            request_id=request_id,
            original_classification=document.classification,
            human_decision=human_decision,
            original_confidence=document.confidence or 0.0,
            reasoning=reasoning,
            document_length=len(document.content),
            key_phrases=self._extract_key_phrases(document.content)
        )
        
        self._feedback[request_id].append(entry)
        return entry
        
    def get_relevant_feedback(
        self,
        request_id: str,
        current_document: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get most relevant feedback examples for few-shot learning"""
        
        feedback_list = self._feedback.get(request_id, [])
        if not feedback_list:
            return []
            
        # Sort by recency and relevance
        sorted_feedback = sorted(
            feedback_list,
            key=lambda f: (f.timestamp, self._calculate_relevance(f, current_document)),
            reverse=True
        )
        
        # Convert to format for prompt
        examples = []
        for feedback in sorted_feedback[:limit]:
            examples.append({
                "document_snippet": f"Document: {feedback.document_id} (length: {feedback.document_length})",
                "ai_classification": feedback.original_classification,
                "human_correction": feedback.human_decision,
                "reasoning": feedback.reasoning or "No reason provided",
                "confidence": feedback.original_confidence
            })
            
        return examples
        
    def _extract_key_phrases(self, content: str) -> List[str]:
        """Extract key phrases for similarity matching"""
        # Simple implementation - could be enhanced with NLP
        words = content.lower().split()
        # Look for important keywords
        keywords = ["request", "responsive", "exempt", "confidential", 
                   "personal", "privileged", "outside scope"]
        return [w for w in words if w in keywords]
        
    def _calculate_relevance(
        self,
        feedback: FeedbackEntry,
        current_doc: Optional[str]
    ) -> float:
        """Calculate relevance score for feedback example"""
        if not current_doc:
            return 0.0
            
        # Simple relevance based on recency and type of correction
        recency_score = 1.0 / (1 + (datetime.now() - feedback.timestamp).seconds / 3600)
        
        # Boost score for high-confidence corrections
        confidence_factor = feedback.original_confidence
        
        return recency_score * confidence_factor
        
    def get_statistics(self, request_id: str) -> Dict[str, Any]:
        """Get feedback statistics for a request"""
        feedback_list = self._feedback.get(request_id, [])
        
        if not feedback_list:
            return {
                "total_corrections": 0,
                "accuracy_improvement": 0.0
            }
            
        total = len(feedback_list)
        
        # Calculate accuracy improvement over time
        # Compare early vs recent corrections
        if total >= 10:
            early = feedback_list[:5]
            recent = feedback_list[-5:]
            early_correction_rate = len([f for f in early if f.original_confidence < 0.7]) / 5
            recent_correction_rate = len([f for f in recent if f.original_confidence < 0.7]) / 5
            improvement = max(0, early_correction_rate - recent_correction_rate)
        else:
            improvement = 0.0
            
        return {
            "total_corrections": total,
            "accuracy_improvement": improvement * 100,
            "most_corrected_type": self._get_most_corrected_type(feedback_list)
        }
        
    def _get_most_corrected_type(self, feedback_list: List[FeedbackEntry]) -> str:
        """Identify the most common type of correction"""
        corrections = defaultdict(int)
        for f in feedback_list:
            key = f"{f.original_classification} -> {f.human_decision}"
            corrections[key] += 1
            
        if corrections:
            return max(corrections.items(), key=lambda x: x[1])[0]
        return "N/A"
```

### Enhanced Classifier with Feedback

```python
# src/langgraph/nodes/classifier.py (modifications)
def classify_document(state: DocumentState) -> DocumentState:
    """Classify document with feedback-enhanced prompts"""
    
    try:
        # Get feedback examples if available
        feedback_examples = state.get("feedback_examples", [])
        
        # Build enhanced prompt with examples
        if feedback_examples:
            example_text = "\n\nHere are recent classification corrections to learn from:\n"
            for i, example in enumerate(feedback_examples, 1):
                example_text += f"""
Example {i}:
- Document: {example['document_snippet']}
- AI classified as: {example['ai_classification']} (confidence: {example['confidence']:.1%})
- Human corrected to: {example['human_correction']}
- Reason: {example['reasoning']}
"""
            
            enhanced_prompt = base_prompt + example_text + """

Based on these examples, please be more careful about:
1. Documents that might seem {original} but are actually {corrected}
2. The specific reasoning patterns shown in the corrections
3. Adjusting confidence when similar patterns are detected
"""
        else:
            enhanced_prompt = base_prompt
            
        # Use enhanced prompt for classification
        response = llm.invoke(enhanced_prompt.format(
            content=state["content"][:2000],
            foia_request=state["foia_request"]
        ))
        
        # Parse response and update state
        classification_data = response.model_dump()
        
        # Add feedback attribution if examples were used
        if feedback_examples:
            classification_data["used_feedback"] = True
            classification_data["feedback_count"] = len(feedback_examples)
            
        state.update(classification_data)
        
    except Exception as e:
        logger.error(f"Classification error: {e}")
        state["classification"] = "uncertain"
        state["confidence"] = 0.0
        state["error"] = str(e)
        
    return state
```

### Reprocessing UI

```python
# src/gui/tabs/intake_tab.py (modifications)
class IntakeTab(QWidget):
    def __init__(self, request_manager: RequestManager, 
                 feedback_manager: FeedbackManager):
        super().__init__()
        self.request_manager = request_manager
        self.feedback_manager = feedback_manager
        self._setup_ui()
        
    def _setup_ui(self):
        # Add reprocess button
        self.reprocess_button = QPushButton("Reprocess with Feedback")
        self.reprocess_button.setToolTip(
            "Reprocess documents using learned patterns from corrections"
        )
        self.reprocess_button.clicked.connect(self._reprocess_with_feedback)
        
        # Add feedback statistics display
        self.feedback_stats = QLabel("No feedback yet")
        
    def _reprocess_with_feedback(self):
        """Reprocess documents with accumulated feedback"""
        request = self.request_manager.get_active_request()
        if not request or not request.document_folder:
            return
            
        # Get feedback statistics
        stats = self.feedback_manager.get_statistics(request.id)
        
        if stats["total_corrections"] == 0:
            QMessageBox.information(
                self,
                "No Feedback",
                "No corrections have been made yet to learn from."
            )
            return
            
        # Confirm reprocessing
        reply = QMessageBox.question(
            self,
            "Reprocess with Feedback",
            f"Reprocess {request.total_documents} documents using "
            f"{stats['total_corrections']} corrections?\n\n"
            f"Most common correction: {stats['most_corrected_type']}\n"
            f"Estimated accuracy improvement: {stats['accuracy_improvement']:.1f}%"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._start_processing(reprocess=True)
```

---

## Feature 4: Automated Redaction Application

### Overview
Apply detected PII redactions when exporting documents, replacing sensitive information with exemption codes while maintaining document readability.

### Redaction Implementation

```python
# src/models/document.py (modifications)
@dataclass
class Document:
    """Document with exemption and redaction support"""
    filename: str
    content: str
    classification: str | None = None
    confidence: float | None = None
    justification: str | None = None
    exemptions: list[dict[str, Any]] = field(default_factory=list)
    human_decision: str | None = None
    human_feedback: str | None = None
    
    def get_redacted_content(self, 
                           apply_redactions: bool = True,
                           redaction_format: str = "[REDACTED - {code}]") -> str:
        """Get content with exemptions redacted"""
        
        if not apply_redactions or not self.exemptions:
            return self.content
            
        # Sort exemptions by position (reverse order for replacement)
        sorted_exemptions = sorted(
            self.exemptions,
            key=lambda e: e.get("start", 0),
            reverse=True
        )
        
        redacted_content = self.content
        
        for exemption in sorted_exemptions:
            start = exemption.get("start", 0)
            end = exemption.get("end", 0)
            code = exemption.get("exemption_code", "b6")
            
            # Validate positions
            if start >= 0 and end > start and end <= len(redacted_content):
                # Apply redaction
                redaction_text = redaction_format.format(code=code.upper())
                redacted_content = (
                    redacted_content[:start] + 
                    redaction_text + 
                    redacted_content[end:]
                )
            else:
                logger.warning(
                    f"Invalid exemption position in {self.filename}: "
                    f"start={start}, end={end}, content_length={len(redacted_content)}"
                )
                
        return redacted_content
        
    def get_exemption_summary(self) -> Dict[str, int]:
        """Get summary of exemptions by type"""
        summary = defaultdict(int)
        for exemption in self.exemptions:
            exemption_type = exemption.get("type", "unknown")
            summary[exemption_type] += 1
        return dict(summary)
        
    def validate_exemptions(self) -> List[str]:
        """Validate exemption positions don't overlap"""
        errors = []
        
        # Check for overlaps
        sorted_exemptions = sorted(
            self.exemptions,
            key=lambda e: e.get("start", 0)
        )
        
        for i in range(len(sorted_exemptions) - 1):
            current = sorted_exemptions[i]
            next_exemption = sorted_exemptions[i + 1]
            
            if current.get("end", 0) > next_exemption.get("start", 0):
                errors.append(
                    f"Overlapping exemptions: {current} and {next_exemption}"
                )
                
        return errors
```

### Export Manager Enhancement

```python
# src/processing/export_manager.py
from pathlib import Path
from typing import List, Dict, Any
import csv
import json
from datetime import datetime

class ExportManager:
    """Handles document export with redaction support"""
    
    def __init__(self):
        self.export_formats = ["csv", "json", "txt", "redacted_txt"]
        
    def export_documents(
        self,
        documents: List[Document],
        output_dir: Path,
        format: str = "csv",
        apply_redactions: bool = True,
        include_metadata: bool = True
    ) -> Path:
        """Export documents in specified format"""
        
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "csv":
            return self._export_csv(documents, output_dir, timestamp, include_metadata)
        elif format == "json":
            return self._export_json(documents, output_dir, timestamp, include_metadata)
        elif format == "txt":
            return self._export_text(documents, output_dir, timestamp, apply_redactions=False)
        elif format == "redacted_txt":
            return self._export_text(documents, output_dir, timestamp, apply_redactions=True)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
    def _export_text(
        self,
        documents: List[Document],
        output_dir: Path,
        timestamp: str,
        apply_redactions: bool
    ) -> Path:
        """Export documents as text files with optional redactions"""
        
        export_subdir = output_dir / f"export_{timestamp}"
        export_subdir.mkdir(exist_ok=True)
        
        if apply_redactions:
            docs_dir = export_subdir / "redacted_documents"
        else:
            docs_dir = export_subdir / "original_documents"
            
        docs_dir.mkdir(exist_ok=True)
        
        for doc in documents:
            if doc.human_decision == "responsive" or doc.classification == "responsive":
                # Get content (redacted or original)
                content = doc.get_redacted_content(apply_redactions)
                
                # Write to file
                output_path = docs_dir / doc.filename
                output_path.write_text(content, encoding='utf-8')
                
        # Create manifest
        manifest = {
            "export_timestamp": timestamp,
            "total_documents": len(documents),
            "redactions_applied": apply_redactions,
            "responsive_count": sum(
                1 for d in documents 
                if d.human_decision == "responsive" or d.classification == "responsive"
            )
        }
        
        manifest_path = export_subdir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        
        return export_subdir
        
    def generate_exemption_log(
        self,
        documents: List[Document],
        output_path: Path
    ) -> Path:
        """Generate detailed exemption log"""
        
        log_path = output_path / "exemption_log.csv"
        
        with open(log_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Document", "Exemption Type", "Exemption Code", 
                "Count", "Sample Text"
            ])
            
            for doc in documents:
                if doc.exemptions:
                    # Group by type
                    by_type = defaultdict(list)
                    for exemption in doc.exemptions:
                        by_type[exemption.get("type", "unknown")].append(exemption)
                        
                    for exemption_type, exemptions in by_type.items():
                        # Get sample (first occurrence)
                        sample = exemptions[0]
                        sample_text = doc.content[
                            sample.get("start", 0):sample.get("end", 0)
                        ]
                        
                        writer.writerow([
                            doc.filename,
                            exemption_type,
                            sample.get("exemption_code", "b6"),
                            len(exemptions),
                            f"'{sample_text}' (redacted)"
                        ])
                        
        return log_path
```

### Enhanced Finalize Tab

```python
# src/gui/tabs/finalize_tab.py (modifications)
class FinalizeTab(QWidget):
    def _setup_export_controls(self):
        """Setup export controls with redaction options"""
        
        # Export format selection
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "CSV - Metadata Only",
            "JSON - Full Export", 
            "Text Files - Original",
            "Text Files - Redacted",
            "FOIA Package - Complete"
        ])
        
        # Redaction options
        self.redaction_group = QGroupBox("Redaction Options")
        redaction_layout = QVBoxLayout()
        
        self.apply_redactions_cb = QCheckBox("Apply redactions to exports")
        self.apply_redactions_cb.setChecked(True)
        
        self.redaction_format_combo = QComboBox()
        self.redaction_format_combo.addItems([
            "[REDACTED - {code}]",
            "[{code}]",
            "[REDACTED]",
            "█████"
        ])
        
        self.preview_button = QPushButton("Preview Redacted")
        self.preview_button.clicked.connect(self._preview_redacted)
        
        redaction_layout.addWidget(self.apply_redactions_cb)
        redaction_layout.addWidget(QLabel("Redaction Format:"))
        redaction_layout.addWidget(self.redaction_format_combo)
        redaction_layout.addWidget(self.preview_button)
        
        self.redaction_group.setLayout(redaction_layout)
        
    def _preview_redacted(self):
        """Show preview of redacted document"""
        current_doc = self._get_selected_document()
        if not current_doc:
            return
            
        # Get redaction format
        format_template = self.redaction_format_combo.currentText()
        
        # Show preview dialog
        preview_dialog = RedactionPreviewDialog(
            current_doc,
            format_template,
            self
        )
        preview_dialog.exec()
        
    def _generate_foia_package(self):
        """Generate complete FOIA response package"""
        
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )
        
        if not output_dir:
            return
            
        try:
            # Create package structure
            package_dir = Path(output_dir) / f"FOIA_Package_{datetime.now():%Y%m%d_%H%M%S}"
            package_dir.mkdir()
            
            # Export redacted documents
            responsive_docs = [
                d for d in self.documents 
                if d.human_decision == "responsive" or d.classification == "responsive"
            ]
            
            if responsive_docs:
                docs_dir = package_dir / "responsive_documents"
                docs_dir.mkdir()
                
                for doc in responsive_docs:
                    content = doc.get_redacted_content(True)
                    (docs_dir / doc.filename).write_text(content)
                    
            # Generate exemption log
            self.export_manager.generate_exemption_log(
                self.documents,
                package_dir
            )
            
            # Generate cover letter
            self._generate_cover_letter(package_dir, responsive_docs)
            
            # Show success
            QMessageBox.information(
                self,
                "Package Created",
                f"FOIA package created successfully:\n{package_dir}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to create package: {str(e)}"
            )
```

---

## Integration Architecture

### System-Wide Changes

1. **MainWindow Updates**
```python
# src/gui/main_window.py
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize managers
        self.request_manager = RequestManager()
        self.feedback_manager = FeedbackManager()
        self.export_manager = ExportManager()
        
        # Create tabs with manager references
        self.requests_tab = RequestsTab(self.request_manager)
        self.intake_tab = IntakeTab(self.request_manager, self.feedback_manager)
        self.review_tab = ReviewTab(self.request_manager, self.feedback_manager)
        self.finalize_tab = FinalizeTab(self.request_manager, self.export_manager)
        
        # Connect signals for request context switching
        self.requests_tab.request_selected.connect(self._on_request_selected)
        self.requests_tab.request_deleted.connect(self._on_request_deleted)
```

2. **Document Storage Enhancement**
```python
# src/processing/document_store.py
class DocumentStore:
    """In-memory document storage with request isolation"""
    
    def __init__(self):
        self._documents: Dict[str, Dict[str, Document]] = defaultdict(dict)
        
    def add_document(self, request_id: str, document: Document):
        """Add document to request-specific store"""
        self._documents[request_id][document.filename] = document
        
    def get_documents(self, request_id: str) -> List[Document]:
        """Get all documents for a request"""
        return list(self._documents[request_id].values())
        
    def clear_request(self, request_id: str):
        """Clear all documents for a request"""
        if request_id in self._documents:
            del self._documents[request_id]
```

---

## Migration Strategy

### Phase 1: Multi-Request Foundation (Week 1)
1. Implement RequestManager and data models
2. Add RequestsTab UI
3. Update MainWindow with request context
4. Test request creation and switching

### Phase 2: Parallel Processing (Week 1-2)
1. Implement ParallelDocumentProcessor
2. Update ProcessingWorker
3. Add progress aggregation
4. Performance testing and optimization

### Phase 3: Learning System (Week 2)
1. Implement FeedbackManager
2. Update classifier with few-shot learning
3. Add reprocessing UI
4. Test accuracy improvements

### Phase 4: Redaction System (Week 2-3)
1. Implement redaction methods
2. Update export functionality
3. Add preview capabilities
4. Validate PII removal

---

## Testing Strategy

### Unit Tests
```python
# tests/test_redaction.py
def test_redaction_application():
    """Test that redactions are correctly applied"""
    doc = Document(
        filename="test.txt",
        content="Call me at 555-123-4567 or email test@example.com",
        exemptions=[
            {"start": 11, "end": 23, "type": "phone", "exemption_code": "b6"},
            {"start": 34, "end": 50, "type": "email", "exemption_code": "b6"}
        ]
    )
    
    redacted = doc.get_redacted_content()
    assert "555-123-4567" not in redacted
    assert "[REDACTED - B6]" in redacted
    assert "test@example.com" not in redacted

# tests/test_parallel_processing.py
def test_document_distribution():
    """Test even distribution of documents to workers"""
    processor = ParallelDocumentProcessor(num_workers=4)
    documents = [Path(f"doc{i}.txt") for i in range(17)]
    
    batches = processor._create_batches(documents)
    assert len(batches) == 4
    assert len(batches[0]) == 4  # First three get 4 docs
    assert len(batches[3]) == 5  # Last gets 5 docs
```

### Integration Tests
- Multi-request workflow testing
- Parallel processing performance benchmarks
- Feedback learning effectiveness
- Redaction accuracy validation

### Performance Tests
- Target: 75% reduction in processing time
- Measure: Documents per minute with parallel processing
- Memory usage with multiple active requests
- UI responsiveness during heavy processing

---

## Performance Considerations

### Memory Management
- Each request maintains separate document storage
- Feedback examples limited to most recent 5-10
- Worker processes release memory after batch completion
- No persistence between sessions maintains low memory footprint

### Processing Optimization
- ProcessPoolExecutor for true parallelism
- Batch size optimization based on document count
- Shared progress counter for minimal overhead
- Compiled regex patterns for exemption detection

### UI Responsiveness
- All processing in separate threads/processes
- Progress updates throttled to 10Hz
- Virtual scrolling for large document lists
- Lazy loading of document content in viewers

---

## Security Considerations

### Process Isolation
- Each worker process has isolated memory space
- No shared state between workers except progress counter
- API keys passed through environment variables
- No inter-process communication of document content

### Data Isolation
- Requests maintain separate document stores
- No cross-request data access
- Feedback scoped to individual requests
- Export operations validate request context

### Redaction Security
- Original documents never modified
- Redactions applied only on export
- Position-based redaction prevents regex bypass
- Validation of exemption positions before application

### No Persistence
- All data remains in memory only
- No database or file system storage
- Session data cleared on application exit
- No recovery of previous sessions

---

## Conclusion

Epic 2 transforms RAPID RESPONSE AI from a single-user, sequential processing tool into a high-performance system capable of handling multiple FOIA requests with AI-powered learning and automated redaction. The architecture maintains the security and simplicity of the original design while delivering significant performance and accuracy improvements.

Key achievements:
- **4x performance improvement** through parallel processing
- **Multi-request support** with isolated contexts
- **Adaptive learning** from user corrections
- **Automated redaction** for secure document export

The implementation follows a phased approach that allows for incremental testing and validation while maintaining system stability throughout the development process.