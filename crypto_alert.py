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
STATS_52W_FILE = "52w_stats.json"

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

def load_52w_stats():
    """Load 52w stats from JSON file"""
    try:
        with open(STATS_52W_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"52w stats file {STATS_52W_FILE} not found. Run update_52w_stats.py first.")
        return {"last_updated": None, "coins": {}}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing 52w stats: {e}")
        return {"last_updated": None, "coins": {}}

def validate_coins_config(config):
    """
    Validate coins configuration structure and content

    Returns:
        List of error messages (empty list if valid)
    """
    errors = []

    # Check if 'coins' key exists
    if 'coins' not in config:
        errors.append("Missing required key: 'coins'")
        return errors

    # Check if coins is a list
    if not isinstance(config['coins'], list):
        errors.append("'coins' must be a list")
        return errors

    # Validate each coin
    required_fields = ['id', 'name', 'symbol', 'ath_thresholds', 'price_alerts']

    for idx, coin in enumerate(config['coins']):
        coin_prefix = f"Coin {idx + 1}"

        # Check required fields
        for field in required_fields:
            if field not in coin:
                errors.append(f"{coin_prefix}: Missing required field '{field}'")

        # Validate field types
        if 'id' in coin:
            if not isinstance(coin['id'], str):
                errors.append(f"{coin_prefix}: 'id' must be a string")
            elif coin['id'] != coin['id'].lower():
                errors.append(f"{coin_prefix}: 'id' should be lowercase (CoinGecko format)")

        if 'name' in coin and not isinstance(coin['name'], str):
            errors.append(f"{coin_prefix}: 'name' must be a string")

        if 'symbol' in coin and not isinstance(coin['symbol'], str):
            errors.append(f"{coin_prefix}: 'symbol' must be a string")

        if 'ath_thresholds' in coin and not isinstance(coin['ath_thresholds'], list):
            errors.append(f"{coin_prefix}: 'ath_thresholds' must be a list")

        if 'price_alerts' in coin and not isinstance(coin['price_alerts'], list):
            errors.append(f"{coin_prefix}: 'price_alerts' must be a list")

    return errors

def validate_alert_config(config):
    """
    Validate alert configuration structure and types

    Returns:
        List of error messages (empty list if valid)
    """
    errors = []

    # Expected types for each field
    expected_types = {
        'reset_alerts_daily': bool,
        'check_interval_minutes': int,
        'max_alerts_per_run': int,
        'alert_tracking_file': str
    }

    for field, expected_type in expected_types.items():
        if field in config:
            if not isinstance(config[field], expected_type):
                errors.append(f"'{field}' must be of type {expected_type.__name__}, got {type(config[field]).__name__}")

    return errors

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
        "sparkline": "false",
        "price_change_percentage": "24h,7d"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching current prices: {str(e)}")
        return None

def get_ath_price(crypto_id, max_retries=3):
    """
    Fetch all-time high price for a specific cryptocurrency with retry logic
    """
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false"
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                retry_wait = (attempt + 1) * 5  # 5s, 10s, 15s
                logger.warning(f"Rate limit hit for {crypto_id} ATH, waiting {retry_wait}s before retry {attempt + 1}/{max_retries}")
                time.sleep(retry_wait)
                continue
            else:
                logger.error(f"HTTP error fetching ATH for {crypto_id}: {str(e)}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching ATH for {crypto_id}: {str(e)}")
            return None

    logger.error(f"Failed to fetch ATH for {crypto_id} after {max_retries} retries")
    return None

