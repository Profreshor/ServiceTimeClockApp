# utils/cache_utils.py
"""
Cache utility module for the Warner Service Time Clock app.
Maintains an in-memory copy of the latest technician summary and auto-refreshes it
at a fixed interval (configured in config.json).
"""

import json
import os
import threading
from datetime import datetime

import pandas as pd

from utils.db_utils import fetch_punches_today
from utils.transform_utils import summarize_technicians
from utils.log_utils import setup_logger

logger = setup_logger()

# -------------------------------------------------------------------
# Global cache state
# -------------------------------------------------------------------
_cache_data = None
_cache_json = None
_last_refresh = None
_refresh_interval = 60  # default fallback
_refresh_thread = None


# -------------------------------------------------------------------
# Internal refresh logic
# -------------------------------------------------------------------
def _load_config():
    """Load refresh interval and DB settings from config.json."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    with open(os.path.abspath(config_path)) as f:
        return json.load(f)


def _refresh_cache():
    """Pull fresh data from SQL and update the in-memory cache."""
    global _cache_data, _cache_json, _last_refresh, _refresh_thread

    try:
        logger.info("Refreshing cached technician data...")
        df = fetch_punches_today()

        if not df.empty:
            summary = summarize_technicians(df)
            _cache_data = summary
            _cache_json = summary.to_dict(orient="records")
            _last_refresh = datetime.now()
            logger.info(f"Cache updated — {len(summary)} records @ {_last_refresh.strftime('%H:%M:%S')}")
        else:
            logger.warning("No data returned during cache refresh.")

    except Exception as e:
        logger.error(f"Cache refresh failed: {e}")

    # Schedule next refresh
    _refresh_thread = threading.Timer(_refresh_interval, _refresh_cache)
    _refresh_thread.daemon = True
    _refresh_thread.start()


def start_cache():
    """Initialize and start the background cache refresh loop."""
    global _refresh_interval
    cfg = _load_config()
    _refresh_interval = int(cfg.get("refresh_interval_seconds", 60))

    logger.info(f"Starting cache refresh thread (interval = {_refresh_interval}s)")
    _refresh_cache()


def get_cached_data():
    """Return cached JSON data and metadata for API responses."""
    return {
        "last_refresh": _last_refresh.strftime("%Y-%m-%d %H:%M:%S") if _last_refresh else None,
        "record_count": len(_cache_json) if _cache_json else 0,
        "data": _cache_json or [],
    }


def stop_cache():
    """Stop the background refresh loop (used during app shutdown)."""
    global _refresh_thread
    if _refresh_thread:
        _refresh_thread.cancel()
        logger.info("Cache refresh thread stopped.")
