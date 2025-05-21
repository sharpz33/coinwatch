import requests
import json
from datetime import datetime
import os
import logging
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

# Configuration
CRYPTOCURRENCIES = ['bitcoin', 'ethereum']  # Add more if needed
THRESHOLDS = [30, 40, 50, 60, 70]  # Percentage drops to monitor

def get_current_prices():
    """
    Fetch current prices for specified cryptocurrencies
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(CRYPTOCURRENCIES),
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

def calculate_price_drops():
    """
    Calculate percentage drops from ATH for all cryptocurrencies
    """
    current_data = get_current_prices()
    if not current_data:
        return []
    
    alerts = []
    
    for crypto in current_data:
        crypto_id = crypto['id']
        current_price = crypto['current_price']
        
        # Get ATH data
        ath_data = get_ath_price(crypto_id)
        if not ath_data:
            continue
            
        ath_price = ath_data['market_data']['ath']['usd']
        
        # Calculate percentage drop from ATH
        drop_percent = ((ath_price - current_price) / ath_price) * 100
        
        logger.info(f"{crypto['name']} ({crypto['symbol'].upper()}) - Current: ${current_price:.2f}, ATH: ${ath_price:.2f}, Drop: {drop_percent:.2f}%")
        
        # Check against thresholds
        for threshold in THRESHOLDS:
            if drop_percent >= threshold and drop_percent < (threshold + 10):
                crypto_name = crypto['name']
                crypto_symbol = crypto['symbol'].upper()
                
                alerts.append({
                    "crypto": f"{crypto_name} ({crypto_symbol})",
                    "currentPrice": current_price,
                    "athPrice": ath_price,
                    "dropPercent": round(drop_percent, 2),
                    "threshold": threshold
                })
    
    return alerts

def send_discord_alert(alerts):
    """
    Send alerts to Discord using webhook
    """
    if not alerts:
        return
        
    embeds = []
    
    for alert in alerts:
        embed = {
            "title": f"🚨 {alert['crypto']} Price Alert!",
            "color": 16711680,  # Red color
            "description": (
                f"**{alert['crypto']}** has dropped **{alert['dropPercent']}%** from its all-time high.\n\n"
                f"Current price: ${alert['currentPrice']:,.2f}\n"
                f"ATH price: ${alert['athPrice']:,.2f}\n"
                f"Threshold reached: {alert['threshold']}%"
            ),
            "footer": {
                "text": f"Crypto Alert Bot • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        embeds.append(embed)
    
    payload = {
        "embeds": embeds
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, headers=headers)
        response.raise_for_status()
        logger.info(f"Successfully sent {len(alerts)} alerts to Discord")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending alerts to Discord: {str(e)}")


def main():
    """
    Main function to run the alert check once
    """
    logger.info("Running Crypto Price Drop Alert check")
    
    # Validate Discord webhook URL
    if not DISCORD_WEBHOOK_URL:
        logger.error("Discord webhook URL not found. Please set the DISCORD_WEBHOOK_URL environment variable.")
        return
    
    try:
        # Calculate price drops and get alerts
        alerts = calculate_price_drops()
        
        if alerts:
            logger.info(f"Found {len(alerts)} alerts. Sending to Discord...")
            send_discord_alert(alerts)
        else:
            logger.info("No alerts triggered at this time.")
            
    except Exception as e:
        logger.error(f"Error in alert system: {str(e)}")

if __name__ == "__main__":
    main()