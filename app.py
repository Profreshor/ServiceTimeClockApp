# app.py
"""
Flask entry point for the Warner Service Time Clock web app.
Serves the technician dashboard and cached JSON API endpoint.
"""

from flask import Flask, jsonify, render_template, request
from utils.cache_utils import start_cache, get_cached_data, stop_cache
from utils.log_utils import setup_logger
import signal
import sys
import json
import os

# -------------------------------------------------------------------
# Flask setup
# -------------------------------------------------------------------
app = Flask(__name__)
logger = setup_logger()

# -------------------------------------------------------------------
# Config loader
# -------------------------------------------------------------------
def load_config():
    """Load configuration (including branch names) from config.json."""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "r") as f:
        return json.load(f)

config = load_config()

# Start cache refresh thread immediately on launch
start_cache()

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.route("/")
def index():
    """
    Main dashboard route.
    Accepts optional ?branch=### parameter to filter displayed data.
    Displays friendly branch name from config.json.
    """
    branch_id = request.args.get("branch", "100")
    branch_name = config.get("branches", {}).get(branch_id, f"Branch {branch_id}")
    return render_template("index.html", branch_name=branch_name)


@app.route("/api/timeclock")
def api_timeclock():
    """
    API endpoint returning cached technician data.
    Optional ?branch=### filters by BrnId.
    """
    import math

    branch = request.args.get("branch")
    cache = get_cached_data()
    data = cache.get("data", [])

    if branch:
        data = [r for r in data if str(r.get("BrnId")) == str(branch)]

    # --- Clean invalid JSON values (e.g., NaN, None) before jsonify ---
    def clean_json(obj):
        if isinstance(obj, list):
            return [clean_json(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: clean_json(v) for k, v in obj.items()}
        elif obj is None or (isinstance(obj, float) and math.isnan(obj)):
            return None
        else:
            return obj

    data = clean_json(data)

    response = {
        "last_refresh": cache.get("last_refresh"),
        "record_count": len(data),
        "data": data
    }

    return jsonify(response)

# -------------------------------------------------------------------
# Graceful shutdown
# -------------------------------------------------------------------
def shutdown_handler(*_):
    """Stop background cache thread and exit cleanly."""
    logger.info("Stopping Service Time Clock app...")
    stop_cache()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# -------------------------------------------------------------------
# Run server
# -------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting Warner Service Time Clock app on port 8080...")
    app.run(host="0.0.0.0", port=8080, debug=False)
