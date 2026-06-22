import streamlit as st
from PIL import Image
import tensorflow as tf
import numpy as np
import json
import os
import google.generativeai as genai
import base64
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.api_core.exceptions import ResourceExhausted

# ── HEIC support ──────────────────────────────────────────────────────────────
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# ── Gemini init (guarded) ─────────────────────────────────────────────────────
gemini_model = None
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    GEMINI_OK = True
except Exception:
    GEMINI_OK = False

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Guardian.AI",
    page_icon="bons_ai_logo_icon_168500.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Session state ─────────────────────────────────────────────────────────────
if "entered" not in st.session_state:
    st.session_state.entered = False
if "gemini_quota_exhausted" not in st.session_state:
    st.session_state.gemini_quota_exhausted = False
if "carry_image" not in st.session_state:
    st.session_state.carry_image = None
if "carry_context" not in st.session_state:
    st.session_state.carry_context = None
if "carry_consumed" not in st.session_state:
    st.session_state.carry_consumed = False
if "quota_exhausted_at" not in st.session_state:
    st.session_state.quota_exhausted_at = None

def mark_quota_exhausted():
    st.session_state.gemini_quota_exhausted = True
    if st.session_state.quota_exhausted_at is None:
        st.session_state.quota_exhausted_at = datetime.now(ZoneInfo("America/Los_Angeles"))

def gemini_available():
    return GEMINI_OK and not st.session_state.gemini_quota_exhausted and gemini_model is not None

