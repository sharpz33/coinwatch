#!/bin/bash
# This script sets up the cron job for the crypto price alert system with virtual environment support

# Define the project directory - update this to your actual path
PROJECT_DIR="$HOME/crypto_alert"
WRAPPER_SCRIPT="$PROJECT_DIR/run_crypto_alert.sh"
PYTHON_SCRIPT="$PROJECT_DIR/crypto_alert.py"
LOG_PATH="$PROJECT_DIR/cron_execution.log"

# Check if virtual environment exists
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "❌ Virtual environment not found at $PROJECT_DIR/venv"
    echo "Please create a virtual environment first:"
    echo "  cd $PROJECT_DIR"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install requests python-dotenv"
    exit 1
fi

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Python script not found at $PYTHON_SCRIPT"
    echo "Please make sure crypto_alert.py is in the project directory"
    exit 1
fi

# Make scripts executable
chmod +x "$WRAPPER_SCRIPT"
chmod +x "$PYTHON_SCRIPT"

# Create the crontab entry - runs every 15 minutes using the wrapper script
CRON_ENTRY="*/15 * * * * $WRAPPER_SCRIPT >> $LOG_PATH 2>&1"

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "$WRAPPER_SCRIPT"; then
    echo "⚠️  Cron job already exists for this script"
    echo "Current crontab entries containing the wrapper script:"
    crontab -l 2>/dev/null | grep "$WRAPPER_SCRIPT"
    echo ""
    read -p "Do you want to replace it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove existing entry and add new one
        (
            crontab -l 2>/dev/null | grep -v "$WRAPPER_SCRIPT"
            echo "$CRON_ENTRY"
        ) | crontab -
        echo "✅ Cron job has been updated"
    else
        echo "❌ Setup cancelled"
        exit 0
    fi
else
    # Add the crontab entry
    (
        crontab -l 2>/dev/null
        echo "$CRON_ENTRY"
    ) | crontab -
    echo "✅ Cron job has been set up to run the crypto alert script every 15 minutes"
fi

echo "📝 Logs will be saved to: $LOG_PATH"
echo "🔍 You can check your crontab with: crontab -l"
echo "🧪 Test the wrapper script manually with: $WRAPPER_SCRIPT"
echo ""
echo "📋 Current crontab:"
crontab -l 2>/dev/null
