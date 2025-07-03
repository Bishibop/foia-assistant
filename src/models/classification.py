"""Classification types and enums for document processing."""

from enum import Enum


class Classification(str, Enum):
    """Document classification types."""

    RESPONSIVE = "responsive"
    NON_RESPONSIVE = "non_responsive"
    UNCERTAIN = "uncertain"

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return self.value.replace("_", " ").title()

    @classmethod
    def from_string(cls, value: str | None) -> "Classification | None":
        """Create Classification from string value."""
        if not value:
            return None
        try:
            return cls(value.lower())
        except ValueError:
            return None
