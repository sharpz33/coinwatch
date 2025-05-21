# Cryptocurrency ATH Drop Alert System - Installation Guide

This guide will help you set up a cron-based system to monitor Bitcoin and Ethereum price drops from their All-Time Highs (ATH) and send alerts to Discord when specific thresholds are crossed.

## Prerequisites

- Linux/Unix-based system (for cron)
- Python 3.6+
- Discord server with webhook permissions

## Step 1: Create a Project Directory

```bash
mkdir -p ~/crypto_alert
cd ~/crypto_alert
```

## Step 2: Set Up a Python Virtual Environment (Optional but Recommended)

```bash
# Install virtualenv if you don't have it
pip install virtualenv

# Create and activate a virtual environment
virtualenv venv
source venv/bin/activate
```

## Step 3: Install Required Dependencies

```bash
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

## Step 7: Make the Script Executable

```bash
chmod +x crypto_alert.py
```

## Step 8: Test the Script Manually

```bash
python crypto_alert.py
```

You should see log outputs, and if any cryptocurrency has already dropped below the thresholds, you'll receive a Discord notification.

## Step 9: Set Up the Cron Job

There are two ways to set up the cron job:

### Option 1: Using the setup script

1. Create a file named `setup_cron.sh` and copy the setup script into it
2. Make it executable: `chmod +x setup_cron.sh`
3. Run it: `./setup_cron.sh`

### Option 2: Setting up manually

1. Open your crontab: `crontab -e`
2. Add the following line to run every 15 minutes:
   ```
   */15 * * * * cd ~/crypto_alert && /usr/bin/python3 ~/crypto_alert/crypto_alert.py >> ~/crypto_alert/cron_execution.log 2>&1
   ```
3. Save and exit the editor

## Step 10: Verify the Cron Job

```bash
crontab -l
```

You should see your new cron entry listed.

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