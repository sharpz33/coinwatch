import pytest
import json
import os
from datetime import date
from unittest.mock import patch, mock_open, MagicMock
import crypto_alert


@pytest.fixture
def sample_coins_config():
    """Sample coins configuration for testing"""
    return {
        "coins": [
            {
                "id": "bitcoin",
                "name": "Bitcoin",
                "symbol": "BTC",
                "ath_thresholds": [30, 40, 50],
                "price_alerts": [80000, 70000]
            },
            {
                "id": "ethereum",
                "name": "Ethereum",
                "symbol": "ETH",
                "ath_thresholds": [40, 50],
                "price_alerts": [2500, 2000]
            }
        ]
    }


@pytest.fixture
def sample_alert_config():
    """Sample alert configuration for testing"""
    return {
        "reset_alerts_daily": True,
        "check_interval_minutes": 15,
        "max_alerts_per_run": 20,
        "alert_tracking_file": "sent_alerts.json"
    }


@pytest.fixture
def sample_sent_alerts():
    """Sample sent alerts tracking data"""
    return {
        "date": str(date.today()),
        "sent_alerts": {
            "bitcoin_ath_30": True,
            "ethereum_price_2500": True
        }
    }


class TestConfigLoading:
    """Test configuration loading functions"""

    def test_load_coins_config_success(self, sample_coins_config):
        """Test successful loading of coins config"""
        mock_file_content = json.dumps(sample_coins_config)
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            result = crypto_alert.load_coins_config()
            assert result == sample_coins_config
            assert len(result["coins"]) == 2

    def test_load_coins_config_file_not_found(self):
        """Test handling of missing coins config file"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = crypto_alert.load_coins_config()
            assert result is None

    def test_load_coins_config_invalid_json(self):
        """Test handling of invalid JSON in coins config"""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            result = crypto_alert.load_coins_config()
            assert result is None

    def test_load_alert_config_success(self, sample_alert_config):
        """Test successful loading of alert config"""
        mock_file_content = json.dumps(sample_alert_config)
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            result = crypto_alert.load_alert_config()
            assert result == sample_alert_config
            assert result["reset_alerts_daily"] is True

    def test_load_alert_config_file_not_found(self):
        """Test default config when file not found"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = crypto_alert.load_alert_config()
            assert result["reset_alerts_daily"] is True
            assert result["alert_tracking_file"] == "sent_alerts.json"


class TestAlertTracking:
    """Test alert tracking functions"""

    def test_load_sent_alerts_same_day(self, sample_alert_config, sample_sent_alerts):
        """Test loading sent alerts for the same day"""
        mock_file_content = json.dumps(sample_sent_alerts)
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            result = crypto_alert.load_sent_alerts(sample_alert_config)
            assert result["date"] == str(date.today())
            assert "bitcoin_ath_30" in result["sent_alerts"]

    def test_load_sent_alerts_new_day(self, sample_alert_config):
        """Test alert reset on new day"""
        old_alerts = {
            "date": "2024-01-01",
            "sent_alerts": {
                "bitcoin_ath_30": True
            }
        }
        mock_file_content = json.dumps(old_alerts)
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            result = crypto_alert.load_sent_alerts(sample_alert_config)
            assert result["date"] == str(date.today())
            assert result["sent_alerts"] == {}

    def test_load_sent_alerts_file_not_found(self, sample_alert_config):
        """Test creating new tracking when file doesn't exist"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = crypto_alert.load_sent_alerts(sample_alert_config)
            assert result["date"] == str(date.today())
            assert result["sent_alerts"] == {}

    def test_save_sent_alerts(self, sample_alert_config, sample_sent_alerts):
        """Test saving alert tracking data"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            crypto_alert.save_sent_alerts(sample_sent_alerts, sample_alert_config)
            mock_file.assert_called_once_with("sent_alerts.json", 'w')
            handle = mock_file()
            written_data = "".join(call.args[0] for call in handle.write.call_args_list)
            assert "bitcoin_ath_30" in written_data


