import pytest
import json
from datetime import date, timedelta
from unittest.mock import patch, mock_open, MagicMock
import update_52w_stats


@pytest.fixture
def sample_coins_config():
    """Sample coins configuration"""
    return {
        "coins": [
            {
                "id": "bitcoin",
                "name": "Bitcoin",
                "symbol": "BTC"
            },
            {
                "id": "ethereum",
                "name": "Ethereum",
                "symbol": "ETH"
            }
        ]
    }


@pytest.fixture
def sample_52w_stats():
    """Sample 52w stats data"""
    return {
        "last_updated": str(date.today()),
        "coins": {
            "bitcoin": {
                "high_52w": 124128,
                "low_52w": 15460,
                "updated_at": str(date.today())
            },
            "ethereum": {
                "high_52w": 4878,
                "low_52w": 880,
                "updated_at": str(date.today())
            }
        }
    }


@pytest.fixture
def sample_market_chart_response():
    """Sample API response for market chart"""
    return {
        "prices": [
            [1640000000000, 50000],
            [1641000000000, 55000],
            [1642000000000, 45000],
            [1643000000000, 60000],
            [1644000000000, 40000]
        ]
    }


class TestLoadStats:
    """Test loading 52w stats from file"""

    def test_load_stats_success(self, sample_52w_stats):
        """Test successful loading of 52w stats"""
        mock_file_content = json.dumps(sample_52w_stats)
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            result = update_52w_stats.load_52w_stats()
            assert result["last_updated"] == str(date.today())
            assert "bitcoin" in result["coins"]
            assert result["coins"]["bitcoin"]["high_52w"] == 124128

    def test_load_stats_file_not_found(self):
        """Test handling when stats file doesn't exist"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = update_52w_stats.load_52w_stats()
            assert result == {"last_updated": None, "coins": {}}

    def test_load_stats_invalid_json(self):
        """Test handling of invalid JSON in stats file"""
        with patch("builtins.open", mock_open(read_data="invalid json")):
            result = update_52w_stats.load_52w_stats()
            assert result == {"last_updated": None, "coins": {}}


class TestSaveStats:
    """Test saving 52w stats to file"""

    def test_save_stats_success(self, sample_52w_stats):
        """Test successful saving of 52w stats"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            update_52w_stats.save_52w_stats(sample_52w_stats)
            mock_file.assert_called_once_with("52w_stats.json", 'w')
            handle = mock_file()
            written_data = "".join(call.args[0] for call in handle.write.call_args_list)
            assert "bitcoin" in written_data
            assert "high_52w" in written_data

    def test_save_stats_with_custom_file(self, sample_52w_stats):
        """Test saving to custom file path"""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            update_52w_stats.save_52w_stats(sample_52w_stats, "custom_stats.json")
            mock_file.assert_called_once_with("custom_stats.json", 'w')


class TestFetchMarketChart:
    """Test fetching 52w high/low from API"""

    def test_fetch_52w_success(self, sample_market_chart_response):
        """Test successful API call for 52w data"""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_market_chart_response
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = update_52w_stats.fetch_52w_high_low("bitcoin")
            assert result["high_52w"] == 60000
            assert result["low_52w"] == 40000

    def test_fetch_52w_api_error(self):
        """Test handling of API errors"""
        import requests
        with patch("requests.get", side_effect=requests.exceptions.RequestException("API Error")):
            result = update_52w_stats.fetch_52w_high_low("bitcoin")
            assert result is None

    def test_fetch_52w_empty_prices(self):
        """Test handling when API returns no price data"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"prices": []}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = update_52w_stats.fetch_52w_high_low("bitcoin")
            assert result is None

    def test_fetch_52w_malformed_response(self):
        """Test handling malformed API response"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"invalid": "data"}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            result = update_52w_stats.fetch_52w_high_low("bitcoin")
            assert result is None


