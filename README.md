# Guardian.AI
### ज्ञानेन रक्षणम् — *"Protection through Knowledge"*

Guardian.AI is an AI-powered multi-domain screening platform built with **Streamlit**, combining custom-trained TensorFlow models with **Google Gemini** for image validation, condition detection, and natural-language health/agriculture reports.

---

## Features

- **4 Screening Modules**
  - 🦷 Oral Health Scanner
  - 🩺 Skin Disease Scanner
  - 🌾 Crop Disease Scanner
  - 🐍 Reptile Scanner (species identification)
- **💬 Guardian Chatbot** — ask follow-up questions about oral, skin, crop, or reptile topics
- **Image-aware chat continuity** — carry a scanned image straight into the chatbot with one click to keep discussing the same result
- **Single-call Gemini analysis** — validation, detection, and report generation combined into one API call per scan (quota-efficient)
- **Offline fallback mode** — if Gemini is unavailable or quota-exhausted, the app automatically switches to local TensorFlow models with a built-in knowledge-base report generator, so the app keeps working without internet AI access
- **Per-module adaptive confidence thresholds** — tuned per model based on class count (binary vs. 9-class vs. 44-class vs. 82-class)
- **Domain-aware risk scoring** — healthy results score low risk, disease/condition results scale risk by confidence and severity
- **Camera or file upload** — supports JPG, PNG, WEBP, BMP, TIFF, HEIC/HEIF
- **Quota reset countdown** — displays the next Gemini quota reset time (Pacific Time) when temporarily disabled

---

## Tech Stack

- **Frontend/App:** Streamlit
- **ML Models:** TensorFlow / Keras (`.h5` models, per-module)
- **AI Reasoning:** Google Gemini (`gemini-1.5-flash`)
- **Image Handling:** Pillow, pillow-heif (HEIC support)
- **Language:** Python

---

## Project Structure

```
Guardian.AI/
├── Main.py                  # Streamlit application
├── requirements.txt         # Python dependencies
├── oral_model.h5             # Oral health classification model
├── oral_labels.json
├── skin_model.h5              # Skin condition classification model
├── skin_labels.json
├── crop_model.h5               # Crop disease classification model
├── crop_labels.json
├── reptile_model.h5             # Reptile species identification model
├── reptile_labels.json
└── .streamlit/
    └── secrets.toml          # Gemini API key (NOT committed — see Setup)
```

---

## Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/vsicsishansinghbhadoria106-a11y/Guardian.AI.git
cd Guardian.AI
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add your Gemini API key
Create a file at `.streamlit/secrets.toml` (this file is git-ignored and never uploaded):
```toml
GEMINI_API_KEY = "your-api-key-here"
```
Get a free key at [Google AI Studio](https://aistudio.google.com/).

> ⚠️ Never commit `secrets.toml` to GitHub — it contains your private API key.

### 4. Run the app
```bash
streamlit run Main.py
```

---

## How It Works

1. Select a scanner module from the sidebar, upload or capture an image.
2. The app sends the image to Gemini in a single combined call: validates it belongs to the selected domain, detects the condition/species, computes a risk score, and writes a short report.
3. If Gemini is unavailable (offline / quota exhausted), the app falls back to the local TensorFlow model for prediction and generates an offline report using a built-in condition knowledge base.
4. Click **"💬 Discuss this in Chatbot"** on any result to continue the conversation about that specific image and finding.

---

## Disclaimer

Guardian.AI is an **AI-powered educational screening tool** and is **not a diagnostic or medical/agricultural authority**. All results should be verified by a qualified professional — a dentist, dermatologist, agricultural extension officer, or certified herpetologist as relevant to the module used.

---

## Team

**Team — The Boys**
