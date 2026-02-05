import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import os
import sys

URL = "https://ngoctham.com/bang-gia-vang/"
CSV_FILE = "gold_history.csv"
TIMEZONE = "Asia/Ho_Chi_Minh"

# -------------------------
# Helpers
# -------------------------

def clean_price(text: str) -> int:
    """
    Convert '17.420.000' → 17420000
    """
    return int(text.replace(".", "").replace(",", "").strip())


def normalize_gold_name(name: str) -> str:
    """
    Normalize gold names so UI & charts stay consistent
    """
    name = name.strip()

    if "SJC" in name:
        return "Vàng miếng SJC"
    if "Nhẫn" in name:
        return "Vàng Nhẫn 999.9"
    if "Ta 999.9" in name:
        return "Vàng Ta (999.9)"
    if "Ta 990" in name:
        return "Vàng Ta (990)"
    if "18K" in name or "750" in name:
        return "Vàng 18K (750)"
    if "Trắng" in name or "AU750" in name.upper():
        return "Vàng trắng Au750"

    return name


def parse_update_time(soup: BeautifulSoup) -> datetime:
    """
    Parse: 'Cập nhật ngày 05/02/2026 7:16 PM'
    """
    time_el = soup.select_one(".time")
    if not time_el:
        return datetime.now()

    raw = time_el.get_text(" ", strip=True)
    raw = raw.replace("Cập nhật ngày", "").strip()

    try:
        return datetime.strptime(raw, "%d/%m/%Y %I:%M %p")
    except Exception:
        return datetime.now()


# -------------------------
# Main scraper
# -------------------------

def main():
    try:
        resp = requests.get(
            URL,
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0 (GoldTracker Bot)"
            }
        )
        resp.raise_for_status()
    except Exception as e:
        print("❌ Request failed:", e)
        sys.exit(0)  # IMPORTANT: do not fail GitHub Action

    soup = BeautifulSoup(resp.text, "html.parser")

    table = soup.select_one("table.table")
    if not table:
        print("❌ Gold table not found")
        sys.exit(0)

    rows = table.select("tbody tr")
    if not rows:
        print("⚠️ No gold rows found")
        sys.exit(0)

    timestamp = parse_update_time(soup)
    ts_str = timestamp.strftime("%Y-%m-%d %H:%M")

    records = []

    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) != 3:
            continue

        try:
            gold_type = normalize_gold_name(tds[0].get_text())
            buy = clean_price(tds[1].get_text())
            sell = clean_price(tds[2].get_text())

            records.append({
                "date": ts_str,
                "type": gold_type,
                "buy": buy,
                "sell": sell
            })

        except Exception as e:
            print("⚠️ Skip row:", e)

    if not records:
        print("⚠️ No valid data parsed")
        sys.exit(0)

    df_new = pd.DataFrame(records)

    # -------------------------
    # Append safely to CSV
    # -------------------------

    if os.path.exists(CSV_FILE):
        try:
            df_old = pd.read_csv(CSV_FILE)
            df = pd.concat([df_old, df_new], ignore_index=True)
        except Exception:
            print("⚠️ CSV corrupted, recreating file")
            df = df_new
    else:
        df = df_new

    # Remove exact duplicates
    df = df.drop_duplicates(subset=["date", "type", "buy", "sell"])

    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")

    print(f"✅ Saved {len(df_new)} rows at {ts_str}")


if __name__ == "__main__":
    main()
