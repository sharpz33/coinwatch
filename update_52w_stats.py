import requests
import json
import time
import logging
from datetime import date, datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("update_52w_stats.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
COINS_CONFIG_FILE = "coins_config.json"
STATS_FILE = "52w_stats.json"
RATE_LIMIT_SLEEP = 3.0  # seconds between API calls (increased for free tier limits)


def load_coins_config():
    """Load coins configuration from JSON file"""
    try:
        with open(COINS_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"❌ Configuration file '{COINS_CONFIG_FILE}' not found")
        logger.error(f"💡 Please ensure {COINS_CONFIG_FILE} exists in the current directory")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON syntax in '{COINS_CONFIG_FILE}'")
        logger.error(f"💡 Error at line {e.lineno}, column {e.colno}: {e.msg}")
        logger.error(f"💡 Check for missing commas, quotes, or brackets")
        return None


def load_52w_stats(filename=STATS_FILE):
    """Load 52w stats from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info(f"Stats file {filename} not found, will create new one")
        return {"last_updated": None, "coins": {}}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing stats file: {e}")
        return {"last_updated": None, "coins": {}}


def save_52w_stats(stats_data, filename=STATS_FILE):
    """Save 52w stats to JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(stats_data, f, indent=2)
        logger.info(f"✅ Saved stats to {filename}")
    except PermissionError:
        logger.error(f"❌ Permission denied writing to '{filename}'")
        logger.error(f"💡 Check file permissions or run with appropriate access")
    except IOError as e:
        logger.error(f"❌ Failed to save stats to '{filename}': {e}")
        logger.error(f"💡 Check disk space and file system permissions")


def fetch_52w_high_low(crypto_id, max_retries=3):
    """
    Fetch 52-week high and low for a cryptocurrency with retry logic
    Returns dict with high_52w and low_52w, or None on error
    """
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": "365"
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "prices" not in data or len(data["prices"]) == 0:
                logger.warning(f"⚠️  No price data returned for {crypto_id}")
                return None

            # Extract prices from [timestamp, price] pairs
            prices = [price[1] for price in data["prices"]]

            result = {
                "high_52w": max(prices),
                "low_52w": min(prices)
            }

            logger.info(f"{crypto_id}: 52w high=${result['high_52w']:,.2f}, low=${result['low_52w']:,.2f}")
            return result

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                retry_wait = (attempt + 1) * 10
                logger.warning(f"⚠️  Timeout fetching {crypto_id}, retrying in {retry_wait}s ({attempt + 1}/{max_retries})")
                time.sleep(retry_wait)
                continue
            else:
                logger.error(f"❌ Timeout fetching 52w data for {crypto_id} after {max_retries} attempts")
                return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                retry_wait = (attempt + 1) * 10  # 10s, 20s, 30s
                logger.warning(f"⚠️  Rate limit hit for {crypto_id}, waiting {retry_wait}s before retry ({attempt + 1}/{max_retries})")
                time.sleep(retry_wait)
                continue
            elif e.response.status_code >= 500:
                logger.error(f"❌ CoinGecko API server error ({e.response.status_code}) for {crypto_id}")
                logger.error(f"💡 CoinGecko service may be down, try again later")
                return None
            else:
                logger.error(f"❌ HTTP {e.response.status_code} error fetching 52w data for {crypto_id}")
                return None
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Network connection error fetching {crypto_id}")
            logger.error(f"💡 Check your internet connection")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching 52w data for {crypto_id}: {str(e)}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"❌ Error parsing 52w data for {crypto_id}: {str(e)}")
            logger.error(f"💡 API response format may have changed")
            return None

    logger.error(f"❌ Failed to fetch {crypto_id} after {max_retries} retries")
    return None


def is_stats_stale(last_updated_str, max_age_days=7):
    """
    Check if stats are older than max_age_days
    Returns True if stale, False if fresh
    """
    if last_updated_str is None:
        return True

    try:
        last_updated = datetime.strptime(last_updated_str, "%Y-%m-%d").date()
        age = date.today() - last_updated
        return age.days > max_age_days
    except (ValueError, TypeError):
        logger.warning(f"Invalid date format: {last_updated_str}")
        return True


def get_coin_52w_stats(crypto_id, stats_data):
    """
    Get 52w stats for a specific coin from stats data
    Returns dict with high_52w and low_52w, or None if not found
    """
    if "coins" not in stats_data:
        return None

    return stats_data["coins"].get(crypto_id)


def update_all_52w_stats():
    """
    Main function to update 52w stats for all coins
    """
    logger.info("🔄 Starting 52w stats update")

    # Load coins config
    coins_config = load_coins_config()
    if not coins_config:
        logger.error("❌ Could not load coins config, aborting update")
        return

    # Prepare new stats data
    stats_data = {
        "last_updated": str(date.today()),
        "coins": {}
    }

    # Fetch 52w data for each coin
    coin_ids = [coin['id'] for coin in coins_config['coins']]
    total_coins = len(coin_ids)
    failed_coins = []

    for idx, coin_id in enumerate(coin_ids, 1):
        logger.info(f"Updating {coin_id} ({idx}/{total_coins})")

        result = fetch_52w_high_low(coin_id)

        if result:
            stats_data["coins"][coin_id] = {
                "high_52w": result["high_52w"],
                "low_52w": result["low_52w"],
                "updated_at": str(date.today())
            }
        else:
            logger.warning(f"Failed to fetch 52w data for {coin_id}, will retry later")
            failed_coins.append(coin_id)

        # Rate limiting - don't sleep after last request
        if idx < total_coins:
            logger.debug(f"Sleeping {RATE_LIMIT_SLEEP}s for rate limiting")
            time.sleep(RATE_LIMIT_SLEEP)

    # Retry failed coins after a longer wait
    if failed_coins:
        logger.info(f"Retrying {len(failed_coins)} failed coins after 60s cooldown")
        time.sleep(60)

        for idx, coin_id in enumerate(failed_coins, 1):
            logger.info(f"Retry: Updating {coin_id} ({idx}/{len(failed_coins)})")
            result = fetch_52w_high_low(coin_id, max_retries=2)

            if result:
                stats_data["coins"][coin_id] = {
                    "high_52w": result["high_52w"],
                    "low_52w": result["low_52w"],
                    "updated_at": str(date.today())
                }
                logger.info(f"Successfully fetched {coin_id} on retry")
            else:
                logger.error(f"Failed to fetch {coin_id} even after retry")

            # Rate limiting between retries
            if idx < len(failed_coins):
                time.sleep(RATE_LIMIT_SLEEP)

    # Save results
    if stats_data["coins"]:
        save_52w_stats(stats_data)
        logger.info(f"✅ Successfully updated stats for {len(stats_data['coins'])} coins")
    else:
        logger.error("❌ No stats were successfully fetched, not saving")
        logger.error("💡 Check your internet connection and CoinGecko API status")


def main():
    """Entry point for the script"""
    try:
        update_all_52w_stats()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Update interrupted by user")
    except KeyError as e:
        logger.error(f"❌ Configuration error: Missing required field {e}")
        logger.error(f"💡 Check your coins_config.json structure")
        import sys
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error during 52w stats update")
        logger.error(f"💡 Error details: {str(e)}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
