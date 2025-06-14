#!/bin/bash
# Quick install script for MkDocs with Material theme

echo "Creating virtual environment..."
python3 -m venv venv-docs

echo "Activating virtual environment..."
source venv-docs/bin/activate

echo "Installing core MkDocs and Material theme..."
pip install --upgrade pip
pip install mkdocs mkdocs-material

echo "Installing additional plugins..."
pip install pymdown-extensions pygments

echo "MkDocs installation complete!"
echo "To serve the site, run:"
echo "  source venv-docs/bin/activate"
echo "  mkdocs serve"