# 🌾 Agromanch Daily Alert

रोज़ सुबह 6 बजे **मंडी भाव + मौसम** के Hindi WhatsApp messages अपने आप तैयार
हो जाते हैं — Ballia, Mau, Deoria, Ghazipur, Azamgarh के लिए।

**यह system खुद कोई message नहीं भेजता** (WhatsApp number ban का खतरा zero)।
यह एक web page बनाता है जिसमें हर ज़िले का message तैयार रहता है —
आप **Copy** करें या **WhatsApp button** दबाएँ, group चुनें, और send करें। बस।

सब कुछ **free** है — कोई server नहीं, कोई paid service नहीं।

---

## एक बार का setup (One-time setup)

### Step 1 — Free API key लें (data.gov.in)

मंडी भाव सरकारी Agmarknet data से आते हैं। इसके लिए free key चाहिए:

1. https://data.gov.in पर जाएँ → **Sign Up** (free है)
2. Login करके अपनी **Profile / My Account** में जाएँ
3. वहाँ आपकी **API Key** दिखेगी — उसे copy कर लें

> Laptop पर test करने के लिए: `daily_alert/config.json` खोलें और
> `"data_gov_api_key"` में `YAHAN_APNI_DATA_GOV_KEY_DALEIN` की जगह अपनी key paste करें।
> ⚠️ अगर key config.json में डालकर GitHub पर push करेंगे तो key public हो जाएगी —
> GitHub के लिए Step 3 वाला secret तरीका इस्तेमाल करें और config में placeholder ही रहने दें।

### Step 2 — GitHub पर push करें

अगर repo पहले से GitHub पर है तो बस:

```
git add .
git commit -m "Add daily alert system"
git push
```

नया repo बनाना हो तो: https://github.com/new → repo बनाएँ → फिर:

```
git remote add origin https://github.com/APKA_USERNAME/REPO_NAAM.git
git push -u origin main
```

### Step 3 — GitHub पर API key (secret) डालें

ताकि GitHub Actions को key मिले, बिना public किए:

1. GitHub पर अपना repo खोलें
2. **Settings → Secrets and variables → Actions → New repository secret**
3. Name: `DATA_GOV_API_KEY`
4. Value: अपनी data.gov.in वाली key paste करें → **Add secret**

### Step 4 — GitHub Pages चालू करें

1. Repo में **Settings → Pages**
2. "Build and deployment" में Source: **Deploy from a branch**
3. Branch: `main`, Folder: **`/docs`** → **Save**
4. 1-2 मिनट में आपका page live हो जाएगा:
   `https://APKA_USERNAME.github.io/REPO_NAAM/`

📱 **इस link को phone के home screen पर save कर लें** — रोज़ यहीं से भेजना है।

### Step 5 — पहली बार हाथ से चलाकर देखें

1. Repo में **Actions** tab → "**Agromanch Daily Alert**" workflow
2. **Run workflow** button दबाएँ
3. 1-2 मिनट में page update हो जाएगा

---

## रोज़ का काम (सिर्फ 2 मिनट)

1. सुबह 6:05 बजे के बाद phone पर page खोलें
2. हर ज़िले के card में:
   - **📋 Copy message** → message copy, फिर WhatsApp में जाकर paste करें, **या**
   - **🟢 WhatsApp पर भेजें** → WhatsApp खुलेगा, message भरा होगा —
     group/contact चुनें और send दबाएँ
3. हो गया! 5 ज़िले = 5 tap.

> WhatsApp हर बार **आप** भेज रहे हैं, कोई bot नहीं — इसलिए number ban का
> कोई खतरा नहीं।

---

## अगर API से भाव न मिले (manual fallback)

Agmarknet कभी-कभी किसी ज़िले का data नहीं देता (छुट्टी, देरी आदि)। तब:

1. `daily_alert/manual_rates.csv` खोलें
2. आज की लाइन जोड़ें, जैसे:
   ```
   12-06-2026,Ballia,wheat,2300,रसड़ा मंडी फोन से
   ```
3. Commit + push करें, फिर Actions में workflow दोबारा चलाएँ
   (या अगली सुबह अपने आप ले लेगा, अगर तारीख ताज़ा है)

जो भाव कहीं से नहीं मिलता, वह message में **दिखता ही नहीं** — गलत/पुराना
data किसानों को कभी नहीं जाता।

---

## अपने हिसाब से बदलना (Customization)

सब कुछ `daily_alert/config.json` में है:

| क्या बदलना है | कहाँ |
|---|---|
| ज़िला जोड़ना/हटाना | `districts` list (lat/lon Google Maps से) |
| फसल जोड़ना/हटाना | `crops` list |
| बारिश/गर्मी की चेतावनी की सीमा | `weather` section |
| App link | `app_link` |
| भेजने का समय | `.github/workflows/daily_alert.yml` में `cron` line |

Laptop पर test: `pip install -r requirements.txt` फिर `python daily_alert/main.py`
→ `docs/index.html` browser में खोलकर देखें।

---

## Files का नक्शा

```
daily_alert/
├── config.json          ← settings (districts, crops, key)
├── manual_rates.csv     ← हाथ से भाव डालने की फाइल
├── fetch_mandi.py       ← Agmarknet API + manual merge
├── fetch_weather.py     ← Open-Meteo मौसम (free, no key)
├── generate_messages.py ← Hindi message + HTML page
└── main.py              ← सब चलाने वाली script
docs/index.html          ← रोज़ की page (GitHub Pages इसे दिखाता है)
.github/workflows/daily_alert.yml ← रोज़ 6:00 IST का scheduler
```
