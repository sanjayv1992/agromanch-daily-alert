"""
fetch_weather.py — Open-Meteo (free, बिना API key) से हर ज़िले का आज का मौसम।

देता है: आज का max/min तापमान, बारिश की संभावना (%), बारिश (mm),
और किसान के लिए Hindi चेतावनी lines (तेज़ बारिश / लू / ठंड)।
"""

import requests

API_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather(district, thresholds):
    """एक ज़िले का आज का मौसम। दिक्कत हो तो None (message में मौसम line नहीं जाएगी)।"""
    params = {
        "latitude": district["lat"],
        "longitude": district["lon"],
        "daily": "temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max,precipitation_sum",
        "timezone": "Asia/Kolkata",
        "forecast_days": 1,
    }
    try:
        resp = requests.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        daily = resp.json()["daily"]
        tmax = round(daily["temperature_2m_max"][0])
        tmin = round(daily["temperature_2m_min"][0])
        rain_prob = int(daily["precipitation_probability_max"][0] or 0)
        rain_mm = float(daily["precipitation_sum"][0] or 0)
    except Exception as e:
        print(f"  [weather] {district['name']}: error ({e}) — मौसम नहीं दिखेगा")
        return None

    # किसान के काम की चेतावनियाँ — सीमाएँ config.json के 'weather' section में हैं
    warnings = []
    if rain_prob >= thresholds["rain_probability_warning"] or rain_mm >= thresholds["rain_mm_warning"]:
        warnings.append("⚠️ तेज़ बारिश की संभावना — कटी फसल/अनाज ढककर रखें, मंडी ले जाने से पहले मौसम देख लें।")
    if tmax >= thresholds["heat_warning_celsius"]:
        warnings.append("⚠️ भीषण गर्मी/लू — दोपहर 12 से 4 बजे खेत के काम से बचें, सिंचाई शाम को करें।")
    if tmin <= thresholds["cold_warning_celsius"]:
        warnings.append("⚠️ कड़ाके की ठंड/पाला संभव — नर्सरी और सब्ज़ी की फसल ढकें।")

    print(f"  [weather] {district['name']}: {tmax}°/{tmin}°C, बारिश {rain_prob}%")
    return {
        "tmax": tmax,
        "tmin": tmin,
        "rain_prob": rain_prob,
        "rain_mm": rain_mm,
        "warnings": warnings,
    }