class TestAPIFunctions:
    """Test API interaction functions"""

    def test_get_current_prices_success(self):
        """Test successful API call for current prices"""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "bitcoin",
                "current_price": 65000,
                "name": "Bitcoin"
            }
        ]
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = crypto_alert.get_current_prices(["bitcoin"])
            assert len(result) == 1
            assert result[0]["id"] == "bitcoin"
            assert result[0]["current_price"] == 65000

    def test_get_current_prices_api_error(self):
        """Test handling of API errors"""
        import requests
        with patch("requests.get", side_effect=requests.exceptions.RequestException("API Error")):
            result = crypto_alert.get_current_prices(["bitcoin"])
            assert result is None

    def test_get_ath_price_success(self):
        """Test successful ATH price fetch"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "bitcoin",
            "market_data": {
                "ath": {
                    "usd": 69000
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = crypto_alert.get_ath_price("bitcoin")
            assert result["market_data"]["ath"]["usd"] == 69000


class TestAlertLogic:
    """Test alert triggering logic"""

    def test_ath_drop_calculation(self):
        """Test ATH drop percentage calculation"""
        ath_price = 69000
        current_price = 48300  # 30% drop
        drop_percent = ((ath_price - current_price) / ath_price) * 100
        assert abs(drop_percent - 30.0) < 0.01

    def test_ath_alert_triggers_correctly(self, sample_coins_config, sample_alert_config):
        """Test that ATH alert triggers at correct threshold"""
        # Mock API responses
        current_prices = [
            {
                "id": "bitcoin",
                "current_price": 48300  # 30% drop from 69000
            }
        ]

        ath_data = {
            "market_data": {
                "ath": {
                    "usd": 69000
                }
            }
        }

        sent_alerts_data = {
            "date": str(date.today()),
            "sent_alerts": {}
        }

        with patch("crypto_alert.load_coins_config", return_value=sample_coins_config), \
             patch("crypto_alert.load_alert_config", return_value=sample_alert_config), \
             patch("crypto_alert.load_sent_alerts", return_value=sent_alerts_data), \
             patch("crypto_alert.save_sent_alerts"), \
             patch("crypto_alert.get_current_prices", return_value=current_prices), \
             patch("crypto_alert.get_ath_price", return_value=ath_data), \
             patch("time.sleep"):

            alerts = crypto_alert.check_alerts()

            # Should trigger 30% threshold alert
            ath_alerts = [a for a in alerts if a["type"] == "ath"]
            assert len(ath_alerts) == 1
            assert ath_alerts[0]["threshold"] == 30
            assert abs(ath_alerts[0]["dropPercent"] - 30.0) < 0.1

    def test_price_alert_triggers_correctly(self, sample_coins_config, sample_alert_config):
        """Test that price alert triggers when price drops below target"""
        current_prices = [
            {
                "id": "bitcoin",
                "current_price": 69000  # Below 70000 threshold
            }
        ]

        sent_alerts_data = {
            "date": str(date.today()),
            "sent_alerts": {}
        }

        with patch("crypto_alert.load_coins_config", return_value=sample_coins_config), \
             patch("crypto_alert.load_alert_config", return_value=sample_alert_config), \
             patch("crypto_alert.load_sent_alerts", return_value=sent_alerts_data), \
             patch("crypto_alert.save_sent_alerts"), \
             patch("crypto_alert.get_current_prices", return_value=current_prices), \
             patch("crypto_alert.get_ath_price", return_value=None), \
             patch("time.sleep"):

            alerts = crypto_alert.check_alerts()

            # Should trigger 70000 price alert
            price_alerts = [a for a in alerts if a["type"] == "price"]
            assert len(price_alerts) >= 1
            assert any(a["targetPrice"] == 70000 for a in price_alerts)

    def test_alert_not_sent_twice(self, sample_coins_config, sample_alert_config):
        """Test that alerts are not sent twice for the same condition"""
        current_prices = [
            {
                "id": "bitcoin",
                "current_price": 69000
            }
        ]

        sent_alerts_data = {
            "date": str(date.today()),
            "sent_alerts": {
                "bitcoin_price_70000": True  # Already sent
            }
        }

        with patch("crypto_alert.load_coins_config", return_value=sample_coins_config), \
             patch("crypto_alert.load_alert_config", return_value=sample_alert_config), \
             patch("crypto_alert.load_sent_alerts", return_value=sent_alerts_data), \
             patch("crypto_alert.save_sent_alerts"), \
             patch("crypto_alert.get_current_prices", return_value=current_prices), \
             patch("crypto_alert.get_ath_price", return_value=None), \
             patch("time.sleep"):

            alerts = crypto_alert.check_alerts()

            # Should not trigger 70000 alert again
            price_alerts_70k = [a for a in alerts if a.get("targetPrice") == 70000]
            assert len(price_alerts_70k) == 0


class TestDryRunMode:
    """Test dry run mode functionality"""

    def test_dry_run_does_not_send_to_discord(self):
        """Test that dry run mode doesn't send to Discord"""
        alerts = [
            {
                "type": "ath",
                "crypto": "Bitcoin (BTC)",
                "currentPrice": 48300,
                "athPrice": 69000,
                "dropPercent": 30.0,
                "threshold": 30
            }
        ]

        with patch("requests.post") as mock_post:
            crypto_alert.send_discord_alert(alerts, dry_run=True)
            # Discord webhook should NOT be called in dry run
            assert not mock_post.called

    def test_dry_run_does_not_save_sent_alerts(self):
        """Test that dry run doesn't save alert tracking"""
        sample_coins_config = {
            "coins": [
                {
                    "id": "bitcoin",
                    "name": "Bitcoin",
                    "symbol": "BTC",
                    "ath_thresholds": [30],
                    "price_alerts": []
                }
            ]
        }

        current_prices = [{"id": "bitcoin", "current_price": 48300}]
        ath_data = {"market_data": {"ath": {"usd": 69000}}}
        sent_alerts_data = {"date": str(date.today()), "sent_alerts": {}}
        alert_config = {"reset_alerts_daily": True}

        with patch("crypto_alert.load_coins_config", return_value=sample_coins_config), \
             patch("crypto_alert.load_alert_config", return_value=alert_config), \
             patch("crypto_alert.load_sent_alerts", return_value=sent_alerts_data), \
             patch("crypto_alert.load_52w_stats", return_value={"coins": {}}), \
             patch("crypto_alert.save_sent_alerts") as mock_save, \
             patch("crypto_alert.get_current_prices", return_value=current_prices), \
             patch("crypto_alert.get_ath_price", return_value=ath_data), \
             patch("time.sleep"):

            alerts = crypto_alert.check_alerts(dry_run=True)

            # Should find alerts but NOT save them
            assert len(alerts) > 0
            assert not mock_save.called

    def test_dry_run_returns_alerts(self):
        """Test that dry run still returns alerts for inspection"""
        sample_coins_config = {
            "coins": [
                {
                    "id": "bitcoin",
                    "name": "Bitcoin",
                    "symbol": "BTC",
                    "ath_thresholds": [30],
                    "price_alerts": []
                }
            ]
        }

        current_prices = [{"id": "bitcoin", "current_price": 48300}]
        ath_data = {"market_data": {"ath": {"usd": 69000}}}
        sent_alerts_data = {"date": str(date.today()), "sent_alerts": {}}
        alert_config = {"reset_alerts_daily": True}

        with patch("crypto_alert.load_coins_config", return_value=sample_coins_config), \
             patch("crypto_alert.load_alert_config", return_value=alert_config), \
             patch("crypto_alert.load_sent_alerts", return_value=sent_alerts_data), \
             patch("crypto_alert.load_52w_stats", return_value={"coins": {}}), \
             patch("crypto_alert.save_sent_alerts"), \
             patch("crypto_alert.get_current_prices", return_value=current_prices), \
             patch("crypto_alert.get_ath_price", return_value=ath_data), \
             patch("time.sleep"):

            alerts = crypto_alert.check_alerts(dry_run=True)

            # Should return alerts even in dry run
            assert len(alerts) == 1
            assert alerts[0]["type"] == "ath"
            assert alerts[0]["crypto"] == "Bitcoin (BTC)"


