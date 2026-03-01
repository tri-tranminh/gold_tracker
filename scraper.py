#!/usr/bin/env python3
"""
Gold Price Scraper - Fetches gold prices from Ngoc Tham Jewelry API
and stores them in a CSV file. Only uses Python stdlib (no pip dependencies).
"""

import urllib.request
import json
import csv
import os
from datetime import datetime, timezone, timedelta

# Configuration
API_URL = "https://ngoctham.com/ajax/proxy_banggia.php"
CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "gold_prices.csv")
GOLD_TYPES = ["Nhẫn 999.9", "Vàng Miếng SJC (Loại 10 chỉ)"]
VN_TZ = timezone(timedelta(hours=7))


def fetch_gold_prices():
    """Fetch gold prices from Ngoc Tham API."""
    req = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://ngoctham.com/bang-gia-vang/",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data


def parse_prices(data):
    """Extract target gold type prices from API response."""
    results = []
    items = data.get("chitiet", data if isinstance(data, list) else [])

    for item in items:
        name = item.get("loaivang", "").strip()
        if name in GOLD_TYPES:
            buy_price = item.get("giamua", "0").replace(".", "").replace(",", "")
            sell_price = item.get("giaban", "0").replace(".", "").replace(",", "")
            results.append({
                "gold_type": name,
                "buy_price": int(buy_price) if buy_price else 0,
                "sell_price": int(sell_price) if sell_price else 0,
            })
    return results


def load_existing_dates():
    """Load set of existing (date, gold_type) pairs from CSV."""
    existing = set()
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.add((row["date"], row["gold_type"]))
    return existing


def save_prices(prices, today_str):
    """Append new prices to CSV file."""
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)

    file_exists = os.path.exists(CSV_FILE) and os.path.getsize(CSV_FILE) > 0
    existing = load_existing_dates()

    new_rows = []
    for p in prices:
        key = (today_str, p["gold_type"])
        if key not in existing:
            new_rows.append(p)

    if not new_rows:
        print(f"[{today_str}] Data already exists for today. Skipping.")
        return False

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "gold_type", "buy_price", "sell_price"])
        for p in new_rows:
            writer.writerow([today_str, p["gold_type"], p["buy_price"], p["sell_price"]])
            print(f"[{today_str}] Saved: {p['gold_type']} - Buy: {p['buy_price']:,} / Sell: {p['sell_price']:,}")

    return True


def main():
    today = datetime.now(VN_TZ).strftime("%Y-%m-%d")
    print(f"Fetching gold prices for {today}...")

    try:
        data = fetch_gold_prices()
        prices = parse_prices(data)

        if not prices:
            print("WARNING: No target gold types found in API response!")
            print("Available types:", [item.get("loaivang") for item in data.get("chitiet", data if isinstance(data, list) else [])])
            return

        saved = save_prices(prices, today)
        if saved:
            print("Done! Prices saved successfully.")
        else:
            print("Done! No new data to save.")

    except Exception as e:
        print(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
