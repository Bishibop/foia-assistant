"""Utility functions for calculating document statistics."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.gui.tabs.finalize_tab import ProcessedDocument


@dataclass
class DocumentStatistics:
    """Container for document processing statistics."""

    total: int
    responsive: int
    non_responsive: int
    uncertain: int
    agreements: int
    agreement_rate: float

    def to_display_string(self) -> str:
        """Format statistics for display in UI."""
        return (
            f"Total: {self.total} | R: {self.responsive} | N: {self.non_responsive} | "
            f"U: {self.uncertain} | Agreement: {self.agreement_rate:.0f}%"
        )


def calculate_document_statistics(
    documents: list["ProcessedDocument"],
) -> DocumentStatistics:
    """Calculate statistics for a list of processed documents.

    Args:
        documents: List of processed documents to analyze

    Returns:
        DocumentStatistics object containing calculated statistics

    """
    total = len(documents)

    if total == 0:
        return DocumentStatistics(
            total=0,
            responsive=0,
            non_responsive=0,
            uncertain=0,
            agreements=0,
            agreement_rate=0.0,
        )

    responsive = sum(1 for d in documents if d.document.human_decision == "responsive")

    non_responsive = sum(
        1 for d in documents if d.document.human_decision == "non_responsive"
    )

    uncertain = total - responsive - non_responsive

    agreements = sum(
        1 for d in documents if d.document.classification == d.document.human_decision
    )

    agreement_rate = (agreements / total * 100) if total > 0 else 0

    return DocumentStatistics(
        total=total,
        responsive=responsive,
        non_responsive=non_responsive,
        uncertain=uncertain,
        agreements=agreements,
        agreement_rate=agreement_rate,
    )
