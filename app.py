from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, time

from db import init_db, insert_price, get_recent_prices, upsert_signal, get_all_signals
from ml_engine import compute_signal, is_anomaly

app = Flask(__name__, static_folder="static")
CORS(app)   # allows your web dashboard and ESP32 to call freely

init_db()

# ── POST /ingest  ─────────────────────────────────────────────────────────────
# Called by ESP32 every 15s with its latest fetched data.
# Body (JSON): { "stocks": [ {sym, price, open, high, low, volume, pct, spk}, … ] }

@app.route("/ingest", methods=["POST"])
def ingest():
    body = request.get_json(force=True, silent=True)
    if not body or "stocks" not in body:
        return jsonify({"error": "Missing stocks array"}), 400

    results = []
    for s in body["stocks"]:
        sym    = s.get("sym", "").upper().strip()
        price  = float(s.get("price", 0))
        open_  = float(s.get("open",  0))
        high   = float(s.get("high",  0))
        low    = float(s.get("low",   0))
        volume = int(s.get("vol",     0))
        pct    = float(s.get("pct",   0))

        if not sym or price <= 0:
            continue

        # 1. Persist to SQLite
        insert_price(sym, price, open_, high, low, volume, pct)

        # 2. Pull recent history for analysis
        recent = get_recent_prices(sym, n=60)
        prices = [r["price"] for r in recent]
        pcts   = [r["pct"]   for r in recent]

        # 3. Run ML
        signal, reason, zscore = compute_signal(prices, pcts)
        anomaly = is_anomaly(zscore)

        # 4. Store signal
        upsert_signal(sym, signal, reason, anomaly, zscore)

        results.append({"sym": sym, "signal": signal, "anomaly": anomaly})

    return jsonify({"ok": True, "analyzed": results})


# ── GET /signals  ─────────────────────────────────────────────────────────────
# Polled by ESP32 and web dashboard to get latest signals for all stocks.

@app.route("/signals", methods=["GET"])
def signals():
    return jsonify({"signals": get_all_signals()})


# ── GET /signals/<sym>  ───────────────────────────────────────────────────────
# Optional: single stock signal (useful for ESP32 to check one at a time).

@app.route("/signals/<sym>", methods=["GET"])
def signal_one(sym):
    all_s = get_all_signals()
    match = next((s for s in all_s if s["symbol"] == sym.upper()), None)
    if not match:
        return jsonify({"error": "Not found"}), 404
    return jsonify(match)


# ── GET /  ────────────────────────────────────────────────────────────────────
# Serves your web dashboard from static/index.html

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)