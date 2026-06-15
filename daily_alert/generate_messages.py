"""
generate_messages.py — हर ज़िले का Hindi WhatsApp message बनाना
और सबको एक static HTML page (docs/index.html) में डालना।

HTML page में हर message के साथ:
  (a) "Copy" button  (b) wa.me link — WhatsApp message भरा हुआ खुलता है,
आप group/contact चुनकर खुद send करते हैं। Auto-send कुछ नहीं होता।
"""

import html
import json
import urllib.parse
from datetime import date

HINDI_MONTHS = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून",
                "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]
HINDI_DAYS = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]


def hindi_date(d):
    return f"{d.day} {HINDI_MONTHS[d.month - 1]} {d.year}, {HINDI_DAYS[d.weekday()]}"


def build_message(district, crops_config, rates, weather, app_link, today):
    """एक ज़िले का WhatsApp-ready Hindi message (plain text)।"""
    lines = [
        "🌾 *अग्रोमंच दैनिक भाव*",
        f"📅 {hindi_date(today)}",
        f"📍 ज़िला: {district['hindi']}",
        "",
    ]

    # --- मंडी भाव ---
    rate_lines = []
    for crop in crops_config:
        rate = rates.get(crop["key"])
        if rate is None:
            continue  # जो भाव है ही नहीं, वह message में नहीं जाएगा — no fake data
        line = f"• {crop['hindi']}: ₹{rate['price']}"
        if rate.get("source"):
            line += f" ({rate['source']}"
            # सिर्फ पुराना भाव हो तो तारीख बताओ — भरोसे के लिए
            # (आज/नई तारीख पर नहीं, वरना उलझन होती है)
            if rate["date"] < today:
                line += f", {rate['date'].day} {HINDI_MONTHS[rate['date'].month - 1]}"
            line += ")"
        rate_lines.append(line)

    if rate_lines:
        lines.append("*मंडी भाव (₹/क्विंटल):*")
        lines.extend(rate_lines)
    else:
        lines.append("आज मंडी भाव उपलब्ध नहीं है।")
    lines.append("")

    # --- मौसम ---
    if weather:
        lines.append(f"*मौसम:* {weather['tmax']}°/{weather['tmin']}°C, "
                     f"बारिश की संभावना {weather['rain_prob']}%")
        lines.extend(weather["warnings"])
        lines.append("")

    # --- footer ---
    lines.append("ℹ️ भाव मंडी के हिसाब से थोड़ा ऊपर-नीचे हो सकता है।")
    lines.append("📲 रोज़ का भाव सीधे फ़ोन पर — Agromanch app:")
    lines.append(app_link)
    return "\n".join(lines)


# ---------------------------------------------------------------- HTML page --

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agromanch Daily Alert</title>
<style>
  :root {{ --green:#1b7a3d; --light:#eef7f0; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:'Segoe UI',system-ui,sans-serif; margin:0; background:var(--light); color:#222; }}
  header {{ background:var(--green); color:#fff; padding:14px 16px; }}
  header h1 {{ margin:0; font-size:1.25rem; }}
  header p {{ margin:4px 0 0; font-size:.85rem; opacity:.9; }}
  main {{ max-width:680px; margin:0 auto; padding:12px; }}
  .card {{ background:#fff; border-radius:12px; box-shadow:0 1px 4px rgba(0,0,0,.12);
          margin-bottom:16px; overflow:hidden; }}
  .card h2 {{ margin:0; padding:10px 14px; background:#e3f2e7; color:var(--green);
             font-size:1.05rem; }}
  .msg {{ white-space:pre-wrap; padding:12px 14px; font-size:.92rem; line-height:1.5;
         margin:0; font-family:inherit; }}
  .btns {{ display:flex; gap:10px; padding:0 14px 14px; }}
  .btns a, .btns button {{ flex:1; text-align:center; padding:11px 8px; border:none;
      border-radius:8px; font-size:.95rem; font-weight:600; cursor:pointer;
      text-decoration:none; }}
  .copy {{ background:#f0f0f0; color:#222; }}
  .copy.done {{ background:#cfe9d6; }}
  .wa {{ background:#25d366; color:#fff; }}
  footer {{ text-align:center; font-size:.78rem; color:#666; padding:10px 0 24px; }}
</style>
</head>
<body>
<header>
  <h1>🌾 Agromanch Daily Alert</h1>
  <p>{date_line} &nbsp;|&nbsp; हर message को Copy करें या सीधे WhatsApp पर भेजें</p>
</header>
<main>
{cards}
</main>
<footer>Auto-generated daily &middot; Agromanch Pvt Ltd &middot; भाव स्रोत: Agmarknet (data.gov.in) + स्थानीय जानकारी</footer>
<script>
function copyMsg(btn, id) {{
  const text = document.getElementById(id).innerText;
  navigator.clipboard.writeText(text).then(() => {{
    btn.textContent = "✅ Copy हो गया";
    btn.classList.add("done");
    setTimeout(() => {{ btn.textContent = "📋 Copy message"; btn.classList.remove("done"); }}, 2000);
  }}).catch(() => {{
    // पुराने browser के लिए fallback
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta); ta.select();
    document.execCommand("copy"); document.body.removeChild(ta);
    btn.textContent = "✅ Copy हो गया";
  }});
}}
</script>
</body>
</html>
"""

CARD_TEMPLATE = """<div class="card">
  <h2>📍 {district_hindi} ({district_en})</h2>
  <pre class="msg" id="msg-{idx}">{message_html}</pre>
  <div class="btns">
    <button class="copy" onclick="copyMsg(this,'msg-{idx}')">📋 Copy message</button>
    <a class="wa" href="https://wa.me/?text={message_encoded}" target="_blank" rel="noopener">🟢 WhatsApp पर भेजें</a>
  </div>
</div>"""


def build_html(messages, today):
    """messages = [(district_dict, message_text), ...] → पूरा HTML page."""
    cards = []
    for idx, (district, message) in enumerate(messages):
        cards.append(CARD_TEMPLATE.format(
            idx=idx,
            district_hindi=district["hindi"],
            district_en=district["name"],
            message_html=html.escape(message),
            message_encoded=urllib.parse.quote(message),
        ))
    return PAGE_TEMPLATE.format(date_line=hindi_date(today), cards="\n".join(cards))


def build_json(messages, rates_all, weather_all, today):
    """record के लिए आज का सारा data एक JSON में।"""
    out = {"date": today.isoformat(), "districts": []}
    for district, message in messages:
        name = district["name"]
        crops = {}
        for key, rate in (rates_all.get(name) or {}).items():
            if rate:
                crops[key] = {"price": rate["price"], "date": rate["date"].isoformat(),
                              "source": rate["source"], "from": rate["from"]}
            else:
                crops[key] = None
        out["districts"].append({
            "name": name, "hindi": district["hindi"],
            "rates": crops, "weather": weather_all.get(name), "message": message,
        })
    return json.dumps(out, ensure_ascii=False, indent=2)
