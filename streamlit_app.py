# quotex_wrapper.py

import logging
from collections import defaultdict
from quotexapi.api import QuotexAPI
import quotexapi.global_value as global_value

# Set up logging
logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s', level=logging.INFO)

def nested_dict(n, type):
    if n == 1:
        return defaultdict(type)
    else:
        return defaultdict(lambda: nested_dict(n - 1, type))

class Quotex:
    __version__ = "1.3"

    def __init__(self, set_ssid):
        self.set_ssid = set_ssid
        self.api = None
        self.size = [1, 5, 10, 15, 30, 60, 120, 300, 600, 900,
                     1800, 3600, 7200, 14400, 28800, 43200, 86400, 604800, 2592000]
        self.subscribe_candle = []
        self.subscribe_candle_all_size = []
        self.subscribe_mood = []

    def connect(self):
        """Connect to Quotex via WebSocket using SSID."""
        try:
            if self.api:
                self.api.close()
        except Exception as e:
            logging.warning(f"Failed to close previous API instance: {e}")

        try:
            logging.info("Connecting to Quotex via WebSocket...")
            self.api = QuotexAPI("quotex.market", self.set_ssid)
            success, reason = self.api.connect()

            if success:
                logging.info("✅ Connected successfully to Quotex.")
                self.re_subscribe_stream()
                return True, None
            else:
                logging.error(f"❌ Connection failed: {reason}")
                return False, reason
        except Exception as e:
            logging.exception(f"❌ Exception during connection: {e}")
            return False, str(e)

    def re_subscribe_stream(self):
        """Re-subscribe to active streams after reconnect."""
        try:
            for item in self.subscribe_candle:
                self.api.start_candles_stream(item[0], item[1])
            for item in self.subscribe_candle_all_size:
                self.api.start_candles_all_size_stream(item)
            for item in self.subscribe_mood:
                self.api.start_mood_stream(item)
            logging.info("📡 Re-subscribed to all active streams.")
        except Exception as e:
            logging.warning(f"Failed to re-subscribe: {e}")

    def check_connect(self):
        """Check if still connected to WebSocket."""
        return global_value.check_websocket_if_connect is True

    def close(self):
        """Gracefully close the WebSocket connection."""
        try:
            if self.api:
                self.api.close()
                logging.info("🔌 Disconnected from Quotex.")
        except Exception as e:
            logging.warning(f"Failed to close connection: {e}")