class TestConfigValidator:
    """Test configuration validation"""

    def test_validate_valid_coins_config(self):
        """Test validation of valid coins config"""
        valid_config = {
            "coins": [
                {
                    "id": "bitcoin",
                    "name": "Bitcoin",
                    "symbol": "BTC",
                    "ath_thresholds": [30, 40, 50],
                    "price_alerts": [80000, 70000]
                }
            ]
        }
        errors = crypto_alert.validate_coins_config(valid_config)
        assert len(errors) == 0

    def test_validate_missing_coins_key(self):
        """Test validation fails when 'coins' key is missing"""
        invalid_config = {"data": []}
        errors = crypto_alert.validate_coins_config(invalid_config)
        assert len(errors) > 0
        assert any("coins" in err.lower() for err in errors)

    def test_validate_coins_not_list(self):
        """Test validation fails when coins is not a list"""
        invalid_config = {"coins": "not a list"}
        errors = crypto_alert.validate_coins_config(invalid_config)
        assert len(errors) > 0
        assert any("list" in err.lower() for err in errors)

    def test_validate_coin_missing_required_fields(self):
        """Test validation fails when coin is missing required fields"""
        invalid_config = {
            "coins": [
                {
                    "id": "bitcoin",
                    # Missing name, symbol
                    "ath_thresholds": [30],
                    "price_alerts": []
                }
            ]
        }
        errors = crypto_alert.validate_coins_config(invalid_config)
        assert len(errors) > 0
        assert any("name" in err.lower() for err in errors)
        assert any("symbol" in err.lower() for err in errors)

    def test_validate_invalid_threshold_types(self):
        """Test validation fails for invalid threshold types"""
        invalid_config = {
            "coins": [
                {
                    "id": "bitcoin",
                    "name": "Bitcoin",
                    "symbol": "BTC",
                    "ath_thresholds": "not a list",
                    "price_alerts": [80000]
                }
            ]
        }
        errors = crypto_alert.validate_coins_config(invalid_config)
        assert len(errors) > 0
        assert any("ath_thresholds" in err.lower() for err in errors)

    def test_validate_valid_alert_config(self):
        """Test validation of valid alert config"""
        valid_config = {
            "reset_alerts_daily": True,
            "check_interval_minutes": 360,
            "max_alerts_per_run": 20,
            "alert_tracking_file": "sent_alerts.json"
        }
        errors = crypto_alert.validate_alert_config(valid_config)
        assert len(errors) == 0

    def test_validate_alert_config_invalid_types(self):
        """Test validation fails for invalid types in alert config"""
        invalid_config = {
            "reset_alerts_daily": "yes",  # Should be bool
            "check_interval_minutes": "360",  # Should be int
            "max_alerts_per_run": 20.5,  # Should be int
        }
        errors = crypto_alert.validate_alert_config(invalid_config)
        assert len(errors) > 0

    def test_validate_coin_id_format(self):
        """Test validation of CoinGecko ID format"""
        invalid_config = {
            "coins": [
                {
                    "id": "Bitcoin",  # Should be lowercase
                    "name": "Bitcoin",
                    "symbol": "BTC",
                    "ath_thresholds": [],
                    "price_alerts": []
                }
            ]
        }
        errors = crypto_alert.validate_coins_config(invalid_config)
        # Should warn about uppercase in ID
        assert len(errors) > 0
        assert any("lowercase" in err.lower() or "id" in err.lower() for err in errors)


