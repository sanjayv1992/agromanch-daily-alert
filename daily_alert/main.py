"""
main.py — पूरा system एक बार चलाने वाली script.

चलाने का तरीका (laptop पर):
    python daily_alert/main.py

GitHub Actions रोज़ सुबह 6:00 IST पर इसी को चलाता है
(.github/workflows/daily_alert.yml देखें)।

Steps: config पढ़ो → मंडी भाव लाओ (API + manual merge) → मौसम लाओ
→ Hindi messages बनाओ → docs/index.html और docs/data/latest.json लिखो।
"""

import json
import os
import sys
from datetime import date

# Windows console पर Hindi print करने के लिए
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # daily_alert/
REPO_ROOT = os.path.dirname(BASE_DIR)                    # repo root
sys.path.insert(0, BASE_DIR)

from fetch_mandi import get_all_rates            # noqa: E402
from fetch_weather import get_weather            # noqa: E402
from generate_messages import build_message, build_html, build_json  # noqa: E402


def main():
    with open(os.path.join(BASE_DIR, "config.json"), encoding="utf-8") as f:
        config = json.load(f)

    today = date.today()
    print(f"=== Agromanch Daily Alert — {today.isoformat()} ===")

    print("\n[1/3] मंडी भाव...")
    rates_all = get_all_rates(config, BASE_DIR)

    print("\n[2/3] मौसम...")
    weather_all = {}
    for district in config["districts"]:
        weather_all[district["name"]] = get_weather(district, config["weather"])

    print("\n[3/3] Messages + HTML page...")
    messages = []
    for district in config["districts"]:
        msg = build_message(
            district=district,
            rates=rates_all[district["name"]],
            weather=weather_all[district["name"]],
            app_link=config["app_link"],
            today=today,
        )
        messages.append((district, msg))

    html_path = os.path.join(REPO_ROOT, config["output_html"])
    json_path = os.path.join(REPO_ROOT, config["output_json"])
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(build_html(messages, today))
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(build_json(messages, rates_all, weather_all, today))

    print(f"\n✔ Page तैयार: {html_path}")
    print(f"✔ Data:        {json_path}")


if __name__ == "__main__":
    main()
