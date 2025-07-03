from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.constants import (
    BUTTON_STYLE_DECISION,
    FEEDBACK_TEXT_MAX_HEIGHT,
    JUSTIFICATION_TEXT_MAX_HEIGHT,
    STAT_COLOR_NON_RESPONSIVE,
    STAT_COLOR_RESPONSIVE,
    STAT_COLOR_UNCERTAIN,
)
from src.gui.styles import (
    create_primary_button,
    create_secondary_button,
    create_warning_button,
)


class DecisionPanel(QWidget):
    """Widget for displaying AI classification and capturing user decisions."""

    decision_made = pyqtSignal(str, str)  # decision, feedback

    def __init__(self) -> None:
        super().__init__()
        self._current_classification: str | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout()

        # AI Classification Display
        ai_group = QGroupBox("AI Classification")
        ai_layout = QVBoxLayout()

        # Classification with confidence
        self._classification_label = QLabel("Classification: -")
        self._classification_label.setStyleSheet("font-weight: bold;")
        ai_layout.addWidget(self._classification_label)

        self._confidence_label = QLabel("Confidence: -")
        ai_layout.addWidget(self._confidence_label)

        # Justification
        justification_label = QLabel("Justification:")
        ai_layout.addWidget(justification_label)

        self._justification_text = QTextEdit()
        self._justification_text.setReadOnly(True)
        self._justification_text.setMaximumHeight(JUSTIFICATION_TEXT_MAX_HEIGHT)
        ai_layout.addWidget(self._justification_text)

        # Exemptions summary
        self._exemptions_label = QLabel("Exemptions: None detected")
        ai_layout.addWidget(self._exemptions_label)

        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)

        # Decision Controls
        decision_group = QGroupBox("Your Decision")
        decision_layout = QVBoxLayout()

        # Approve button on its own row
        self._approve_button = create_primary_button("Approve Classification")
        self._approve_button.clicked.connect(lambda: self._make_decision("approved"))
        decision_layout.addWidget(self._approve_button)

        # Override buttons in a horizontal layout
        override_layout = QHBoxLayout()
        override_layout.setSpacing(5)

        self._override_responsive = create_secondary_button("Override: Responsive")
        self._override_responsive.clicked.connect(
            lambda: self._make_decision("responsive")
        )
        # Apply custom styling to make this button taller
        self._override_responsive.setStyleSheet(BUTTON_STYLE_DECISION)
        override_layout.addWidget(self._override_responsive)

        self._override_non_responsive = create_secondary_button(
            "Override: Non-Responsive"
        )
        self._override_non_responsive.clicked.connect(
            lambda: self._make_decision("non_responsive")
        )
        # Apply custom styling to make this button taller
        self._override_non_responsive.setStyleSheet(BUTTON_STYLE_DECISION)
        override_layout.addWidget(self._override_non_responsive)

        self._override_uncertain = create_warning_button("Override: Uncertain")
        self._override_uncertain.clicked.connect(
            lambda: self._make_decision("uncertain")
        )
        override_layout.addWidget(self._override_uncertain)

        decision_layout.addLayout(override_layout)
        
        # Override non-duplicate button (hidden by default)
        self._override_non_duplicate = create_warning_button("Override - Non-Duplicate")
        self._override_non_duplicate.clicked.connect(
            lambda: self._make_decision("override_non_duplicate")
        )
        self._override_non_duplicate.setVisible(False)
        decision_layout.addWidget(self._override_non_duplicate)

        # Add spacing between buttons and feedback
        decision_layout.addSpacing(25)

        # Feedback text
        feedback_label = QLabel("Feedback (optional):")
        decision_layout.addWidget(feedback_label)

        self._feedback_text = QTextEdit()
        self._feedback_text.setMaximumHeight(FEEDBACK_TEXT_MAX_HEIGHT)
        self._feedback_text.setPlaceholderText(
            "Add notes about why you made this decision..."
        )
        decision_layout.addWidget(self._feedback_text)

        decision_group.setLayout(decision_layout)
        layout.addWidget(decision_group)

        # Keyboard shortcuts hint
        self._shortcuts_label = QLabel(
            "Shortcuts: Space = Approve | R = Responsive | N = Non-Responsive | U = Uncertain"
        )
        self._shortcuts_label.setStyleSheet("color: gray; font-size: 11px;")
        self._shortcuts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._shortcuts_label)

        layout.addStretch()
        self.setLayout(layout)

    def display_classification(
        self,
        classification: str | None,
        confidence: float | None,
        justification: str | None,
        exemptions: list[dict] | None,
    ) -> None:
        """Display the AI classification results."""
        # Store current classification
        self._current_classification = classification

        # Update classification with color
        if classification:
            color = {
                "responsive": STAT_COLOR_RESPONSIVE,
                "non_responsive": STAT_COLOR_NON_RESPONSIVE,
                "uncertain": STAT_COLOR_UNCERTAIN,
                "duplicate": "#666666",  # Gray color for duplicates
            }.get(classification, "black")

            self._classification_label.setText(
                f"Classification: {classification.replace('_', ' ').title()}"
            )
            self._classification_label.setStyleSheet(
                f"font-weight: bold; font-size: 14px; color: {color};"
            )
        else:
            self._classification_label.setText("Classification: Error")

        # Update confidence
        if confidence is not None:
            self._confidence_label.setText(f"Confidence: {confidence:.1%}")
        else:
            self._confidence_label.setText("Confidence: -")

        # Update justification
        if justification:
            self._justification_text.setPlainText(justification)
        else:
            self._justification_text.setPlainText("No justification provided")

        # Update exemptions
        if exemptions:
            exemption_types = {ex["type"] for ex in exemptions}
            self._exemptions_label.setText(
                f"Exemptions: {len(exemptions)} detected ({', '.join(exemption_types)})"
            )
        else:
            self._exemptions_label.setText("Exemptions: None detected")

        # Enable buttons based on classification
        self._enable_buttons(classification)

    def _make_decision(self, decision: str) -> None:
        feedback = self._feedback_text.toPlainText().strip()
        self.decision_made.emit(decision, feedback)
        self._clear_feedback()

    def _clear_feedback(self) -> None:
        self._feedback_text.clear()

    def _enable_buttons(self, classification: str | None = None) -> None:
        # For duplicates, show only approve and override non-duplicate buttons
        if classification == "duplicate":
            self._approve_button.setEnabled(True)
            self._approve_button.setText("Approve (Skip Duplicate)")
            # Hide normal override buttons
            self._override_responsive.setVisible(False)
            self._override_non_responsive.setVisible(False)
            self._override_uncertain.setVisible(False)
            # Show override non-duplicate button
            self._override_non_duplicate.setVisible(True)
            self._override_non_duplicate.setEnabled(True)
            # Update shortcuts label
            self._shortcuts_label.setText(
                "Shortcuts: Space = Approve | D = Override Non-Duplicate"
            )
        else:
            # Normal behavior for non-duplicates
            self._approve_button.setEnabled(True)
            self._approve_button.setText("Approve AI Decision")
            # Show normal override buttons
            self._override_responsive.setVisible(True)
            self._override_non_responsive.setVisible(True)
            self._override_uncertain.setVisible(True)
            # Hide override non-duplicate button
            self._override_non_duplicate.setVisible(False)
            # Restore normal shortcuts label
            self._shortcuts_label.setText(
                "Shortcuts: Space = Approve | R = Responsive | N = Non-Responsive | U = Uncertain"
            )
            
            # Enable override buttons, but disable the one matching current classification
            self._override_responsive.setEnabled(classification != "responsive")
            self._override_non_responsive.setEnabled(classification != "non_responsive")
            self._override_uncertain.setEnabled(classification != "uncertain")

    def _disable_buttons(self) -> None:
        self._approve_button.setEnabled(False)
        self._override_responsive.setEnabled(False)
        self._override_non_responsive.setEnabled(False)
        self._override_uncertain.setEnabled(False)
        self._override_non_duplicate.setEnabled(False)

    def clear(self) -> None:
        """Clear all classification display and disable buttons."""
        self._current_classification = None
        self._classification_label.setText("Classification: -")
        self._classification_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self._confidence_label.setText("Confidence: -")
        self._justification_text.clear()
        self._exemptions_label.setText("Exemptions: None detected")
        self._feedback_text.clear()
        self._disable_buttons()