class TestDiscordIntegration:
    """Test Discord webhook integration"""

    def test_send_discord_alert_ath(self):
        """Test sending ATH alert to Discord"""
        alerts = [
            {
                "type": "ath",
                "crypto": "Bitcoin (BTC)",
                "currentPrice": 48300,
                "athPrice": 69000,
                "dropPercent": 30.0,
                "threshold": 30
            }
        ]

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            with patch("crypto_alert.DISCORD_WEBHOOK_URL", "https://discord.webhook.url"):
                crypto_alert.send_discord_alert(alerts)

                # Verify webhook was called
                assert mock_post.called
                call_args = mock_post.call_args
                payload = call_args.kwargs["json"]
                assert "embeds" in payload
                assert "ATH Drop Alerts" in payload["embeds"][0]["description"]

    def test_send_discord_alert_price(self):
        """Test sending price alert to Discord"""
        alerts = [
            {
                "type": "price",
                "crypto": "Bitcoin (BTC)",
                "currentPrice": 69000,
                "targetPrice": 70000,
                "priceDiff": -1000,
                "priceDiffPercent": -1.43
            }
        ]

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            with patch("crypto_alert.DISCORD_WEBHOOK_URL", "https://discord.webhook.url"):
                crypto_alert.send_discord_alert(alerts)

                # Verify webhook was called
                assert mock_post.called
                call_args = mock_post.call_args
                payload = call_args.kwargs["json"]
                assert "Price Alerts" in payload["embeds"][0]["description"]

    def test_send_discord_alert_empty(self):
        """Test that no webhook is called for empty alerts"""
        with patch("requests.post") as mock_post:
            crypto_alert.send_discord_alert([])
            assert not mock_post.called
