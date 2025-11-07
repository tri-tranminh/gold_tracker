import csv
import os
import re
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup
import pandas as pd

URL = "https://ngoctham.com/bang-gia-vang/"
CSV_FILE = "gold_history.csv"

# Vietnam timezone
VN_TZ = timezone(timedelta(hours=7))

def parse_vnd(text: str) -> int:
    if not text:
        return 0
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0

def ensure_csv_header():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "date", "type", "buy", "sell"])

def load_df():
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame(columns=["timestamp", "date", "type", "buy", "sell"])
    df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    # Normalize types
    for col in ["timestamp", "date", "type", "buy", "sell"]:
        if col not in df.columns:
            df[col] = None
    # Parse timestamp, keep original string date as-is
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["buy"]  = pd.to_numeric(df["buy"], errors="coerce").fillna(0).astype(int)
    df["sell"] = pd.to_numeric(df["sell"], errors="coerce").fillna(0).astype(int)
    return df

def crawl():
    headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Find a table with headers containing LOẠI/MUA/BÁN
    target_table = None
    for table in soup.find_all("table"):
        head = table.find("thead") or table
        th_text = " ".join(th.get_text(strip=True).upper() for th in head.find_all("th"))
        if all(k in th_text for k in ["LOẠI", "MUA", "BÁN"]):
            target_table = table
            break
    if target_table is None:
        tables = soup.find_all("table")
        if tables:
            target_table = tables[0]
        else:
            raise RuntimeError("No price table found.")

    rows = []
    for tr in target_table.find_all("tr")[1:]:
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(tds) < 3:
            continue
        gold_type = tds[0]
        buy = parse_vnd(tds[1])
        sell = parse_vnd(tds[2])
        if gold_type and (buy or sell):
            rows.append((gold_type, buy, sell))
    if not rows:
        raise RuntimeError("Parsed 0 price rows.")
    return rows

def main():
    ensure_csv_header()
    df = load_df()

    now_vn = datetime.now(VN_TZ)
    timestamp = now_vn.strftime("%Y-%m-%d %H:%M:%S")
    today_str = now_vn.strftime("%Y-%m-%d")

    fresh = crawl()

    # Build today's latest by type from existing CSV
    today_df = df[df["timestamp"].dt.strftime("%Y-%m-%d") == today_str] if not df.empty else pd.DataFrame()
    latest_today_by_type = {}
    if not today_df.empty:
        today_sorted = today_df.sort_values("timestamp")
        # keep last (latest) per type
        latest_today_by_type = today_sorted.groupby("type").tail(1).set_index("type")[["buy", "sell"]].to_dict("index")

    to_append = []
    for gold_type, buy, sell in fresh:
        prev = latest_today_by_type.get(gold_type)
        if prev is None:
            # no entry today -> append
            to_append.append([timestamp, today_str, gold_type, buy, sell])
        else:
            if int(prev["buy"]) != buy or int(prev["sell"]) != sell:
                # changed -> append
                to_append.append([timestamp, today_str, gold_type, buy, sell])
            # else unchanged -> skip

    if to_append:
        with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            for row in to_append:
                w.writerow(row)
        print(f"✅ Appended {len(to_append)} new rows at {timestamp} VN.")
    else:
        print(f"ℹ️ No changes detected at {timestamp} VN.")

if __name__ == "__main__":
    main()