def check_alerts(dry_run=False):
    """
    Check for both ATH percentage drops and price alerts

    Args:
        dry_run: If True, alerts are found but not saved to tracking
    """
    # Load configurations
    coins_config = load_coins_config()
    alert_config = load_alert_config()

    if not coins_config:
        return []

    # Load alert tracking and 52w stats
    sent_alerts = load_sent_alerts(alert_config)
    stats_52w = load_52w_stats()

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

        # Get additional market data from API response
        price_change_24h = crypto.get('price_change_percentage_24h')
        price_change_7d = crypto.get('price_change_percentage_7d_in_currency')
        market_cap_rank = crypto.get('market_cap_rank')
        total_volume = crypto.get('total_volume')
        market_cap = crypto.get('market_cap')

        # Get 52w stats if available
        coin_52w_stats = stats_52w.get('coins', {}).get(crypto_id)
        high_52w = coin_52w_stats.get('high_52w') if coin_52w_stats else None
        low_52w = coin_52w_stats.get('low_52w') if coin_52w_stats else None

        # Calculate % from 52w high/low
        pct_from_52w_high = None
        pct_from_52w_low = None
        if high_52w and high_52w > 0:
            pct_from_52w_high = ((current_price - high_52w) / high_52w) * 100
        if low_52w and low_52w > 0:
            pct_from_52w_low = ((current_price - low_52w) / low_52w) * 100

        # Build common market data dict
        market_data = {
            "priceChange24h": round(price_change_24h, 2) if price_change_24h else None,
            "priceChange7d": round(price_change_7d, 2) if price_change_7d else None,
            "marketCapRank": market_cap_rank,
            "totalVolume": total_volume,
            "marketCap": market_cap,
            "high52w": high_52w,
            "low52w": low_52w,
            "pctFrom52wHigh": round(pct_from_52w_high, 2) if pct_from_52w_high else None,
            "pctFrom52wLow": round(pct_from_52w_low, 2) if pct_from_52w_low else None
        }

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

                        alert = {
                            "type": "ath",
                            "crypto": f"{crypto_name} ({crypto_symbol})",
                            "currentPrice": current_price,
                            "athPrice": ath_price,
                            "dropPercent": round(drop_percent, 2),
                            "threshold": threshold
                        }
                        alert.update(market_data)
                        alerts.append(alert)
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

                    alert = {
                        "type": "price",
                        "crypto": f"{crypto_name} ({crypto_symbol})",
                        "currentPrice": current_price,
                        "targetPrice": target_price,
                        "priceDiff": price_diff,
                        "priceDiffPercent": round(price_diff_percent, 2)
                    }
                    alert.update(market_data)
                    alerts.append(alert)
                    new_sent_alerts[alert_key] = True

    # Save updated alert tracking (skip in dry run)
    if not dry_run and new_sent_alerts != sent_alerts['sent_alerts']:
        sent_alerts['sent_alerts'] = new_sent_alerts
        save_sent_alerts(sent_alerts, alert_config)

    return alerts

