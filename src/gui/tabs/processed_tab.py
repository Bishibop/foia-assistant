"""Processed documents tab for viewing and exporting reviewed documents."""

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui.styles import create_styled_button
from src.gui.widgets.document_viewer import DocumentViewer
from src.models.document import Document


@dataclass
class ProcessedDocument:
    """Document with review metadata."""

    document: Document
    review_timestamp: datetime
    processing_time: float  # seconds
    flagged_for_review: bool = False


class ProcessedTab(QWidget):
    """Tab for viewing and managing processed documents."""

    # Signals
    export_requested = pyqtSignal(list)  # List of documents to export
    package_requested = pyqtSignal(list)  # List of documents for FOIA package

    def __init__(self) -> None:
        """Initialize the processed tab."""
        super().__init__()
        self.processed_documents: list[ProcessedDocument] = []
        self.filtered_documents: list[ProcessedDocument] = []
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Toolbar
        toolbar_layout = self._create_toolbar()
        layout.addLayout(toolbar_layout)

        # Statistics bar with legend
        stats_layout = QHBoxLayout()
        
        self.stats_label = QLabel("Total: 0 | R: 0 | N: 0 | U: 0 | Agreement: 0%")
        self.stats_label.setStyleSheet(
            """
            QLabel {
                background-color: #f0f0f0;
                padding: 5px 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            """
        )
        self.stats_label.setMaximumHeight(30)
        stats_layout.addWidget(self.stats_label)
        
        stats_layout.addStretch()
        
        # Legend
        legend_label = QLabel("Legend: ")
        legend_label.setStyleSheet("font-weight: bold;")
        stats_layout.addWidget(legend_label)
        
        # Disagreement indicator
        disagreement_sample = QLabel("  Disagreement  ")
        disagreement_sample.setStyleSheet(
            """
            QLabel {
                background-color: rgb(255, 200, 200);
                padding: 2px 5px;
                border-radius: 3px;
            }
            """
        )
        stats_layout.addWidget(disagreement_sample)
        
        # Flag indicator
        flag_sample = QLabel("🚩 = Flagged for Review")
        flag_sample.setStyleSheet("padding: 0 10px;")
        stats_layout.addWidget(flag_sample)
        
        layout.addLayout(stats_layout)

        # Main content area with splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(5)

        # Left panel - Document list
        left_panel = self._create_left_panel()
        self.splitter.addWidget(left_panel)

        # Right panel - Document viewer
        right_panel = self._create_right_panel()
        self.splitter.addWidget(right_panel)

        # Set initial splitter sizes (40/60 ratio)
        self.splitter.setSizes([400, 600])

        layout.addWidget(self.splitter)
        self.setLayout(layout)

    def _create_toolbar(self) -> QHBoxLayout:
        """Create the toolbar with search and filter controls."""
        toolbar = QHBoxLayout()

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search documents...")
        self.search_input.setMaximumWidth(250)
        self.search_input.textChanged.connect(self.apply_filters)
        toolbar.addWidget(self.search_input)

        # Filter dropdown
        self.filter_dropdown = QComboBox()
        self.filter_dropdown.addItems(
            [
                "All Documents",
                "Responsive",
                "Non-Responsive",
                "Uncertain",
                "Disagreements Only",
            ]
        )
        self.filter_dropdown.currentIndexChanged.connect(self.apply_filters)
        toolbar.addWidget(self.filter_dropdown)

        # Date range button
        self.date_range_button = QPushButton("Date Range ▼")
        self.date_range_button.clicked.connect(self.show_date_picker)
        toolbar.addWidget(self.date_range_button)

        toolbar.addStretch()

        # Generate package button
        self.generate_package_button = create_styled_button(
            "Generate FOIA Package", "primary"
        )
        self.generate_package_button.clicked.connect(self.generate_foia_package)
        toolbar.addWidget(self.generate_package_button)

        # Export button (dynamic text)
        self.export_button = create_styled_button("Export All", "secondary")
        self.export_button.clicked.connect(self.export_documents)
        toolbar.addWidget(self.export_button)

        return toolbar

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with document list and export options."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Document table
        self.document_table = QTableWidget()
        self.document_table.setColumnCount(6)
        self.document_table.setHorizontalHeaderLabels(
            ["", "Filename", "AI", "Human", "Time", "Flag"]
        )
        self.document_table.setColumnWidth(0, 30)  # Checkbox column
        self.document_table.setColumnWidth(5, 50)  # Flag column
        self.document_table.setSortingEnabled(True)
        self.document_table.setAlternatingRowColors(True)
        self.document_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.document_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.document_table.itemSelectionChanged.connect(self.on_document_selected)
        layout.addWidget(self.document_table)

        # Export format options
        export_group = QGroupBox("Export Formats")
        export_layout = QHBoxLayout()

        self.csv_checkbox = QCheckBox("CSV")
        self.csv_checkbox.setChecked(True)
        self.excel_checkbox = QCheckBox("Excel")
        self.pdf_checkbox = QCheckBox("PDF")
        self.json_checkbox = QCheckBox("JSON")

        export_layout.addWidget(self.csv_checkbox)
        export_layout.addWidget(self.excel_checkbox)
        export_layout.addWidget(self.pdf_checkbox)
        export_layout.addWidget(self.json_checkbox)
        export_layout.addStretch()

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        panel.setLayout(layout)
        return panel

    def _create_right_panel(self) -> QWidget:
        """Create the right panel with document viewer."""
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Document viewer
        self.document_viewer = DocumentViewer()
        layout.addWidget(self.document_viewer)

        # Decision info panel
        self.decision_panel = QWidget()
        decision_layout = QVBoxLayout()

        self.ai_decision_label = QLabel("AI Classification: -")
        self.human_decision_label = QLabel("Human Decision: -")
        self.confidence_label = QLabel("Confidence: -")

        decision_layout.addWidget(self.ai_decision_label)
        decision_layout.addWidget(self.human_decision_label)
        decision_layout.addWidget(self.confidence_label)

        # Flag for review button
        self.flag_button = create_styled_button("Flag for Review", "secondary")
        self.flag_button.clicked.connect(self.toggle_flag)
        decision_layout.addWidget(self.flag_button)

        self.decision_panel.setLayout(decision_layout)
        self.decision_panel.setMaximumHeight(150)
        layout.addWidget(self.decision_panel)

        panel.setLayout(layout)
        return panel

    def add_processed_document(self, document: Document) -> None:
        """Add a newly processed document from the review tab."""
        # For now, use a dummy processing time
        # In a real implementation, this would be tracked during processing
        processed_doc = ProcessedDocument(
            document=document,
            review_timestamp=datetime.now(timezone.utc),
            processing_time=2.5,  # Placeholder
            flagged_for_review=False,
        )
        self.processed_documents.append(processed_doc)
        self.apply_filters()
        self.update_statistics()

    def apply_filters(self) -> None:
        """Apply current filters to the document list."""
        # Start with all documents
        filtered = self.processed_documents.copy()

        # Apply text search
        search_text = self.search_input.text().lower()
        if search_text:
            filtered = [
                doc
                for doc in filtered
                if search_text in doc.document.filename.lower()
                or search_text in doc.document.content.lower()
            ]

        # Apply classification filter
        filter_index = self.filter_dropdown.currentIndex()
        if filter_index == 1:  # Responsive
            filtered = [
                doc for doc in filtered if doc.document.human_decision == "responsive"
            ]
        elif filter_index == 2:  # Non-Responsive
            filtered = [
                doc
                for doc in filtered
                if doc.document.human_decision == "non_responsive"
            ]
        elif filter_index == 3:  # Uncertain
            filtered = [
                doc for doc in filtered if doc.document.human_decision == "uncertain"
            ]
        elif filter_index == 4:  # Disagreements Only
            filtered = [
                doc
                for doc in filtered
                if doc.document.classification != doc.document.human_decision
            ]

        # TODO: Apply date range filter when implemented

        self.filtered_documents = filtered
        self.refresh_table()

    def refresh_table(self) -> None:
        """Refresh the document table with filtered results."""
        self.document_table.setRowCount(len(self.filtered_documents))

        for row, proc_doc in enumerate(self.filtered_documents):
            doc = proc_doc.document

            # Checkbox
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.update_export_button)
            self.document_table.setCellWidget(row, 0, checkbox)

            # Filename
            self.document_table.setItem(row, 1, QTableWidgetItem(doc.filename))

            # AI Classification
            ai_item = QTableWidgetItem(doc.classification or "-")
            self.document_table.setItem(row, 2, ai_item)

            # Human Decision
            human_item = QTableWidgetItem(doc.human_decision or "-")
            self.document_table.setItem(row, 3, human_item)

            # Processing Time
            time_item = QTableWidgetItem(f"{proc_doc.processing_time:.1f}s")
            self.document_table.setItem(row, 4, time_item)

            # Flag
            flag_item = QTableWidgetItem("🚩" if proc_doc.flagged_for_review else "")
            flag_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.document_table.setItem(row, 5, flag_item)

            # Style row if there's a disagreement
            if doc.classification != doc.human_decision:
                for col in range(self.document_table.columnCount()):
                    if col > 0:  # Skip checkbox column
                        item = self.document_table.item(row, col)
                        if item:
                            item.setBackground(QColor(255, 200, 200))

    def on_document_selected(self) -> None:
        """Handle document selection in the table."""
        current_row = self.document_table.currentRow()
        if 0 <= current_row < len(self.filtered_documents):
            proc_doc = self.filtered_documents[current_row]
            self.display_document(proc_doc)

    def display_document(self, proc_doc: ProcessedDocument) -> None:
        """Display the selected document in the viewer."""
        doc = proc_doc.document
        self.document_viewer.display_document(
            doc.filename, doc.content, doc.exemptions
        )

        # Update decision info
        self.ai_decision_label.setText(
            f"AI Classification: {doc.classification or '-'}"
        )
        self.human_decision_label.setText(
            f"Human Decision: {doc.human_decision or '-'}"
        )
        confidence_text = (
            f"Confidence: {doc.confidence:.2f}" if doc.confidence else "Confidence: -"
        )
        self.confidence_label.setText(confidence_text)

        # Update flag button
        if proc_doc.flagged_for_review:
            self.flag_button.setText("Remove Flag")
        else:
            self.flag_button.setText("Flag for Review")

    def update_statistics(self) -> None:
        """Update the statistics display."""
        total = len(self.processed_documents)
        if total == 0:
            self.stats_label.setText("Total: 0 | R: 0 | N: 0 | U: 0 | Agreement: 0%")
            return

        responsive = sum(
            1
            for d in self.processed_documents
            if d.document.human_decision == "responsive"
        )
        non_responsive = sum(
            1
            for d in self.processed_documents
            if d.document.human_decision == "non_responsive"
        )
        uncertain = total - responsive - non_responsive

        agreements = sum(
            1
            for d in self.processed_documents
            if d.document.classification == d.document.human_decision
        )
        agreement_rate = (agreements / total * 100) if total > 0 else 0

        self.stats_label.setText(
            f"Total: {total} | R: {responsive} | N: {non_responsive} | "
            f"U: {uncertain} | Agreement: {agreement_rate:.0f}%"
        )

    def update_export_button(self) -> None:
        """Update export button text based on selection."""
        selected_count = 0
        for row in range(self.document_table.rowCount()):
            checkbox = self.document_table.cellWidget(row, 0)
            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected_count += 1

        if selected_count > 0:
            self.export_button.setText(f"Export Selection ({selected_count})")
        else:
            self.export_button.setText("Export All")

    def get_selected_documents(self) -> list[ProcessedDocument]:
        """Get list of selected documents."""
        selected = []
        for row in range(self.document_table.rowCount()):
            checkbox = self.document_table.cellWidget(row, 0)
            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected.append(self.filtered_documents[row])
        return selected

    def show_date_picker(self) -> None:
        """Show date range picker dialog."""
        # TODO: Implement date picker dialog
        pass

    def toggle_flag(self) -> None:
        """Toggle flag for review on current document."""
        current_row = self.document_table.currentRow()
        if 0 <= current_row < len(self.filtered_documents):
            proc_doc = self.filtered_documents[current_row]
            proc_doc.flagged_for_review = not proc_doc.flagged_for_review
            self.refresh_table()
            self.display_document(proc_doc)

    def export_documents(self) -> None:
        """Export documents in selected formats."""
        # Get documents to export
        selected = self.get_selected_documents()
        if not selected and not self.processed_documents:
            QMessageBox.warning(self, "No Documents", "No documents to export.")
            return

        documents_to_export = selected if selected else self.processed_documents

        # Get export directory
        export_dir = QFileDialog.getExistingDirectory(
            self, "Select Export Directory", ""
        )
        if not export_dir:
            return

        # Export in selected formats
        exported_files = []
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if self.csv_checkbox.isChecked():
            filename = self._export_csv(documents_to_export, export_dir, timestamp)
            if filename:
                exported_files.append(filename)

        if self.json_checkbox.isChecked():
            filename = self._export_json(documents_to_export, export_dir, timestamp)
            if filename:
                exported_files.append(filename)

        if self.excel_checkbox.isChecked():
            filename = self._export_excel(documents_to_export, export_dir, timestamp)
            if filename:
                exported_files.append(filename)

        if self.pdf_checkbox.isChecked():
            filename = self._export_pdf(documents_to_export, export_dir, timestamp)
            if filename:
                exported_files.append(filename)

        # Show success message
        if exported_files:
            QMessageBox.information(
                self,
                "Export Complete",
                f"Exported {len(documents_to_export)} documents to:\n"
                + "\n".join(exported_files),
            )

    def _export_csv(
        self, documents: list[ProcessedDocument], export_dir: str, timestamp: str
    ) -> str | None:
        """Export documents to CSV format."""
        try:
            filepath = Path(export_dir) / f"foia_export_{timestamp}.csv"
            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "filename",
                    "ai_classification",
                    "human_decision",
                    "confidence",
                    "review_timestamp",
                    "processing_time",
                    "flagged",
                    "justification",
                    "exemption_count",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for proc_doc in documents:
                    doc = proc_doc.document
                    writer.writerow(
                        {
                            "filename": doc.filename,
                            "ai_classification": doc.classification or "",
                            "human_decision": doc.human_decision or "",
                            "confidence": (
                                f"{doc.confidence:.2f}" if doc.confidence else ""
                            ),
                            "review_timestamp": proc_doc.review_timestamp.isoformat(),
                            "processing_time": f"{proc_doc.processing_time:.1f}",
                            "flagged": "Yes" if proc_doc.flagged_for_review else "No",
                            "justification": doc.justification or "",
                            "exemption_count": (
                                len(doc.exemptions) if doc.exemptions else 0
                            ),
                        }
                    )
            return str(filepath)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {e}")
            return None

    def _export_json(
        self, documents: list[ProcessedDocument], export_dir: str, timestamp: str
    ) -> str | None:
        """Export documents to JSON format."""
        try:
            filepath = Path(export_dir) / f"foia_export_{timestamp}.json"
            data = []

            for proc_doc in documents:
                doc = proc_doc.document
                data.append(
                    {
                        "filename": doc.filename,
                        "content": doc.content,
                        "ai_classification": doc.classification,
                        "human_decision": doc.human_decision,
                        "confidence": doc.confidence,
                        "justification": doc.justification,
                        "exemptions": doc.exemptions or [],
                        "human_feedback": doc.human_feedback,
                        "review_timestamp": proc_doc.review_timestamp.isoformat(),
                        "processing_time": proc_doc.processing_time,
                        "flagged_for_review": proc_doc.flagged_for_review,
                    }
                )

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return str(filepath)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export JSON: {e}")
            return None

    def _export_excel(
        self, documents: list[ProcessedDocument], export_dir: str, timestamp: str
    ) -> str | None:
        """Export documents to Excel format."""
        # TODO: Implement Excel export with openpyxl
        QMessageBox.information(
            self, "Excel Export", "Excel export will be implemented in the next phase."
        )
        return None

    def _export_pdf(
        self, documents: list[ProcessedDocument], export_dir: str, timestamp: str
    ) -> str | None:
        """Export documents to PDF format."""
        # TODO: Implement PDF export with reportlab
        QMessageBox.information(
            self, "PDF Export", "PDF export will be implemented in the next phase."
        )
        return None

    def generate_foia_package(self) -> None:
        """Generate complete FOIA response package."""
        # Get responsive documents only
        responsive_docs = [
            doc
            for doc in self.processed_documents
            if doc.document.human_decision == "responsive"
        ]

        if not responsive_docs:
            QMessageBox.warning(
                self,
                "No Responsive Documents",
                "No responsive documents found to include in FOIA package.",
            )
            return

        # Get output directory
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory for FOIA Package", ""
        )
        if not output_dir:
            return

        try:
            # Create package directory
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            package_dir = Path(output_dir) / f"FOIA_Response_Package_{timestamp}"
            package_dir.mkdir(exist_ok=True)

            # Create subdirectories
            responsive_dir = package_dir / "responsive_documents"
            responsive_dir.mkdir(exist_ok=True)

            # Copy responsive documents
            for proc_doc in responsive_docs:
                doc = proc_doc.document
                doc_path = responsive_dir / doc.filename
                doc_path.write_text(doc.content, encoding="utf-8")

            # Generate exemption log
            self._generate_exemption_log(responsive_docs, package_dir)

            # Generate summary report
            self._generate_summary_report(package_dir)

            # Generate cover letter template
            self._generate_cover_letter(package_dir, len(responsive_docs))

            QMessageBox.information(
                self,
                "Package Generated",
                f"FOIA response package generated successfully:\n{package_dir}",
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Package Generation Error",
                f"Failed to generate FOIA package: {e}",
            )

    def _generate_exemption_log(
        self, responsive_docs: list[ProcessedDocument], package_dir: Path
    ) -> None:
        """Generate CSV log of all exemptions applied."""
        exemption_log_path = package_dir / "exemption_log.csv"

        with open(exemption_log_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "filename",
                "exemption_type",
                "exemption_code",
                "redacted_text",
                "location",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for proc_doc in responsive_docs:
                doc = proc_doc.document
                if doc.exemptions:
                    for exemption in doc.exemptions:
                        writer.writerow(
                            {
                                "filename": doc.filename,
                                "exemption_type": exemption.get("type", ""),
                                "exemption_code": exemption.get("exemption_code", ""),
                                "redacted_text": exemption.get("text", ""),
                                "location": f"{exemption.get('start', '')}-{exemption.get('end', '')}",
                            }
                        )

    def _generate_summary_report(self, package_dir: Path) -> None:
        """Generate processing summary report."""
        summary_path = package_dir / "processing_summary.txt"

        total = len(self.processed_documents)
        responsive = sum(
            1
            for d in self.processed_documents
            if d.document.human_decision == "responsive"
        )
        non_responsive = sum(
            1
            for d in self.processed_documents
            if d.document.human_decision == "non_responsive"
        )
        uncertain = sum(
            1
            for d in self.processed_documents
            if d.document.human_decision == "uncertain"
        )

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("FOIA PROCESSING SUMMARY REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("DOCUMENT STATISTICS:\n")
            f.write(f"Total Documents Processed: {total}\n")
            f.write(f"Responsive Documents: {responsive}\n")
            f.write(f"Non-Responsive Documents: {non_responsive}\n")
            f.write(f"Uncertain Documents: {uncertain}\n\n")

            # Calculate agreement rate
            agreements = sum(
                1
                for d in self.processed_documents
                if d.document.classification == d.document.human_decision
            )
            agreement_rate = (agreements / total * 100) if total > 0 else 0
            f.write(f"AI/Human Agreement Rate: {agreement_rate:.1f}%\n\n")

            # List flagged documents
            flagged = [d for d in self.processed_documents if d.flagged_for_review]
            if flagged:
                f.write(f"DOCUMENTS FLAGGED FOR REVIEW ({len(flagged)}):\n")
                for doc in flagged:
                    f.write(f"- {doc.document.filename}\n")

    def _generate_cover_letter(self, package_dir: Path, responsive_count: int) -> None:
        """Generate FOIA response cover letter template."""
        cover_letter_path = package_dir / "cover_letter_template.txt"

        with open(cover_letter_path, "w", encoding="utf-8") as f:
            f.write("[AGENCY LETTERHEAD]\n\n")
            f.write(f"Date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}\n\n")
            f.write("[Requester Name]\n")
            f.write("[Requester Address]\n\n")
            f.write("Re: Freedom of Information Act Request\n\n")
            f.write("Dear [Requester Name]:\n\n")
            f.write(
                "This letter is in response to your Freedom of Information Act (FOIA) request "
            )
            f.write(
                "dated [DATE], in which you requested [DESCRIPTION OF REQUEST].\n\n"
            )
            f.write(
                "We have completed our search and review of records responsive to your request. "
            )
            f.write(
                f"We identified {responsive_count} document(s) that are responsive to your request.\n\n"
            )
            f.write(
                "The responsive documents are enclosed with this letter. Some information has been "
            )
            f.write("redacted pursuant to the following FOIA exemptions:\n\n")
            f.write(
                "- Exemption (b)(6): Information that would constitute a clearly unwarranted "
            )
            f.write("invasion of personal privacy\n\n")
            f.write(
                "If you have any questions regarding this response, please contact [CONTACT NAME] "
            )
            f.write("at [CONTACT INFO].\n\n")
            f.write("Sincerely,\n\n")
            f.write("[Name]\n")
            f.write("[Title]\n")
            f.write("[Agency]\n")
