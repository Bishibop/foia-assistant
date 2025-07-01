#!/bin/bash

echo "Setting up FOIA Response Assistant development environment..."

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

echo "Setup complete! Don't forget to set your OPENAI_API_KEY environment variable:"
echo "export OPENAI_API_KEY='your-key-here'"