class TestStaleCheck:
    """Test checking if stats are stale"""

    def test_stats_not_stale(self):
        """Test that fresh stats are not considered stale"""
        today = str(date.today())
        assert update_52w_stats.is_stats_stale(today, max_age_days=7) is False

    def test_stats_stale_after_7_days(self):
        """Test that stats older than 7 days are stale"""
        old_date = str(date.today() - timedelta(days=8))
        assert update_52w_stats.is_stats_stale(old_date, max_age_days=7) is True

    def test_stats_stale_exactly_7_days(self):
        """Test edge case: exactly 7 days old"""
        seven_days_ago = str(date.today() - timedelta(days=7))
        assert update_52w_stats.is_stats_stale(seven_days_ago, max_age_days=7) is False

    def test_stats_stale_no_date(self):
        """Test that None date is considered stale"""
        assert update_52w_stats.is_stats_stale(None, max_age_days=7) is True

    def test_stats_stale_invalid_date(self):
        """Test that invalid date string is considered stale"""
        assert update_52w_stats.is_stats_stale("invalid-date", max_age_days=7) is True


class TestUpdateStats:
    """Test main update function"""

    def test_update_all_coins_success(self, sample_coins_config, sample_market_chart_response):
        """Test successfully updating stats for all coins"""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_market_chart_response
        mock_response.raise_for_status = MagicMock()

        coins_config_json = json.dumps(sample_coins_config)
        mock_file = mock_open(read_data=coins_config_json)

        with patch("builtins.open", mock_file), \
             patch("requests.get", return_value=mock_response), \
             patch("update_52w_stats.save_52w_stats") as mock_save, \
             patch("time.sleep"):

            update_52w_stats.update_all_52w_stats()

            # Verify save was called
            assert mock_save.called
            saved_data = mock_save.call_args[0][0]
            assert "coins" in saved_data
            assert "bitcoin" in saved_data["coins"]
            assert "ethereum" in saved_data["coins"]
            assert saved_data["last_updated"] == str(date.today())

    def test_update_skips_failed_coins(self, sample_coins_config):
        """Test that update continues even if one coin fails"""
        import requests

        def side_effect_api(*args, **kwargs):
            url = args[0]
            if "bitcoin" in url:
                raise requests.exceptions.RequestException("API Error")
            else:
                mock_resp = MagicMock()
                mock_resp.json.return_value = {
                    "prices": [[1640000000000, 1000], [1641000000000, 2000]]
                }
                mock_resp.raise_for_status = MagicMock()
                return mock_resp

        coins_config_json = json.dumps(sample_coins_config)
        mock_file = mock_open(read_data=coins_config_json)

        with patch("builtins.open", mock_file), \
             patch("requests.get", side_effect=side_effect_api), \
             patch("update_52w_stats.save_52w_stats") as mock_save, \
             patch("time.sleep"):

            update_52w_stats.update_all_52w_stats()

            # Should still save ethereum data even though bitcoin failed
            assert mock_save.called
            saved_data = mock_save.call_args[0][0]
            assert "ethereum" in saved_data["coins"]
            assert "bitcoin" not in saved_data["coins"]

    def test_update_respects_rate_limiting(self, sample_coins_config, sample_market_chart_response):
        """Test that rate limiting sleep is called between API requests"""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_market_chart_response
        mock_response.raise_for_status = MagicMock()

        coins_config_json = json.dumps(sample_coins_config)
        mock_file = mock_open(read_data=coins_config_json)

        with patch("builtins.open", mock_file), \
             patch("requests.get", return_value=mock_response), \
             patch("update_52w_stats.save_52w_stats"), \
             patch("time.sleep") as mock_sleep:

            update_52w_stats.update_all_52w_stats()

            # Should sleep between requests (2 coins = 1 sleep between them)
            assert mock_sleep.call_count >= 1


class TestGetStats:
    """Test getting stats for a specific coin"""

    def test_get_coin_stats_exists(self, sample_52w_stats):
        """Test getting stats for existing coin"""
        result = update_52w_stats.get_coin_52w_stats("bitcoin", sample_52w_stats)
        assert result is not None
        assert result["high_52w"] == 124128
        assert result["low_52w"] == 15460

    def test_get_coin_stats_not_exists(self, sample_52w_stats):
        """Test getting stats for non-existent coin"""
        result = update_52w_stats.get_coin_52w_stats("dogecoin", sample_52w_stats)
        assert result is None

    def test_get_coin_stats_empty_data(self):
        """Test getting stats from empty data"""
        empty_stats = {"last_updated": None, "coins": {}}
        result = update_52w_stats.get_coin_52w_stats("bitcoin", empty_stats)
        assert result is None
