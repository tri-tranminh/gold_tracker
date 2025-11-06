import csv
import os
import re
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup

URL = "https://ngoctham.com/bang-gia-vang/"
CSV_FILE = "gold_history.csv"

# Vietnam local time for the timestamp
VN_TZ = timezone(timedelta(hours=7))

# Normalize money like "14.580.000" -> 14580000 (int)
def parse_vnd(text: str) -> int:
    if not text:
        return 0
    # keep digits only
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0

def ensure_csv_header():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "type", "buy", "sell"])

def load_existing_rows():
    rows = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    return rows

def already_saved_today(existing, gold_type, today_str):
    # Prevent duplicate entries for the same type on the same date (YYYY-MM-DD)
    for r in existing:
        if r["type"] == gold_type and r["date"].startswith(today_str):
            return True
    return False

def crawl():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the first table that looks like the price table
    # (has headers like "LOẠI VÀNG", "GIÁ MUA", "GIÁ BÁN")
    target_table = None
    for table in soup.find_all("table"):
        head = table.find("thead") or table
        th_text = " ".join(th.get_text(strip=True).upper() for th in head.find_all("th"))
        if ("LOẠI" in th_text and "VÀNG" in th_text) and ("MUA" in th_text) and ("BÁN" in th_text):
            target_table = table
            break
    if target_table is None:
        # fallback: pick the first table on the page
        tables = soup.find_all("table")
        if tables:
            target_table = tables[0]
        else:
            raise RuntimeError("No table found on page.")

    result = []
    rows = target_table.find_all("tr")
    # skip header row
    for tr in rows[1:]:
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(tds) < 3:
            continue
        gold_type = tds[0]
        buy = parse_vnd(tds[1])
        sell = parse_vnd(tds[2])
        if gold_type and (buy or sell):
            result.append((gold_type, buy, sell))
    if not result:
        raise RuntimeError("No price rows parsed. The page structure may have changed.")
    return result

def main():
    ensure_csv_header()
    existing = load_existing_rows()

    now = datetime.now(VN_TZ)
    timestamp = now.strftime("%Y-%m-%d %H:%M")
    today_str = now.strftime("%Y-%m-%d")

    data = crawl()

    appended = 0
    with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for gold_type, buy, sell in data:
            # Avoid duplicate for the same day/type
            if not already_saved_today(existing, gold_type, today_str):
                writer.writerow([timestamp, gold_type, buy, sell])
                appended += 1

    print(f"✅ Scrape complete. {appended} new rows added at {timestamp} (VN time).")
    if appended == 0:
        print("ℹ️ Data for today already exists. Nothing new to add.")

if __name__ == "__main__":
    main()
