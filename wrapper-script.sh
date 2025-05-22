#!/bin/bash

# Crypto Alert Wrapper Script for Cron
# This script activates the virtual environment and runs the Python script

# Set the project directory - update this to your actual path
PROJECT_DIR="$HOME/app/finance_alert"

# Change to the project directory
cd "$PROJECT_DIR" || {
    echo "Error: Could not change to project directory: $PROJECT_DIR"
    exit 1
}

# Activate the virtual environment
source "$PROJECT_DIR/venv/bin/activate" || {
    echo "Error: Could not activate virtual environment"
    exit 1
}

# Set PYTHONPATH to ensure proper module loading
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Run the Python script
python "$PROJECT_DIR/crypto_alert.py"

# Capture the exit code
EXIT_CODE=$?

# Deactivate the virtual environment
deactivate

# Exit with the same code as the Python script
exit $EXIT_CODE
