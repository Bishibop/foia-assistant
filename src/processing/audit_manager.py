"""Audit manager for logging and tracking all document processing activities.
"""
import csv
from pathlib import Path

from ..models.audit import AuditEntry


class AuditManager:
    """Manages audit trail logging and export."""

    def __init__(self):
        """Initialize empty audit log."""
        self._entries: list[AuditEntry] = []

    def log_classification(self, filename: str, result: str,
                         confidence: float, request_id: str) -> None:
        """Log an AI classification event.
        
        Args:
            filename: The document filename
            result: The classification result
            confidence: The confidence score
            request_id: The FOIA request ID

        """
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
        """Log a user review decision.
        
        Args:
            filename: The document filename
            ai_result: The AI's classification
            user_decision: The user's decision
            request_id: The FOIA request ID

        """
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
        """Log a document view event.
        
        Args:
            filename: The document filename
            tab_name: The tab where document was viewed
            request_id: The FOIA request ID

        """
        entry = AuditEntry(
            request_id=request_id,
            document_filename=filename,
            event_type="view",
            details=f"Document viewed in {tab_name}"
        )
        self._entries.append(entry)

    def log_export(self, format: str, document_count: int,
                  request_id: str, selected_files: list[str] | None = None) -> None:
        """Log an export event.
        
        Args:
            format: The export format (CSV, JSON, Excel, PDF)
            document_count: Number of documents exported
            request_id: The FOIA request ID
            selected_files: List of selected filenames (optional)

        """
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

    def log_error(self, filename: str | None, error_message: str,
                 request_id: str) -> None:
        """Log an error event.
        
        Args:
            filename: The document filename (optional)
            error_message: The error message
            request_id: The FOIA request ID

        """
        entry = AuditEntry(
            request_id=request_id,
            document_filename=filename,
            event_type="error",
            details=f"Error: {error_message}"
        )
        self._entries.append(entry)

    def get_entries(self, request_id: str | None = None,
                   document_filter: list[str] | None = None) -> list[AuditEntry]:
        """Get audit entries with optional filtering.
        
        Args:
            request_id: Filter by request ID (optional)
            document_filter: Filter by document filenames (optional)
            
        Returns:
            List of matching audit entries

        """
        entries = self._entries

        # Filter by request ID if provided
        if request_id:
            entries = [e for e in entries if e.request_id == request_id]

        # Filter by documents if provided
        if document_filter:
            entries = [e for e in entries
                      if e.document_filename in document_filter]

        return entries

    def export_csv(self, filepath: Path) -> None:
        """Export all audit entries to CSV file.
        
        Args:
            filepath: Path to save the CSV file

        """
        # Sort entries chronologically
        entries = sorted(self._entries, key=lambda e: e.timestamp)

        # Write to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['timestamp', 'request_id', 'document',
                         'event', 'details', 'ai_result', 'user_decision']
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            # Write header
            writer.writeheader()

            # Write entries
            for entry in entries:
                writer.writerow(entry.to_dict())

    def get_all_documents(self) -> list[tuple[str, str]]:
        """Get all unique document-request pairs for filtering.
        
        Returns:
            List of (filename, request_id) tuples

        """
        doc_request_pairs = set()

        for entry in self._entries:
            if entry.document_filename:
                doc_request_pairs.add((entry.document_filename, entry.request_id))

        # Return sorted list
        return sorted(list(doc_request_pairs))

    def log_embedding(self, filename: str, request_id: str, 
                     success: bool, processing_time: float | None = None,
                     error_message: str | None = None) -> None:
        """Log an embedding generation event.
        
        Args:
            filename: The document filename
            request_id: The FOIA request ID
            success: Whether embedding generation was successful
            processing_time: Time taken to generate embedding (optional)
            error_message: Error message if failed (optional)

        """
        if success:
            details = "Embedding generated successfully"
            if processing_time:
                details += f" in {processing_time:.2f}s"
        else:
            details = f"Embedding generation failed: {error_message or 'Unknown error'}"
        
        entry = AuditEntry(
            request_id=request_id,
            document_filename=filename,
            event_type="embedding",
            details=details
        )
        self._entries.append(entry)

    def log_duplicate(self, filename: str, request_id: str, 
                     is_duplicate: bool, duplicate_of: str | None = None,
                     similarity_score: float | None = None) -> None:
        """Log a duplicate detection/marking event.
        
        Args:
            filename: The document filename
            request_id: The FOIA request ID
            is_duplicate: Whether document was marked as duplicate
            duplicate_of: Original document filename if duplicate
            similarity_score: Similarity score if near-duplicate

        """
        if is_duplicate:
            if similarity_score == 1.0:
                details = f"Marked as exact duplicate of {duplicate_of}"
            else:
                details = f"Marked as duplicate of {duplicate_of}"
                if similarity_score:
                    details += f" ({similarity_score:.1%} similar)"
        else:
            details = "Marked as original document (no duplicates found)"
        
        entry = AuditEntry(
            request_id=request_id,
            document_filename=filename,
            event_type="duplicate",
            details=details
        )
        self._entries.append(entry)

    def get_entry_count(self) -> int:
        """Get total number of audit entries.
        
        Returns:
            Number of audit entries

        """
        return len(self._entries)
