# Cryptocurrency ATH Drop Alert System - Installation Guide

This guide will help you set up a cron-based system to monitor Bitcoin and Ethereum price drops from their All-Time Highs (ATH) and send alerts to Discord when specific thresholds are crossed.

## Prerequisites

- Linux/Unix-based system (for cron)
- Python 3.6+
- Discord server with webhook permissions

## Step 1: Create a Project Directory

```bash
mkdir -p ~/app/crypto_alert
cd ~/app/crypto_alert
```

## Step 2: Set Up a Python Virtual Environment

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

## Step 3: Install Required Dependencies

```bash
# Make sure you're in the activated virtual environment
pip install requests python-dotenv
```

## Step 4: Create the Discord Webhook

1. Open Discord and navigate to your server
2. Right-click on your server or desired channel → Server Settings → Integrations
3. Click "Webhooks" → "New Webhook"
4. Name your webhook (e.g., "Crypto Alert Bot") and choose an avatar if desired
5. Select the channel where you want to receive alerts
6. Click "Copy Webhook URL" - you'll need this in the next step

## Step 5: Create the .env File

Create a file named `.env` in your project directory:

```bash
echo "DISCORD_WEBHOOK_URL=your_discord_webhook_url_here" > .env
```

Replace `your_discord_webhook_url_here` with the webhook URL you copied from Discord.

## Step 6: Add the Python Script

Copy the entire Python script into a file named `crypto_alert.py` in your project directory.

## Step 7: Create the Wrapper Script

Create a file named `run_crypto_alert.sh` and copy the wrapper script into it. This script handles the virtual environment activation for cron.

## Step 8: Test the Scripts Manually

```bash
# Test the Python script directly (with venv activated)
source venv/bin/activate
python crypto_alert.py

# Test the wrapper script (from any environment)
./run_crypto_alert.sh
```

You should see log outputs, and if any cryptocurrency has already dropped below the thresholds, you'll receive a Discord notification.

## Step 9: Set Up the Cron Job

### Option 1: Using the automated setup script (Recommended)

1. Create a file named `setup_cron.sh` and copy the updated cron setup script into it
2. Make it executable: `chmod +x setup_cron.sh`
3. Run it: `./setup_cron.sh`

The script will:
- Check if your virtual environment exists
- Check if the Python script exists
- Make all scripts executable
- Set up the cron job to use the wrapper script
- Handle existing cron entries gracefully

### Option 2: Setting up manually

1. First make the wrapper script executable:
   ```bash
   chmod +x ~/crypto_alert/run_crypto_alert.sh
   ```

2. Open your crontab: `crontab -e`

3. Add the following line to run every 15 minutes:
   ```
   */15 * * * * ~/crypto_alert/run_crypto_alert.sh >> ~/crypto_alert/cron_execution.log 2>&1
   ```

4. Save and exit the editor

## Step 10: Verify the Setup

```bash
# Check your crontab
crontab -l

# Test the wrapper script manually
~/crypto_alert/run_crypto_alert.sh

# Monitor the logs
tail -f ~/crypto_alert/crypto_alert.log
```

## Project Structure

After setup, your project directory should look like this:

```
~/crypto_alert/
├── venv/                    # Virtual environment
├── crypto_alert.py         # Main Python script
├── run_crypto_alert.sh     # Wrapper script for cron
├── setup_cron.sh          # Setup script
├── .env                   # Environment variables
├── crypto_alert.log       # Application logs
└── cron_execution.log     # Cron execution logs
```

## Customizing the Alert Thresholds

To customize which price drop percentages trigger alerts, edit the `THRESHOLDS` list in the `crypto_alert.py` file:

```python
# Default is 30%, 40%, 50%, 60%, 70%
THRESHOLDS = [30, 40, 50, 60, 70]  # Modify these values as needed
```

## Adding More Cryptocurrencies

To monitor additional cryptocurrencies, edit the `CRYPTOCURRENCIES` list in the `crypto_alert.py` file:

```python
# Default is Bitcoin and Ethereum
CRYPTOCURRENCIES = ['bitcoin', 'ethereum', 'solana', 'cardano']  # Add more as needed
```

Make sure to use the ID as it appears in CoinGecko's API (usually the lowercase name with hyphens instead of spaces).

## Monitoring the Logs

You can check the script's logs in two files:

1. `crypto_alert.log` - Contains detailed script execution logs
2. `cron_execution.log` - Contains cron execution logs

```bash
tail -f ~/crypto_alert/crypto_alert.log
```

## Troubleshooting

If you're having issues:

1. **Discord alerts not working**: Double-check your webhook URL in the `.env` file
2. **Script not running**: Check cron execution logs with `tail -f ~/crypto_alert/cron_execution.log`
3. **API rate limiting**: The free CoinGecko API has rate limits. If you're getting errors, you might need to reduce frequency or implement rate limiting
4. **Permission issues**: Make sure your script is executable and that the cron user has access to the directory

## Notes on CoinGecko API Usage

The free CoinGecko API has rate limits. If you plan to run this script frequently or monitor many cryptocurrencies, consider:

1. Adding a delay between API calls
2. Implementing exponential backoff for retries
3. Using CoinGecko's Pro API if you need higher limits

## Security Notes

- Your Discord webhook URL should be kept private
- The `.env` file contains sensitive information, ensure it has appropriate permissions
- If you're using a shared system, consider using file permissions to restrict access to your script and credential files
