#!/bin/bash
# This script sets up the cron jobs for the crypto price alert system with virtual environment support

# Automatically detect the project directory (where this script is located)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_SCRIPT="$PROJECT_DIR/run_crypto_alert.sh"
PYTHON_SCRIPT="$PROJECT_DIR/crypto_alert.py"
UPDATE_52W_SCRIPT="$PROJECT_DIR/update_52w_stats.py"
LOG_PATH="$PROJECT_DIR/cron_execution.log"
UPDATE_52W_LOG="$PROJECT_DIR/update_52w.log"

# Check if virtual environment exists
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "❌ Virtual environment not found at $PROJECT_DIR/venv"
    echo "Please create a virtual environment first:"
    echo "  cd $PROJECT_DIR"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check if Python scripts exist
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Python script not found at $PYTHON_SCRIPT"
    echo "Please make sure crypto_alert.py is in the project directory"
    exit 1
fi

if [ ! -f "$UPDATE_52W_SCRIPT" ]; then
    echo "❌ Python script not found at $UPDATE_52W_SCRIPT"
    echo "Please make sure update_52w_stats.py is in the project directory"
    exit 1
fi

# Make scripts executable
chmod +x "$WRAPPER_SCRIPT"
chmod +x "$PYTHON_SCRIPT"
chmod +x "$UPDATE_52W_SCRIPT"

# Create the crontab entries
# Main alert script - runs every 6 hours
CRON_ENTRY_ALERT="0 */6 * * * $WRAPPER_SCRIPT >> $LOG_PATH 2>&1"
# 52w stats update - runs every Sunday at 3 AM
CRON_ENTRY_52W="0 3 * * 0 cd $PROJECT_DIR && venv/bin/python $UPDATE_52W_SCRIPT >> $UPDATE_52W_LOG 2>&1"

# Check if cron entries already exist
EXISTING_ALERT=$(crontab -l 2>/dev/null | grep -F "$WRAPPER_SCRIPT" || true)
EXISTING_52W=$(crontab -l 2>/dev/null | grep -F "$UPDATE_52W_SCRIPT" || true)

if [ -n "$EXISTING_ALERT" ] || [ -n "$EXISTING_52W" ]; then
    echo "⚠️  Cron job(s) already exist for this project"
    [ -n "$EXISTING_ALERT" ] && echo "Alert script: $EXISTING_ALERT"
    [ -n "$EXISTING_52W" ] && echo "52w update: $EXISTING_52W"
    echo ""
    read -p "Do you want to replace them? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove existing entries and add new ones
        (
            crontab -l 2>/dev/null | grep -v "$WRAPPER_SCRIPT" | grep -v "$UPDATE_52W_SCRIPT"
            echo "$CRON_ENTRY_ALERT"
            echo "$CRON_ENTRY_52W"
        ) | crontab -
        echo "✅ Cron jobs have been updated"
    else
        echo "❌ Setup cancelled"
        exit 0
    fi
else
    # Add the crontab entries
    (
        crontab -l 2>/dev/null
        echo "$CRON_ENTRY_ALERT"
        echo "$CRON_ENTRY_52W"
    ) | crontab -
    echo "✅ Cron jobs have been set up:"
    echo "   - Crypto alert: every 6 hours"
    echo "   - 52w stats update: every Sunday at 3 AM"
fi

echo ""
echo "📝 Logs:"
echo "   - Alert logs: $LOG_PATH"
echo "   - 52w update logs: $UPDATE_52W_LOG"
echo "🔍 Check your crontab with: crontab -l"
echo "🧪 Test scripts manually:"
echo "   - Alert: $WRAPPER_SCRIPT"
echo "   - 52w update: cd $PROJECT_DIR && venv/bin/python $UPDATE_52W_SCRIPT"
echo ""
echo "📋 Current crontab:"
crontab -l 2>/dev/null
