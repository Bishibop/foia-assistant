# FOIA Response Assistant

An AI-powered tool that automates document review and classification for FOIA (Freedom of Information Act) requests. It uses LangGraph workflows and OpenAI to intelligently classify documents, detect duplicates, learn from user feedback, and generate complete FOIA response packages.

## Features

- **Intelligent Document Classification**: AI-powered analysis to determine if documents are responsive, non-responsive, or uncertain
- **Duplicate Detection**: Semantic similarity analysis to identify exact and near-duplicate documents
- **Feedback Learning**: AI learns from user corrections to improve future classifications
- **Parallel Processing**: High-performance processing for large document sets
- **Complete FOIA Packages**: Automated generation of response packages with cover letters and exemption logs

## Requirements

- Python 3.11+
- OpenAI API key

## Setup

1. Clone and enter the repository:
   ```bash
   git clone <repository-url>
   cd foia-assistant
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. Configure API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

## Complete Walkthrough

Launch the GUI application:
```bash
source venv/bin/activate && python -m src.main
```

Follow these steps to experience the full FOIA processing workflow:

### 1. Requests Tab
- Select the "Blue Sky Project" request (F-2024-00123) - this request has a deadline and serves as a realistic example
- Click "Make Active" to set this as your working request

### 2. Intake Tab  
- Click "Browse" and navigate to the `sample_docs` folder in the project directory
- Click "Start Processing" to begin document analysis
- Watch as the system:
  - Generates embeddings for duplicate detection
  - Classifies documents using AI
  - Shows real-time progress with parallel processing

### 3. Review Tab
- Review the AI's classification decisions for each document
- Use "Approve" to accept correct classifications
- Use "Override" to correct any misclassifications and provide feedback
- Notice how the system learns from your corrections for future processing

### 4. Finalize Tab
- Review all processed documents and their final classifications
- Use "Select All Non-Duplicates" to quickly select original documents
- Click "Generate FOIA Package" to create a complete response package
- The system will generate:
  - A folder with all responsive documents
  - Cover letter template
  - Processing summary report
  - Exemption log (if applicable)

## Documentation

See the `docs/` folder for detailed documentation:
- [Implementation Plan](docs/foia_implementation_plan.md)
- [Problem Space Analysis](docs/foia_brainlift.md)
- [Technical Stack](docs/foia_tech_stack.md)