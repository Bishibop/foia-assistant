import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

from .constants import APP_STYLE
from .gui.main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)


def main() -> None:
    """Launch the FOIA Response Assistant application."""
    # Load environment variables from .env file
    # Find the .env file relative to this script
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)

    app = QApplication(sys.argv)

    # Set application style
    app.setStyle(APP_STYLE)

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
