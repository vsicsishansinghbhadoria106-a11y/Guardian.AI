================================================================
 GUARDIAN.AI
 Tagline: ज्ञानेन रक्षणम् (Protection through Knowledge)
 Team: The Boys
================================================================

OVERVIEW
--------
Guardian.AI is a Streamlit-based multi-purpose AI screening platform.
It uses a combination of Google Gemini (for image validation and
conversational Q&A) and custom TensorFlow/Keras models (for the actual
risk classification) to provide quick, educational, preliminary
screenings across four domains:

  - Oral Health Scanner   (teeth, gums, mouth, tongue)
  - Skin Disease Scanner  (skin lesions / conditions)
  - Crop Disease Scanner  (leaves, stems, fruit, plant disease)
  - Reptile Scanner       (snake identification)

It also includes a Guardian Chatbot for general educational questions
on the above topics.

IMPORTANT DISCLAIMER
---------------------
Guardian.AI is an educational AI-powered screening tool. It is NOT a
diagnostic system and does NOT replace a qualified doctor, dentist,
dermatologist, veterinarian, or agricultural expert. Always consult a
professional for any real health, plant, or animal-related concern.

HOW IT WORKS
------------
1. User selects a scanner from the sidebar.
2. User uploads an image (or captures one via camera).
3. Gemini first validates that the image actually matches the selected
   scanner's domain (e.g. rejects a photo of a car for "Skin Disease
   Scanner").
4. If valid, the image is resized and passed to the relevant local
   Keras (.h5) model, which returns a predicted label and confidence
   score.
5. Results are shown with a risk score, risk level (Low/Moderate/High),
   findings, and recommendations.
6. The Guardian Chatbot tab allows free-form educational questions,
   answered by Gemini under strict "no diagnosis" rules.

PROJECT STRUCTURE
------------------
app.py                  Main Streamlit application (UI + logic)
guardian_logo.png       App logo (bonsai tree), shown on landing page & sidebar
superhero.gif           Decorative corner animation on landing page
bons_ai_logo_icon_*.ico Browser tab icon

oral_model.h5 / oral_labels.json
skin_model.h5 / skin_labels.json
crop_model.h5 / crop_labels.json
reptile_model.h5 / reptile_labels.json
   -> Trained Keras classification models + their label lists.
      Each scanner falls back to "Model not available" gracefully if
      its .h5/.json file is missing.

.streamlit/secrets.toml
   -> Stores GEMINI_API_KEY (see SETUP below). Not committed to git.

REQUIREMENTS
-------------
Python 3.10+ recommended.

Install dependencies:
    pip install streamlit tensorflow pillow numpy google-generativeai

SETUP
------
1. Place all model files (.h5) and label files (.json) in the same
   folder as app.py (or update the paths in the MODELS dict inside
   app.py).

2. Create a secrets file at:
       .streamlit/secrets.toml
   with the following content:
       GEMINI_API_KEY = "your_gemini_api_key_here"

3. Place guardian_logo.png and superhero.gif in the project root if
   you want the logo/decoration to appear (the app still runs fine
   without them, just without those visuals).

RUNNING THE APP
-----------------
From the project folder, run:
    streamlit run app.py

Then open the printed local URL (usually http://localhost:8501) in
your browser. Always check the terminal for the actual port in case
8501 is already in use.

THEME / UI NOTES
------------------
The app uses a custom "Elegant Dark Teal & Gold" theme:
  - Fonts: Cinzel (titles), Cormorant Garamond (taglines/body accents)
  - Colors: deep teal background, gold (#D4AF37) accents
  - A decorative SVG wave/leaf texture sits behind the gradient
  - Chatbot bubbles: user messages in bold black-on-cream, AI replies
    in bold white-on-gold-teal gradient

All styling is done via custom CSS injected through st.markdown(...,
unsafe_allow_html=True) - no external JS frameworks are used.

KNOWN LIMITATIONS
-------------------
- If a model (.h5) or labels (.json) file is missing, that scanner
  will still run but report "Model not available".
- Gemini-based image validation requires a valid GEMINI_API_KEY and
  an active internet connection.
- This tool is for educational/demo purposes only and has not been
  clinically validated.

CREDITS
--------
Built by: The Boys
