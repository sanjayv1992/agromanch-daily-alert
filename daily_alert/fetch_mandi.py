"""
fetch_mandi.py — data.gov.in (Agmarknet) से मंडी भाव लाना + manual_rates.csv से merge.

हर ज़िले के लिए एक API call होती है, फिर commodity के नाम config की crop list
से मिलाए जाते हैं। जो भाव API से नहीं मिलता, वह manual_rates.csv से लिया जाता है।
हर भाव के साथ source (मंडी का नाम / "manual") जुड़ा रहता है — कोई fake data नहीं।
"""

import csv
import os
import time
from datetime import date, datetime, timedelta

import requests

API_BASE = "https://api.data.gov.in/resource/"

# कुछ सरकारी firewall 'python-requests' वाली requests को रोक/अटका देते हैं।
# इसलिए browser जैसा User-Agent भेजते हैं ताकि request सामान्य लगे।
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


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
    # data.gov.in API अक्सर धीमी रहती है — इसलिए 3 बार कोशिश (हर बार ज़्यादा इंतज़ार)।
    # जैसे ही जवाब मिल जाए, बाकी कोशिशें छोड़ देते हैं।
    last_error = None
    for attempt in range(1, 4):
        try:
            resp = requests.get(url, params=params, headers=HTTP_HEADERS, timeout=60)
            resp.raise_for_status()
            records = resp.json().get("records", [])
            print(f"  [mandi] {district_name}: API से {len(records)} records मिले"
                  f"{'' if attempt == 1 else f' (कोशिश {attempt})'}")
            return records
        except Exception as e:
            last_error = e
            if attempt < 3:
                time.sleep(5 * attempt)  # 5s, फिर 10s रुककर दोबारा
    print(f"  [mandi] {district_name}: API error ({last_error}) — manual fallback use होगा")
    return []


def _norm_commodity(name):
    """API का commodity नाम साफ़ करो — कोष्ठक हटाकर मुख्य नाम।
    जैसे 'Paddy(Common)' -> 'Paddy', 'Bhindi(Ladies Finger)' -> 'Bhindi'."""
    return (name or "").split("(")[0].strip()


def _hindi_for(commodity_norm, commodity_hindi):
    """commodity का Hindi नाम — map में हो तो वही, वरना अंग्रेज़ी नाम ही दिखा दो।
    (case-insensitive match ताकि 'wheat'/'Wheat' दोनों चलें)"""
    if not commodity_norm:
        return None
    for eng, hin in commodity_hindi.items():
        if eng.lower() == commodity_norm.lower():
            return hin
    return commodity_norm  # अनजान फसल भी छूटे नहीं — अंग्रेज़ी नाम से दिखेगी


def _in_range(price, hindi, price_range):
    """भाव सही सीमा में है या नहीं। जिस फसल की सीमा तय नहीं, वह हमेशा सही मानी जाती है।"""
    bounds = price_range.get(hindi)
    if not bounds:
        return True
    lo, hi = bounds
    return lo <= price <= hi


def _api_rates_by_hindi(records, oldest_ok, commodity_hindi, ignore, price_range,
                        district_name=""):
    """एक ज़िले के API records से हर फसल का सबसे ताज़ा भाव (Hindi नाम के हिसाब से)।
    एक ही Hindi नाम पर कई commodity (जैसे Rice+Paddy=धान) आएँ तो सबसे ताज़ा/पहला रखता है।
    तय सीमा से बाहर का भाव छाँट दिया जाता है।
    Returns: {hindi_name: rate_dict}"""
    rates = {}
    for r in records:
        norm = _norm_commodity(r.get("commodity"))
        if not norm or norm.lower() in ignore:
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
        hindi = _hindi_for(norm, commodity_hindi)
        if not _in_range(price, hindi, price_range):
            print(f"  [mandi] {district_name}: {hindi} ₹{price} सीमा से बाहर — छोड़ा")
            continue
        cand = {
            "price": price,
            "date": d,
            "source": (r.get("market") or "").strip() + " मंडी",
            "from": "api",
        }
        existing = rates.get(hindi)
        if existing is None or d > existing["date"]:
            rates[hindi] = cand
    return rates


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


def _ordered(rates, priority_hindi):
    """फसलें क्रम में लगाओ — पहले config की priority फसलें (धान, गेहूं...),
    फिर बाकी सब Hindi नाम के अक्षर-क्रम में।"""
    def rank(hindi):
        return (priority_hindi.index(hindi) if hindi in priority_hindi
                else len(priority_hindi), hindi)
    return {h: rates[h] for h in sorted(rates, key=rank)}


def get_all_rates(config, base_dir):
    """
    मुख्य function: हर ज़िले में जो भी फसल मंडी में है, उस सबका भाव।
    API से सारी commodity (Hindi में) लाता है, फिर manual_rates.csv की बची फसलें जोड़ता है।
    Returns: {district_name: {hindi_name: rate_dict}}  (खाली भी हो सकता है)
    """
    today = date.today()
    oldest_ok = today - timedelta(days=int(config.get("max_rate_age_days", 2)))
    manual = load_manual_rates(os.path.join(base_dir, "manual_rates.csv"), oldest_ok)

    commodity_hindi = config.get("commodity_hindi", {})
    ignore = {x.lower() for x in config.get("ignore_commodities", [])}
    price_range = config.get("price_range", {})
    # manual CSV का crop key -> Hindi (config crops से)
    crop_key_hindi = {c["key"].lower(): c["hindi"] for c in config.get("crops", [])}
    # दिखाने का क्रम: config crops की Hindi सूची सबसे ऊपर
    priority_hindi = [c["hindi"] for c in config.get("crops", [])]

    result = {}
    for district in config["districts"]:
        name = district["name"]
        records = fetch_district_records(config, name)
        rates = _api_rates_by_hindi(records, oldest_ok, commodity_hindi, ignore,
                                    price_range, name)

        # manual entries — सिर्फ वहीं जहाँ API से वो फसल नहीं मिली (API को प्राथमिकता)
        for (dist_l, crop_l), rate in manual.items():
            if dist_l != name.lower():
                continue
            hindi = crop_key_hindi.get(crop_l, crop_l)
            rates.setdefault(hindi, rate)

        result[name] = _ordered(rates, priority_hindi)
    return result
