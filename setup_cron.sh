#!/bin/bash
# This script sets up the cron job for the crypto price alert system

# Define the script location - update this to your actual path
SCRIPT_PATH="$HOME/crypto_alert/crypto_alert.py"
LOG_PATH="$HOME/crypto_alert/cron_execution.log"

# Make the script executable
chmod +x "$SCRIPT_PATH"

# Create the crontab entry - runs every 3 hours
CRON_ENTRY="* */3 * * * cd $(dirname $SCRIPT_PATH) && /usr/bin/python3 $SCRIPT_PATH >> $LOG_PATH 2>&1"

# Add the crontab entry
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✅ Cron job has been set up to run the crypto alert script every 3 hours"
echo "📝 Logs will be saved to: $LOG_PATH"
echo "🔍 You can check your crontab with: crontab -l"