def quota_reset_message():
    """
    Gemini free-tier daily quota resets at midnight Pacific Time.
    Returns a human-readable string with the exact reset time and countdown.
    """
    now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
    next_midnight = (now_pt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    remaining = next_midnight - now_pt
    hours, rem = divmod(int(remaining.total_seconds()), 3600)
    minutes = rem // 60
    return f"Resets at 12:00 AM Pacific Time — about {hours}h {minutes}m from now."

if not GEMINI_OK:
    st.warning("⚠️ Gemini unavailable. Running in offline mode.")
elif st.session_state.gemini_quota_exhausted:
    st.warning(f"⚠️ Gemini API quota exhausted. AI features temporarily disabled. {quota_reset_message()}")

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def render_chat_bubble(role, content):
    if role == "user":
        st.markdown(f'<div style="background:#F5EFE0;color:#000000;font-weight:700;padding:12px 18px;border-radius:16px 16px 4px 16px;margin:8px 0 8px auto;max-width:75%;text-align:right;box-shadow:0 2px 10px rgba(0,0,0,0.3);">{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background:linear-gradient(135deg,#0B2B30,#D4AF37);color:#FFFFFF;font-weight:700;padding:12px 18px;border-radius:16px 16px 16px 4px;margin:8px auto 8px 0;max-width:75%;text-align:left;box-shadow:0 2px 10px rgba(0,0,0,0.3);">{content}</div>', unsafe_allow_html=True)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&display=swap');
:root {
    --gold: #D4AF37; --gold-light: #F0D88C;
    --teal-dark: #04181C; --teal-mid: #0B2B30;
    --teal-light: #103B40; --cream: #F5EFE0;
}
.stApp { background: linear-gradient(135deg, var(--teal-dark) 0%, var(--teal-mid) 45%, var(--teal-light) 75%, var(--teal-dark) 100%); color: var(--cream); }
h1,h2,h3 { font-family:'Cinzel',serif !important; color:var(--cream) !important; }
.main-title { font-family:'Cinzel',serif; text-align:center; font-size:4.8rem; font-weight:700; color:var(--cream); margin-bottom:0; letter-spacing:2px; text-shadow:0 0 25px rgba(212,175,55,0.35); }
.tagline { font-family:'Cormorant Garamond',serif; text-align:center; font-size:1.9rem; font-weight:600; color:var(--gold); letter-spacing:3px; margin-top:-10px; }
.section-card { background:rgba(11,43,48,0.85); border:1px solid var(--gold); border-radius:20px; padding:25px; margin-top:20px; box-shadow:0 0 25px rgba(212,175,55,0.08); }
div.stButton>button { background:rgba(11,43,48,0.6) !important; color:var(--gold) !important; font-family:'Cinzel',serif !important; font-weight:700 !important; letter-spacing:1px; border-radius:30px !important; border:1.5px solid var(--gold) !important; }
div.stButton>button:hover { background:rgba(212,175,55,0.15) !important; box-shadow:0 0 18px rgba(212,175,55,0.45); color:var(--gold-light) !important; }
[data-testid="stSidebar"] { background-color:var(--teal-dark); border-right:1px solid rgba(212,175,55,0.25); }
[data-testid="stSidebar"] * { color:var(--cream) !important; }
[data-testid="stSidebar"] [data-baseweb="select"] * { color:#04181C !important; }
[data-baseweb="select"] { border:1px solid rgba(212,175,55,0.5) !important; border-radius:10px !important; }
[data-testid="stAlert"] { background-color:rgba(212,175,55,0.08) !important; border:1px solid rgba(212,175,55,0.35) !important; color:var(--cream) !important; border-radius:12px !important; }
button[data-baseweb="tab"] p, button[data-baseweb="tab"] { color:#000000 !important; font-weight:400 !important; font-size:1rem !important; }
.stFileUploader label, [data-testid="stFileUploaderLabel"], [data-testid="stFileUploader"] label { color:#000000 !important; }
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] span { color:#000000 !important; }
[data-testid="stFileUploader"] * { color:#000000 !important; font-weight:400 !important; }
</style>
""", unsafe_allow_html=True)

# ── Model config ──────────────────────────────────────────────────────────────
MODELS = {
    "🦷 Oral Health Scanner":  {"model": "oral_model.h5",    "labels": "oral_labels.json",    "size": (224,224), "defaults": ["Oral Cancer","Normal"]},
    "🩺 Skin Disease Scanner": {"model": "skin_model.h5",    "labels": "skin_labels.json",    "size": (224,224), "defaults": ["Unknown Condition","Normal Skin"]},
    "🌾 Crop Disease Scanner": {"model": "crop_model.h5",    "labels": "crop_labels.json",    "size": (224,224), "defaults": ["Unknown Disease","Healthy Crop"]},
    "🐍 Reptile Scanner":      {"model": "reptile_model.h5", "labels": "reptile_labels.json", "size": (224,224), "defaults": ["Unknown Reptile","Non-Reptile"]},
}

# Per-module confidence thresholds.
# A 44-class model (crop) or 82-class model (reptile) naturally has lower per-class
# probabilities than a binary model. Using 0.60 across the board rejects valid images.
CONFIDENCE_THRESHOLDS = {
    "🦷 Oral Health Scanner":  0.45,  # binary — was 0.55, rejected valid 53% cases
    "🩺 Skin Disease Scanner": 0.35,  # 9 classes
    "🌾 Crop Disease Scanner": 0.28,  # 44 classes — random chance ~2.3%
    "🐍 Reptile Scanner":      0.22,  # 82 classes — random chance ~1.2%
}

VALIDATE_PROMPTS = {
    "🦷 Oral Health Scanner":  "Does this image clearly show a human mouth, teeth, gums, tongue, or oral cavity? Reply only YES or NO.",
    "🩺 Skin Disease Scanner": "Does this image clearly show human skin or a skin lesion? Reply only YES or NO.",
    "🌾 Crop Disease Scanner": "Does this image clearly show a crop, plant leaf, fruit, stem, or agricultural disease? Reply only YES or NO.",
    "🐍 Reptile Scanner":      "Does this image clearly show a snake or reptile? Reply only YES or NO.",
}

DOMAIN_CONTEXT = {
    "🦷 Oral Health Scanner":  "oral health, teeth, gums, mouth conditions",
    "🩺 Skin Disease Scanner": "skin conditions, dermatology, skin diseases",
    "🌾 Crop Disease Scanner": "crop diseases, plant health, agricultural conditions",
    "🐍 Reptile Scanner":      "reptile species identification, snake identification",
}

# Keywords that indicate a healthy/normal prediction
HEALTHY_KEYWORDS = {"healthy", "normal", "non-reptile", "non reptile"}

# ── Single combined Gemini call (validate + detect + report) ──────────────────
def gemini_full_analysis(image, module):
    """
    One Gemini call instead of three (validate, then report, then sometimes
    chatbot). Saves quota. Returns dict(valid, result, risk, level, report)
    or None if Gemini is unavailable / call fails — caller should fall back
    to the local TF model + offline report in that case.
    """
    if not gemini_available():
        return None

    domain = DOMAIN_CONTEXT[module]
    prompt = f"""You are Guardian.AI, an educational screening assistant for {domain}.

Look at the image and reply with ONLY raw JSON, no markdown fences:
{{"valid": true/false, "condition": "specific name", "risk": 0-100, "findings": "2-3 sentences", "recommendations": "2-3 short actionable steps separated by ' | '"}}

Rules:
- valid=false if the image does not show {domain}.
- risk: healthy/normal → 0-30. Reptile ID → confidence-based 0-100. Disease/condition → 40-100 by severity.
- Never diagnose. Always recommend a qualified professional. Be specific, not generic."""

    try:
        response = gemini_model.generate_content([prompt, image])
        text = response.text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())

        risk = max(0, min(100, int(data.get("risk", 50))))
        level = "Low" if risk <= 30 else "Moderate" if risk <= 70 else "High"
        recs = [r.strip() for r in str(data.get("recommendations", "")).split("|") if r.strip()]
        recs_md = "\n".join(f"• {r}" for r in recs)
        report = f"**Findings:** {data.get('findings','')}\n\n**Recommendations:**\n{recs_md}"

        return {
            "valid": bool(data.get("valid", True)),
            "result": data.get("condition", "Unknown"),
            "risk": risk,
            "level": level,
            "report": report,
        }

    except ResourceExhausted:
        mark_quota_exhausted()
        return None
    except Exception:
        return None

# ── Load model ────────────────────────────────────────────────────────────────
@st.cache_resource
def load_model_and_labels(model_path, labels_path, defaults):
    model, labels = None, defaults
    try:
        if os.path.exists(model_path):
            model = tf.keras.models.load_model(model_path, compile=False)
        if os.path.exists(labels_path):
            with open(labels_path) as f:
                loaded = json.load(f)
                labels = loaded if loaded else defaults
    except Exception as e:
        st.warning(f"Could not load {model_path}: {e}")
    return model, labels

# ── Risk score ────────────────────────────────────────────────────────────────
def compute_risk_score(result, confidence, module):
    """
    Map model confidence to a meaningful risk score.

    Problem with the original `risk = confidence * 100`:
      - A healthy class with 90% confidence gets risk=90 — semantically wrong.
      - A disease class with 90% confidence should be high risk.

    Fix:
      - Reptile scanner: pure ID task → confidence = certainty of identification.
      - Healthy/normal class: high confidence = LOW risk. Risk = (1-confidence)*50
        so a 95%-confident "healthy" gives risk ≈ 2/100.
      - Disease class: high confidence = HIGH risk. Risk mapped to 40–100 range
        so even a moderate 50% disease confidence registers as meaningful risk.
    """
    result_lower = result.lower()
    is_healthy = any(kw in result_lower for kw in HEALTHY_KEYWORDS)

    if "🐍 Reptile Scanner" in module:
        return round(confidence * 100)

    if is_healthy:
        return max(5, round((1.0 - confidence) * 50))

    # Disease detected: scale confidence into 40–100 range
    return round(40 + confidence * 60)

# ── Image validation ──────────────────────────────────────────────────────────
def validate_image(image, module):
    """
    Validate that the uploaded image matches the selected scanner domain.
    Uses Gemini when available; falls back silently when quota is exhausted
    or Gemini is offline (model-confidence threshold acts as secondary guard).
    """
    if not gemini_available():
        # Fallback: no pre-model validation; model confidence threshold will
        # reject out-of-domain images after inference.
        return True

    try:
        response = gemini_model.generate_content([VALIDATE_PROMPTS[module], image])

        if not response.candidates:
            return True
        if not response.candidates[0].content.parts:
            return True

        return "YES" in response.text.upper()

    except ResourceExhausted:
        st.warning(f"⚠️ Gemini quota reached. Skipping image validation. {quota_reset_message()}")
        mark_quota_exhausted()
        return True

    except Exception:
        return True

# ── AI report ─────────────────────────────────────────────────────────────────
# Lightweight offline knowledge base — used by _fallback_report when Gemini
# is unavailable, so reports stay specific instead of generic boilerplate.
CONDITION_INFO = {
    "oral cancer":  "a lesion pattern associated with oral cancer screening — typically a persistent ulcer, white/red patch, or lump that does not heal within 2 weeks.",
    "leukoplakia":  "a white patch on the oral mucosa, often linked to chronic irritation or tobacco/areca-nut use.",
    "gingivitis":   "gum inflammation usually caused by plaque buildup — generally reversible with improved oral hygiene.",
    "melanoma":     "a pigmented lesion pattern that can indicate melanoma — irregular borders, color variation, or asymmetry are key warning signs.",
    "eczema":       "a skin inflammation pattern — typically dry, itchy, red patches that flare with irritants or allergens.",
    "psoriasis":    "a chronic immune-related skin condition causing scaly, red, well-defined patches, often on elbows, knees, or scalp.",
    "acne":         "a common skin condition from clogged pores and inflammation, often hormonal or bacterial in origin.",
    "scab":         "a fungal disease causing dark, scabby, corky lesions on leaves and fruit — common in apple and pear crops.",
    "blight":       "a fast-spreading fungal/bacterial disease causing browning, wilting, and tissue death in leaves and stems.",
    "rust":         "a fungal disease producing orange-to-brown pustules on leaf surfaces, spreading via spores.",
    "mosaic":       "a viral disease causing mottled, discolored, mosaic-like patterns on leaves and stunted growth.",
    "rot":          "a fungal or bacterial disease causing soft or dry decay of plant tissue, often starting at wounds or soil contact.",
    "mildew":       "a fungal disease leaving a white-to-grey powdery coating on leaf surfaces, thriving in humid conditions.",
    "spot":         "a fungal/bacterial leaf-spot disease, appearing as small discolored lesions that can merge and cause leaf drop.",
}

def _condition_blurb(result_lower):
    for keyword, blurb in CONDITION_INFO.items():
        if keyword in result_lower:
            return blurb
    return None

def _fallback_report(result, risk, level, module):
    """Generate a meaningful condition-specific report without Gemini."""
    result_lower = result.lower()
    is_healthy = any(kw in result_lower for kw in HEALTHY_KEYWORDS)
    # Clean up label for display (e.g. "Tomato___Late_blight" → "Tomato — Late Blight")
    display = result.replace("___", " — ").replace("_", " ").title()
    blurb = _condition_blurb(result_lower)

    if "🐍 Reptile Scanner" in module:
        findings = (
            f"The identification model recognized this specimen as **{display}** "
            f"with **{risk}%** confidence ({level} certainty). "
            f"Snake and reptile identification should always be verified by a certified herpetologist "
            f"before any handling attempt."
        )
        recs = [
            "Do not handle any snake or reptile without proper protective equipment and expert guidance.",
            "If this is a venomous species, keep a safe distance and contact local wildlife authorities.",
            "In case of a bite from an unidentified snake, seek emergency medical care immediately.",
        ]

    elif is_healthy:
        findings = (
            f"The Guardian.AI screening model analyzed the image and found indicators "
            f"consistent with **{display}** — no significant abnormality was detected. "
            f"Risk score: **{risk}/100** ({level})."
        )
        recs = [
            "Continue regular check-ups with the appropriate specialist as a preventive measure.",
            "Maintain good health or agricultural hygiene practices for the relevant domain.",
            "Consult a qualified professional if you notice any changes or have concerns.",
        ]

    else:
        # Disease / condition detected
        if "🦷 Oral" in module:
            domain_tip = "Schedule an urgent appointment with a dentist or oral surgeon."
        elif "🩺 Skin" in module:
            domain_tip = "Seek a dermatological evaluation promptly, especially if the area is growing or changing."
        elif "🌾 Crop" in module:
            domain_tip = "Consult an agricultural extension officer or plant pathologist for treatment options."
        else:
            domain_tip = "Consult the relevant qualified professional for evaluation."

        about = f" Typically, this refers to {blurb}" if blurb else ""
        findings = (
            f"The Guardian.AI screening model detected indicators consistent with "
            f"**{display}** — Risk score: **{risk}/100** ({level} risk).{about} "
            f"This result warrants attention and professional evaluation."
        )
        recs = [
            domain_tip,
            "Do not self-treat based on this AI screening result alone — it is not a clinical diagnosis.",
            "Bring this result to your professional appointment as supporting screening information.",
        ]

    recs_md = "\n".join(f"• {r}" for r in recs)
    return f"**Findings:** {findings}\n\n**Recommendations:**\n{recs_md}"


def get_ai_report(image, module, result, risk, level):
    domain = DOMAIN_CONTEXT[module]
    prompt = f"""You are Guardian.AI, an educational screening assistant specializing in {domain}.

An AI model analyzed an image and produced:
- Detected condition: {result}
- Risk score: {risk}/100
- Risk level: {level}

Based on this specific result, provide a short educational report with two sections:
**Findings:** 2-3 sentences describing what this condition typically looks like and means.
**Recommendations:** 2-3 actionable steps the user should take.

Do NOT diagnose. Do NOT replace professional advice. Be specific to "{result}", not generic.
Keep it under 150 words total."""

    if not gemini_available():
        return _fallback_report(result, risk, level, module)

    try:
        response = gemini_model.generate_content([prompt, image])
        return response.text

    except ResourceExhausted:
        mark_quota_exhausted()
        st.warning(f"⚠️ Gemini quota reached. Using offline report. {quota_reset_message()}")
        return _fallback_report(result, risk, level, module)

    except Exception:
        return _fallback_report(result, risk, level, module)

# ── Landing page ──────────────────────────────────────────────────────────────
if not st.session_state.entered:
    st.markdown("""
    <style>
    .block-container{padding-top:1rem !important;}
    .landing-container{min-height:70vh;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;}
    .landing-container img.logo{width:180px;display:block;margin:0 auto 10px auto;}
    .main-title{font-family:'Cinzel',serif;font-size:3.6rem;font-weight:700;color:#F5EFE0;margin:0;letter-spacing:2px;text-shadow:0 0 25px rgba(212,175,55,0.35);}
    .tagline{font-family:'Cormorant Garamond',serif;font-size:1.5rem;font-weight:600;color:#D4AF37;letter-spacing:3px;margin:8px 0 0 0;}
    .tagline::before,.tagline::after{content:"❖";color:#D4AF37;margin:0 14px;font-size:1rem;opacity:0.8;}
    div.stButton{display:flex;justify-content:center;margin-top:16px;}
    div.stButton>button{width:240px;height:56px;font-family:'Cinzel',serif;font-size:1.2rem;font-weight:700;}
    .corner-credit{position:fixed;right:20px;bottom:20px;z-index:999;display:flex;flex-direction:column;align-items:center;gap:6px;}
    .corner-credit .byline-corner{font-family:'Cinzel',serif;font-size:1rem;letter-spacing:2px;color:#D4AF37;text-shadow:0 0 8px rgba(212,175,55,0.5);}
    .corner-credit img.corner-gif{width:90px;opacity:0.9;}
    </style>
    """, unsafe_allow_html=True)

    logo_html = ""
    if os.path.exists("guardian_logo.png"):
        logo_b64 = get_base64("guardian_logo.png")
        logo_html = f'<img class="logo" src="data:image/png;base64,{logo_b64}">'

    st.markdown(f"""
    <div class="landing-container">
        {logo_html}
        <div class="main-title">Guardian.AI</div>
        <div class="tagline">ज्ञानेन रक्षणम्</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("Enter", use_container_width=True):
            st.session_state.entered = True
            st.rerun()

    gif_html = ""
    if os.path.exists("superhero.gif"):
        gif_b64 = get_base64("superhero.gif")
        gif_html = f'<img class="corner-gif" src="data:image/gif;base64,{gif_b64}">'

    st.markdown(f'<div class="corner-credit"><div class="byline-corner">Team :- The Boys</div>{gif_html}</div>', unsafe_allow_html=True)

# ── Dashboard ─────────────────────────────────────────────────────────────────
else:
    if os.path.exists("guardian_logo.png"):
        st.sidebar.image("guardian_logo.png", width=150)

    st.sidebar.markdown("## Guardian.AI\n### ज्ञानेन रक्षणम्")

    module = st.sidebar.selectbox("Select Scanner", list(MODELS.keys()) + ["💬 Guardian Chatbot"], key="module_select")

    st.title(module)

    # ── Chatbot ───────────────────────────────────────────────────────────────
    if module == "💬 Guardian Chatbot":
        if not gemini_available():
            if st.session_state.gemini_quota_exhausted:
                st.error(f"💬 Guardian Chatbot is currently offline — Gemini API quota exhausted. {quota_reset_message()}")
            else:
                st.error("💬 Guardian Chatbot is currently offline — Gemini API unavailable. Please try again later.")
            st.stop()

        st.info("Guardian.AI provides educational information only and does not provide medical diagnoses.")

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # ── Carried-over image from a scanner ──────────────────────────────
        if st.session_state.carry_image is not None:
            col_img, col_btn = st.columns([4, 1])
            with col_img:
                st.image(st.session_state.carry_image, width=120, caption="Carried from scan")
            with col_btn:
                if st.button("✖ Remove image"):
                    st.session_state.carry_image = None
                    st.session_state.carry_context = None
                    st.session_state.carry_consumed = False
                    st.rerun()

            # Auto-send the scan context once, so the user doesn't have to retype it
            if not st.session_state.carry_consumed:
                ctx = st.session_state.carry_context
                st.session_state.chat_history.append({"role": "user", "content": ctx})
                with st.spinner("Thinking..."):
                    try:
                        response = gemini_model.generate_content([
                            f"""You are Guardian.AI, an educational screening assistant.
Rules: Never diagnose. Never replace a doctor/dentist/vet/agricultural expert. Educational and preventive info only. Encourage professional consultation.
{ctx}""",
                            st.session_state.carry_image,
                        ])
                        answer = response.text
                    except ResourceExhausted:
                        mark_quota_exhausted()
                        answer = f"⚠️ The AI quota has been reached. The chatbot will be unavailable until the quota resets. {quota_reset_message()} Please consult a qualified professional for any urgent concerns."
                    except Exception:
                        answer = "Sorry, I couldn't process this right now. Please try again later."

                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                st.session_state.carry_consumed = True

        for message in st.session_state.chat_history:
            render_chat_bubble(message["role"], message["content"])

        user_prompt = st.chat_input("Ask about oral health, skin conditions, crop diseases, or snakes...")

        if user_prompt:
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            render_chat_bubble("user", user_prompt)

            with st.spinner("Thinking..."):
                try:
                    base_text = f"""
You are Guardian.AI, an educational screening assistant.
Rules: Never diagnose. Never replace a doctor/dentist/vet/agricultural expert. Educational and preventive info only. Encourage professional consultation.
User question: {user_prompt}"""

                    # Keep referencing the carried image for follow-up questions
                    if st.session_state.carry_image is not None:
                        response = gemini_model.generate_content([base_text, st.session_state.carry_image])
                    else:
                        response = gemini_model.generate_content(base_text)

                    answer = response.text

                except ResourceExhausted:
                    mark_quota_exhausted()
                    answer = f"⚠️ The AI quota has been reached. The chatbot will be unavailable until the quota resets. {quota_reset_message()} Please consult a qualified professional for any urgent concerns."

                except Exception as e:
                    answer = f"Sorry, I couldn't process your question right now. Please try again later."

            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            render_chat_bubble("assistant", answer)

    # ── Scanners ──────────────────────────────────────────────────────────────
    else:
        model_data = MODELS[module]
        model, labels = load_model_and_labels(
            model_data["model"], model_data["labels"], model_data["defaults"]
        )

        if model is None:
            st.error(f"⚠️ Model file `{model_data['model']}` not found. Place it in the app directory.")

        tab1, tab2 = st.tabs(["📁 Upload Image", "📷 Camera"])
        uploaded_file = None

        with tab1:
            file_from_upload = st.file_uploader(
                "Upload Image",
                type=["jpg","jpeg","png","webp","bmp","gif","tiff","tif","jfif","heic","heif"],
                key=f"upload_{module}"
            )

        with tab2:
            camera_file = st.camera_input("Capture Image", key=f"camera_{module}")

        if camera_file:
            uploaded_file = camera_file
        elif file_from_upload:
            uploaded_file = file_from_upload

        if uploaded_file:
            try:
                image = Image.open(uploaded_file)
            except Exception as e:
                st.error(f"Could not open image: {e}. If uploading HEIC, ensure `pillow-heif` is installed.")
                st.stop()

            st.image(image, width=350)

            if st.button("Analyze", use_container_width=True):

                with st.spinner("Analyzing..."):
                    # Try the single combined Gemini call first (1 call instead
                    # of 3 — validation + detection + report together).
                    gemini_result = gemini_full_analysis(image, module)

                    if gemini_result is not None:
                        if not gemini_result["valid"]:
                            st.error("❌ Please upload a valid image for the selected scanner.")
                            st.stop()
                        result = gemini_result["result"]
                        risk = gemini_result["risk"]
                        level = gemini_result["level"]
                        ai_report = gemini_result["report"]

                    else:
                        # Fallback: Gemini unavailable/quota exhausted — use the
                        # local TF model + offline report instead.
                        if not validate_image(image, module):
                            st.error("❌ Please upload a valid image for the selected scanner.")
                            st.stop()

                        if model is not None:
                            try:
                                img = image.convert("RGB").resize(model_data["size"])
                                arr = np.expand_dims(np.array(img, dtype=np.float32) / 255.0, axis=0)
                                pred = model.predict(arr, verbose=0)
                                idx = int(np.argmax(pred[0]))
                                confidence = float(pred[0][idx])

                                # Adaptive threshold: reject out-of-domain images.
                                # Threshold is lower for many-class models because
                                # expected per-class probability is much smaller.
                                threshold = CONFIDENCE_THRESHOLDS.get(module, 0.35)
                                if confidence < threshold:
                                    st.error(
                                        f"❌ This image does not appear to belong to the selected scanner "
                                        f"or is too unclear to analyze. "
                                        f"(Max confidence {confidence:.1%} < {threshold:.0%} threshold)"
                                    )
                                    st.stop()

                                if labels and idx < len(labels):
                                    result = labels[idx]
                                else:
                                    result = f"Class {idx}"

                                # Risk score is domain-aware, not raw confidence.
                                risk = compute_risk_score(result, confidence, module)

                            except Exception as e:
                                st.error(f"Model prediction failed: {e}")
                                st.stop()
                        else:
                            result = "Model not available — place model file in app directory"
                            risk = 0

                        level = "Low" if risk <= 30 else "Moderate" if risk <= 70 else "High"
                        ai_report = get_ai_report(image, module, result, risk, level)

                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.subheader(f"🔍 {result}")
                st.metric("Risk Score", f"{risk}/100")
                st.write(f"**Risk Level:** {level}")
                st.markdown(ai_report)
                st.info("Guardian.AI is an AI-powered screening platform and not a diagnostic system. Always consult a qualified professional.")
                st.markdown('</div>', unsafe_allow_html=True)

                if st.button("💬 Discuss this in Chatbot", use_container_width=True):
                    st.session_state.carry_image = image
                    st.session_state.carry_context = (
                        f"I scanned an image using the {module}. "
                        f"Result: {result} — Risk {risk}/100 ({level} risk). "
                        f"I'd like to discuss this further."
                    )
                    st.session_state.carry_consumed = False
                    st.session_state.module_select = "💬 Guardian Chatbot"
                    st.rerun()