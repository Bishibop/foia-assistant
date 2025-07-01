import sys

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main() -> None:
    """Launch the FOIA Response Assistant application."""
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle("Fusion")

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
