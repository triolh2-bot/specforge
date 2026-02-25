#!/bin/bash

# SpecForge Startup Script

echo "🔓 Starting SpecForge..."

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "Installing Flask..."
    pip install -r requirements.txt
fi

# Run the app
echo "🚀 SpecForge running on http://localhost:5000"
python app.py
