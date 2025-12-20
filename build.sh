#!/bin/bash
# Render Build Script
# This script runs during Render deployment

set -e  # Exit on error

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r api/requirements.txt

echo "=== Downloading spaCy English model ==="
python -m spacy download en_core_web_sm

echo "=== Verifying spaCy installation ==="
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('spaCy model loaded successfully')"

echo "=== Build complete ==="
