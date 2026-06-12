"""
fetch_mandi.py — data.gov.in (Agmarknet) से मंडी भाव लाना + manual_rates.csv से merge.

हर ज़िले के लिए एक API call होती है, फिर commodity के नाम config की crop list
से मिलाए जाते हैं। जो भाव API से नहीं मिलता, वह manual_rates.csv से लिया जाता है।
हर भाव के साथ source (मंडी का नाम / "manual") जुड़ा रहता है — कोई fake data नहीं।
"""

import csv
import os
from datetime import date, datetime, timedelta

import requests

API_BASE = "https://api.data.gov.in/resource/"


def _parse_date(text):
    """Agmarknet तारीख DD/MM/YYYY देता है, manual CSV में DD-MM-YYYY लिखते हैं।"""
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def _get_api_key(config):
    # GitHub Actions पर key secret (env variable) से आती है;
    # laptop पर config.json वाली key इस्तेमाल होती है।
    key = os.environ.get("DATA_GOV_API_KEY", "").strip()
    if key:
        return key
    key = config.get("data_gov_api_key", "").strip()
    if key and "YAHAN" not in key:
        return key
    return None


def fetch_district_records(config, district_name):
    """एक ज़िले के आज-कल के सारे Agmarknet records लाओ। दिक्कत हो तो खाली list."""
    api_key = _get_api_key(config)
    if not api_key:
        print(f"  [mandi] API key नहीं मिली — {district_name} के लिए सिर्फ manual rates use होंगे")
        return []

    url = API_BASE + config["agmarknet_resource_id"]
    params = {
        "api-key": api_key,
        "format": "json",
        "limit": 500,
        "filters[state.keyword]": config["state"],
        "filters[district]": district_name,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        records = resp.json().get("records", [])
        print(f"  [mandi] {district_name}: API से {len(records)} records मिले")
        return records
    except Exception as e:
        print(f"  [mandi] {district_name}: API error ({e}) — manual fallback use होगा")
        return []


def _match_crop(commodity_name, crop):
    """API का commodity नाम config की crop से मिलाओ (case-insensitive)।"""
    c = (commodity_name or "").strip().lower()
    return any(c.startswith(n.lower()) for n in crop["agmarknet_names"])


def _pick_rate_from_api(records, crop, oldest_ok):
    """इस फसल का सबसे ताज़ा भाव चुनो (oldest_ok से पुराना नहीं)।"""
    best = None
    for r in records:
        if not _match_crop(r.get("commodity"), crop):
            continue
        d = _parse_date(r.get("arrival_date", ""))
        if d is None or d < oldest_ok:
            continue
        try:
            price = int(float(r.get("modal_price")))
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        if best is None or d > best["date"]:
            best = {
                "price": price,
                "date": d,
                "source": (r.get("market") or "").strip() + " मंडी",
                "from": "api",
            }
    return best


def load_manual_rates(csv_path, oldest_ok):
    """manual_rates.csv पढ़ो — सिर्फ ताज़ा (oldest_ok तक की) entries रखो।
    Returns: {(district, crop_key): rate_dict}"""
    rates = {}
    if not os.path.exists(csv_path):
        return rates
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # '#' से शुरू होने वाली comment lines छोड़ दो
            if (row.get("date") or "").strip().startswith("#"):
                continue
            d = _parse_date(row.get("date", ""))
            if d is None or d < oldest_ok:
                continue
            try:
                price = int(float(row.get("price_per_quintal", "")))
            except (TypeError, ValueError):
                continue
            key = (row.get("district", "").strip().lower(),
                   row.get("crop", "").strip().lower())
            note = (row.get("note") or "").strip()
            rates[key] = {
                "price": price,
                "date": d,
                "source": note if note else "स्थानीय जानकारी",
                "from": "manual",
            }
    return rates


def get_all_rates(config, base_dir):
    """
    मुख्य function: हर ज़िले की हर फसल का भाव (API पहले, फिर manual fallback)।
    Returns: {district_name: {crop_key: rate_dict_or_None}}
    """
    today = date.today()
    oldest_ok = today - timedelta(days=int(config.get("max_rate_age_days", 2)))
    manual = load_manual_rates(os.path.join(base_dir, "manual_rates.csv"), oldest_ok)

    result = {}
    for district in config["districts"]:
        name = district["name"]
        records = fetch_district_records(config, name)
        crops = {}
        for crop in config["crops"]:
            rate = _pick_rate_from_api(records, crop, oldest_ok)
            if rate is None:
                rate = manual.get((name.lower(), crop["key"].lower()))
            crops[crop["key"]] = rate  # None भी हो सकता है = आज भाव उपलब्ध नहीं
        result[name] = crops
    return result
