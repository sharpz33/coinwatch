import requests
import json
from datetime import datetime, date
import os
import logging
import time
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crypto_alert.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Get Discord webhook URL from environment variables
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# Configuration files
COINS_CONFIG_FILE = "coins_config.json"
ALERT_CONFIG_FILE = "alert_config.json"

def load_coins_config():
    """Load coins configuration from JSON file"""
    try:
        with open(COINS_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Coins config file {COINS_CONFIG_FILE} not found")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing coins config: {e}")
        return None

def load_alert_config():
    """Load alert configuration from JSON file"""
    try:
        with open(ALERT_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Alert config file {ALERT_CONFIG_FILE} not found")
        return {"reset_alerts_daily": True, "alert_tracking_file": "sent_alerts.json"}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing alert config: {e}")
        return {"reset_alerts_daily": True, "alert_tracking_file": "sent_alerts.json"}

def load_sent_alerts(alert_config):
    """Load tracking of sent alerts"""
    tracking_file = alert_config.get("alert_tracking_file", "sent_alerts.json")
    today = str(date.today())

    try:
        with open(tracking_file, 'r') as f:
            data = json.load(f)
            if data.get("date") != today and alert_config.get("reset_alerts_daily", True):
                # Reset alerts for new day
                return {"date": today, "sent_alerts": {}}
            return data
    except FileNotFoundError:
        return {"date": today, "sent_alerts": {}}
    except json.JSONDecodeError:
        return {"date": today, "sent_alerts": {}}

def save_sent_alerts(alert_data, alert_config):
    """Save tracking of sent alerts"""
    tracking_file = alert_config.get("alert_tracking_file", "sent_alerts.json")
    try:
        with open(tracking_file, 'w') as f:
            json.dump(alert_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving alert tracking: {e}")

def get_current_prices(coin_ids):
    """
    Fetch current prices for specified cryptocurrencies
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(coin_ids),
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching current prices: {str(e)}")
        return None

def get_ath_price(crypto_id):
    """
    Fetch all-time high price for a specific cryptocurrency
    """
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching ATH for {crypto_id}: {str(e)}")
        return None

def check_alerts():
    """
    Check for both ATH percentage drops and price alerts
    """
    # Load configurations
    coins_config = load_coins_config()
    alert_config = load_alert_config()

    if not coins_config:
        return []

    # Load alert tracking
    sent_alerts = load_sent_alerts(alert_config)

    # Get coin IDs for API call
    coin_ids = [coin['id'] for coin in coins_config['coins']]

    # Get current prices
    current_data = get_current_prices(coin_ids)
    if not current_data:
        return []

    # Create lookup for coin configs
    coin_lookup = {coin['id']: coin for coin in coins_config['coins']}

    alerts = []
    new_sent_alerts = sent_alerts['sent_alerts'].copy()

    for crypto in current_data:
        crypto_id = crypto['id']
        current_price = crypto['current_price']
        coin_config = coin_lookup.get(crypto_id)

        if not coin_config:
            continue

        crypto_name = coin_config['name']
        crypto_symbol = coin_config['symbol']

        logger.info(f"{crypto_name} ({crypto_symbol}) - Current: ${current_price:.6f}")

        # Check ATH alerts
        if coin_config['ath_thresholds']:
            ath_data = get_ath_price(crypto_id)
            if ath_data:
                ath_price = ath_data['market_data']['ath']['usd']
                drop_percent = ((ath_price - current_price) / ath_price) * 100

                logger.info(f"  ATH: ${ath_price:.6f}, Drop: {drop_percent:.2f}%")

                for threshold in coin_config['ath_thresholds']:
                    alert_key = f"{crypto_id}_ath_{threshold}"
                    if (drop_percent >= threshold and
                        drop_percent < (threshold + 10) and
                        alert_key not in sent_alerts['sent_alerts']):

                        alerts.append({
                            "type": "ath",
                            "crypto": f"{crypto_name} ({crypto_symbol})",
                            "currentPrice": current_price,
                            "athPrice": ath_price,
                            "dropPercent": round(drop_percent, 2),
                            "threshold": threshold
                        })
                        new_sent_alerts[alert_key] = True

            # Rate limiting - wait between API calls
            time.sleep(0.5)

        # Check price alerts
        if coin_config['price_alerts']:
            for target_price in coin_config['price_alerts']:
                alert_key = f"{crypto_id}_price_{target_price}"
                if (current_price <= target_price and
                    alert_key not in sent_alerts['sent_alerts']):

                    price_diff = current_price - target_price
                    price_diff_percent = (price_diff / target_price) * 100 if target_price > 0 else 0

                    alerts.append({
                        "type": "price",
                        "crypto": f"{crypto_name} ({crypto_symbol})",
                        "currentPrice": current_price,
                        "targetPrice": target_price,
                        "priceDiff": price_diff,
                        "priceDiffPercent": round(price_diff_percent, 2)
                    })
                    new_sent_alerts[alert_key] = True

    # Save updated alert tracking
    if new_sent_alerts != sent_alerts['sent_alerts']:
        sent_alerts['sent_alerts'] = new_sent_alerts
        save_sent_alerts(sent_alerts, alert_config)

    return alerts

def send_discord_alert(alerts):
    """
    Send alerts to Discord using webhook with sections for different alert types
    """
    if not alerts:
        return

    # Separate alerts by type
    ath_alerts = [alert for alert in alerts if alert['type'] == 'ath']
    price_alerts = [alert for alert in alerts if alert['type'] == 'price']

    # Build description with sections
    description_parts = []

    if ath_alerts:
        description_parts.append("## 🚨 ATH Drop Alerts")
        for alert in ath_alerts:
            description_parts.append(
                f"**{alert['crypto']}** dropped **{alert['dropPercent']}%** from ATH\n"
                f"├ Current: ${alert['currentPrice']:,.6f}\n"
                f"├ ATH: ${alert['athPrice']:,.6f}\n"
                f"└ Threshold: {alert['threshold']}%\n"
            )

    if price_alerts:
        if description_parts:
            description_parts.append("")  # Empty line separator
        description_parts.append("## 💰 Price Alerts")
        for alert in price_alerts:
            description_parts.append(
                f"**{alert['crypto']}** fell below target price\n"
                f"├ Current: ${alert['currentPrice']:,.6f}\n"
                f"├ Target: ${alert['targetPrice']:,.6f}\n"
                f"└ Difference: ${alert['priceDiff']:,.6f} ({alert['priceDiffPercent']:+.2f}%)\n"
            )

    # Choose color based on alert types
    color = 16711680  # Red for ATH alerts
    if price_alerts and not ath_alerts:
        color = 16753920  # Orange for price alerts

    embed = {
        "title": f"📢 Crypto Alerts ({len(alerts)} total)",
        "color": color,
        "description": "\n".join(description_parts),
        "footer": {
            "text": f"Crypto Alert Bot • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
    }

    payload = {
        "embeds": [embed]
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Successfully sent {len(alerts)} alerts to Discord ({len(ath_alerts)} ATH, {len(price_alerts)} price)")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending alerts to Discord: {str(e)}")


def main():
    """
    Main function to run the alert check once
    """
    logger.info("Running Crypto Alert check (ATH drops + Price alerts)")

    # Validate Discord webhook URL
    if not DISCORD_WEBHOOK_URL:
        logger.error("Discord webhook URL not found. Please set the DISCORD_WEBHOOK_URL environment variable.")
        return

    try:
        # Check for alerts (both ATH and price)
        alerts = check_alerts()

        if alerts:
            ath_count = len([a for a in alerts if a['type'] == 'ath'])
            price_count = len([a for a in alerts if a['type'] == 'price'])
            logger.info(f"Found {len(alerts)} alerts ({ath_count} ATH, {price_count} price). Sending to Discord...")
            send_discord_alert(alerts)
        else:
            logger.info("No alerts triggered at this time.")

    except Exception as e:
        logger.error(f"Error in alert system: {str(e)}")

if __name__ == "__main__":
    main()