def send_discord_alert(alerts, dry_run=False):
    """
    Send alerts to Discord using webhook with sections for different alert types

    Args:
        alerts: List of alert dictionaries
        dry_run: If True, alerts are logged but not sent to Discord
    """
    if not alerts:
        return

    if dry_run:
        logger.info(f"[DRY RUN] Would send {len(alerts)} alerts to Discord")
        for alert in alerts:
            logger.info(f"[DRY RUN] Alert: {alert}")
        return

    # Separate alerts by type
    ath_alerts = [alert for alert in alerts if alert['type'] == 'ath']
    price_alerts = [alert for alert in alerts if alert['type'] == 'price']

    # Build description with sections
    description_parts = []

    if ath_alerts:
        description_parts.append("## 🚨 ATH Drop Alerts")
        for alert in ath_alerts:
            # Build market metrics section
            metrics = []
            if alert.get('priceChange24h') is not None:
                emoji = "📈" if alert['priceChange24h'] > 0 else "📉"
                metrics.append(f"24h: {emoji} {alert['priceChange24h']:+.2f}%")
            if alert.get('priceChange7d') is not None:
                emoji = "📈" if alert['priceChange7d'] > 0 else "📉"
                metrics.append(f"7d: {emoji} {alert['priceChange7d']:+.2f}%")
            if alert.get('marketCapRank'):
                metrics.append(f"Rank: #{alert['marketCapRank']}")

            # 52w range info
            range_info = []
            if alert.get('pctFrom52wHigh') is not None:
                range_info.append(f"From 52w high: {alert['pctFrom52wHigh']:+.1f}%")
            if alert.get('pctFrom52wLow') is not None:
                range_info.append(f"From 52w low: {alert['pctFrom52wLow']:+.1f}%")

            metrics_text = " • ".join(metrics) if metrics else ""
            range_text = " • ".join(range_info) if range_info else ""

            description_parts.append(
                f"**{alert['crypto']}** dropped **{alert['dropPercent']}%** from ATH\n"
                f"├ Current: ${alert['currentPrice']:,.6f}\n"
                f"├ ATH: ${alert['athPrice']:,.6f}\n"
                f"├ Threshold: {alert['threshold']}%\n"
                + (f"├ {metrics_text}\n" if metrics_text else "")
                + (f"└ {range_text}\n" if range_text else "└\n")
            )

    if price_alerts:
        if description_parts:
            description_parts.append("")  # Empty line separator
        description_parts.append("## 💰 Price Alerts")
        for alert in price_alerts:
            # Build market metrics section
            metrics = []
            if alert.get('priceChange24h') is not None:
                emoji = "📈" if alert['priceChange24h'] > 0 else "📉"
                metrics.append(f"24h: {emoji} {alert['priceChange24h']:+.2f}%")
            if alert.get('priceChange7d') is not None:
                emoji = "📈" if alert['priceChange7d'] > 0 else "📉"
                metrics.append(f"7d: {emoji} {alert['priceChange7d']:+.2f}%")
            if alert.get('marketCapRank'):
                metrics.append(f"Rank: #{alert['marketCapRank']}")

            # 52w range info
            range_info = []
            if alert.get('pctFrom52wHigh') is not None:
                range_info.append(f"From 52w high: {alert['pctFrom52wHigh']:+.1f}%")
            if alert.get('pctFrom52wLow') is not None:
                range_info.append(f"From 52w low: {alert['pctFrom52wLow']:+.1f}%")

            metrics_text = " • ".join(metrics) if metrics else ""
            range_text = " • ".join(range_info) if range_info else ""

            description_parts.append(
                f"**{alert['crypto']}** fell below target price\n"
                f"├ Current: ${alert['currentPrice']:,.6f}\n"
                f"├ Target: ${alert['targetPrice']:,.6f}\n"
                f"├ Difference: ${alert['priceDiff']:,.6f} ({alert['priceDiffPercent']:+.2f}%)\n"
                + (f"├ {metrics_text}\n" if metrics_text else "")
                + (f"└ {range_text}\n" if range_text else "└\n")
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
    import sys

    # Check for command flags
    dry_run = '--dry-run' in sys.argv
    validate_only = '--validate' in sys.argv

    # Handle --validate flag
    if validate_only:
        logger.info("Validating configuration files...")

        coins_config = load_coins_config()
        alert_config = load_alert_config()

        all_valid = True

        # Validate coins config
        if coins_config:
            errors = validate_coins_config(coins_config)
            if errors:
                logger.error(f"❌ coins_config.json has {len(errors)} error(s):")
                for error in errors:
                    logger.error(f"  - {error}")
                all_valid = False
            else:
                logger.info("✅ coins_config.json is valid")
        else:
            logger.error("❌ Could not load coins_config.json")
            all_valid = False

        # Validate alert config
        if alert_config:
            errors = validate_alert_config(alert_config)
            if errors:
                logger.error(f"❌ alert_config.json has {len(errors)} error(s):")
                for error in errors:
                    logger.error(f"  - {error}")
                all_valid = False
            else:
                logger.info("✅ alert_config.json is valid")
        else:
            logger.error("❌ Could not load alert_config.json")
            all_valid = False

        if all_valid:
            logger.info("🎉 All configuration files are valid!")
            sys.exit(0)
        else:
            sys.exit(1)

    if dry_run:
        logger.info("Running in DRY RUN mode - no alerts will be sent or saved")
    else:
        logger.info("Running Crypto Alert check (ATH drops + Price alerts)")

    # Validate Discord webhook URL (not needed in dry run)
    if not dry_run and not DISCORD_WEBHOOK_URL:
        logger.error("Discord webhook URL not found. Please set the DISCORD_WEBHOOK_URL environment variable.")
        return

    try:
        # Check for alerts (both ATH and price)
        alerts = check_alerts(dry_run=dry_run)

        if alerts:
            ath_count = len([a for a in alerts if a['type'] == 'ath'])
            price_count = len([a for a in alerts if a['type'] == 'price'])
            logger.info(f"Found {len(alerts)} alerts ({ath_count} ATH, {price_count} price){' [DRY RUN]' if dry_run else '. Sending to Discord...'}")
            send_discord_alert(alerts, dry_run=dry_run)
        else:
            logger.info(f"No alerts triggered at this time{' [DRY RUN]' if dry_run else '.'}")

    except Exception as e:
        logger.error(f"Error in alert system: {str(e)}")

if __name__ == "__main__":
    main()