
"""MatiMitra: Streamlit farming assistant with ML crop recommendations."""

import hashlib
import os
from datetime import datetime
from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from farm_assistant import (
    answer_question,
    available_ai_providers,
    speak_marathi,
    transcribe_marathi_audio,
)
from ml_engine import predict_crop
from sensor_simulator import initial_readings, next_readings
from soil_engine import analyze_soil, generate_soil_alerts

load_dotenv()

st.set_page_config(
    page_title="MatiMitra · Farm companion",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap');

    :root {
        --forest: #73d2a2;
        --forest-2: #8fe3ba;
        --lime: #d9f27e;
        --ink: #edf5f0;
        --muted: #a8b8b0;
        --paper: #0b1417;
        --line: #26383a;
        --orange: #ffad69;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Noto Sans Devanagari', sans-serif;
    }

    html { color-scheme: dark; }

    [data-testid="stAppViewContainer"] {
        background: radial-gradient(ellipse at 78% 0%, #142b2a 0%, transparent 34%), var(--paper);
        color: var(--ink);
    }

    [data-testid="stHeader"] { background: transparent; }

    .block-container {
        max-width: 1440px;
        padding-top: 1.6rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        font-family: 'Manrope', 'Noto Sans Devanagari', sans-serif;
        color: var(--ink);
        letter-spacing: -0.035em;
    }

    h2 { font-size: 1.45rem !important; }

    [data-testid="stSidebar"] {
        background: linear-gradient(175deg, #10241f 0%, #101d25 100%);
    }

    [data-testid="stSidebar"] * { color: #f1f7f6; }

    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #c7d9d5;
    }

    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        color: #edf5f0;
        background-color: #1a2a2b;
    }

    [data-testid="stSidebar"] [data-testid="stForm"] {
        border: 1px solid #304745;
        border-radius: 16px;
        padding: 1rem;
        background: rgba(255,255,255,.025);
    }

    [data-testid="stMetric"] {
        background: #121f23;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 1rem 1.15rem;
        box-shadow: 0 8px 22px rgba(0,0,0,.16);
    }

    [data-testid="stMetricLabel"] {
        color: #b5c4bd;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: #a8e8c2;
        font-family: 'Manrope', 'Noto Sans Devanagari', sans-serif;
    }

    .hero {
        position: relative;
        overflow: hidden;
        border-radius: 26px;
        padding: 2rem 2.2rem;
        color: white;
        background: radial-gradient(circle at 88% 5%, rgba(217,242,126,.32), transparent 24%), linear-gradient(125deg, #102f3c 0%, #0f655d 58%, #20a078 100%);
        box-shadow: 0 18px 42px rgba(14,74,73,.2);
        margin-bottom: 1.25rem;
    }

    .hero-kicker {
        text-transform: uppercase;
        letter-spacing: .16em;
        font-size: .7rem;
        font-weight: 800;
        color: #e5f79d;
        margin-bottom: .7rem;
    }

    .hero h1 {
        color: white !important;
        font-size: clamp(2rem, 4vw, 3rem) !important;
        margin: 0 0 .45rem 0;
    }

    .hero p {
        color: #e1f3ee;
        margin: 0;
        font-size: 1.04rem;
        max-width: 680px;
    }

    .hero-badges {
        display: flex;
        gap: .55rem;
        flex-wrap: wrap;
        margin-top: 1.2rem;
    }

    .hero-badge {
        border: 1px solid rgba(255,255,255,.22);
        background: rgba(255,255,255,.1);
        padding: .38rem .7rem;
        border-radius: 999px;
        color: #f0f6ec;
        font-size: .78rem;
    }

    .section-kicker {
        color: var(--forest-2);
        text-transform: uppercase;
        letter-spacing: .13em;
        font-size: .7rem;
        font-weight: 800;
        margin: .25rem 0 .2rem;
    }

    .sim-note {
        background: #2b2619;
        border: 1px solid #59482b;
        border-radius: 14px;
        padding: .85rem 1rem;
        color: #e5d3a9;
        font-size: .88rem;
        margin: .5rem 0 1.3rem;
    }

    .stButton > button,
    [data-testid="stFormSubmitButton"] button {
        border-radius: 12px;
        border: 1px solid #334747;
        background: #172629;
        color: #eaf3ee;
        font-weight: 700;
        transition: all .18s ease;
    }

    .stButton > button[kind="primary"],
    [data-testid="stFormSubmitButton"] button[kind="primary"] {
        background: #16775e;
        border-color: #16775e;
        color: #f5fff9;
    }

    .stButton > button:hover {
        border-color: var(--orange);
        color: #fff1e2;
        background: #203539;
    }

    [data-testid="stChatMessage"] {
        border: 1px solid var(--line);
        border-radius: 18px;
        background: #121f23;
        color: #edf5f0;
        padding: .75rem 1rem;
        margin-bottom: .55rem;
    }

    [data-testid="stChatInput"] textarea {
        border-radius: 16px;
        background: #121f23;
        color: #edf5f0;
    }

    div[data-testid="stExpander"] {
        border: 1px solid var(--line);
        border-radius: 16px;
        background: #121f23;
        color: #edf5f0;
    }

    [data-testid="stCaptionContainer"] { color: #a8b8b0; }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

def prepare_reading(reading, source="SIMULATED"):
    """Attach source and timestamp metadata."""
    prepared = dict(reading)
    prepared["source"] = source
    prepared.setdefault("timestamp", datetime.now().isoformat())
    return prepared


if "readings" not in st.session_state:
    st.session_state.readings = prepare_reading(initial_readings())

if "history" not in st.session_state:
    st.session_state.history = []

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "नमस्कार! मी MatiMitra आहे. तुमच्या शेतीबद्दल प्रश्न विचारा. "
                "मी उपलब्ध रीडिंगचा संदर्भ घेऊन उत्तर देईन."
            ),
        }
    ]

if "profile" not in st.session_state:
    st.session_state.profile = {
        "farmer": "Demo Farmer",
        "farm": "Plot 1",
        "location": "Kolhapur, Maharashtra",
        "crop": "",
        "area": 1.0,
        "irrigation": "Unknown",
        "stage": "Unknown",
    }

if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = ""

if "last_tts_audio" not in st.session_state:
    st.session_state.last_tts_audio = None

if "last_voice_error" not in st.session_state:
    st.session_state.last_voice_error = None

if "last_answer_mode" not in st.session_state:
    st.session_state.last_answer_mode = None

if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True

if "ai_provider" not in st.session_state:
    st.session_state.ai_provider = os.getenv(
        "DEFAULT_AI_PROVIDER", "Gemini"
    )

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

if not st.session_state.history:
    st.session_state.history.append({
        **st.session_state.readings,
        "time": datetime.now().strftime("%H:%M:%S"),
    })


# ---------------------------------------------------------
# READING MANAGEMENT
# ---------------------------------------------------------

def record_reading():
    """Generate a simulated reading and add it to chart history."""
    new_reading = next_readings(st.session_state.readings)
    st.session_state.readings = prepare_reading(
        new_reading, source="SIMULATED"
    )

    st.session_state.history.append({
        **st.session_state.readings,
        "time": datetime.now().strftime("%H:%M:%S"),
    })
    st.session_state.history = st.session_state.history[-100:]


def save_manual_reading(values):
    """Save farmer-entered values for the current session."""
    reading = prepare_reading(values, source="MANUAL")
    st.session_state.readings = reading

    st.session_state.history.append({
        **reading,
        "time": datetime.now().strftime("%H:%M:%S"),
    })
    st.session_state.history = st.session_state.history[-100:]


def get_crop_prediction(reading):
    """Return a crop prediction, or None if inputs are incomplete/invalid."""
    keys = [
        "N", "P", "K", "temperature", "humidity", "pH", "rainfall"
    ]

    try:
        if any(reading.get(key) is None for key in keys):
            return None

        values = [float(reading[key]) for key in keys]

        if not all(pd.notna(value) for value in values):
            return None

        return predict_crop(
            nitrogen=values[0],
            phosphorus=values[1],
            potassium=values[2],
            temperature=values[3],
            humidity=values[4],
            ph=values[5],
            rainfall=values[6],
        )
    except (ValueError, TypeError, FileNotFoundError, KeyError) as exc:
        st.warning(f"Crop prediction unavailable: {exc}")
        return None


# ---------------------------------------------------------
# SIDEBAR: PROFILE, AI SETTINGS AND READINGS
# ---------------------------------------------------------

with st.sidebar:
    st.markdown("# 🌱 MatiMitra")
    st.caption("YOUR FARM. YOUR NEXT MOVE.")
    st.divider()

    st.markdown("### Farm profile")
    profile = st.session_state.profile

    with st.form("farm_settings"):
        farmer = st.text_input("Farmer name", profile["farmer"])
        farm = st.text_input("Plot name", profile["farm"])
        location = st.text_input(
            "Village / district", profile["location"]
        )
        crop = st.text_input("Current crop", profile["crop"])
        area = st.number_input(
            "Area (acres)",
            min_value=0.0,
            value=float(profile["area"]),
            step=0.5,
        )

        irrigation_options = [
            "Unknown", "Rainfed", "Drip", "Sprinkler", "Flood"
        ]
        irrigation = st.selectbox(
            "Irrigation",
            irrigation_options,
            index=(
                irrigation_options.index(profile["irrigation"])
                if profile["irrigation"] in irrigation_options
                else 0
            ),
        )

        stage_options = [
            "Unknown", "Before sowing", "Vegetative",
            "Flowering", "Fruiting", "Harvest"
        ]
        stage = st.selectbox(
            "Crop stage",
            stage_options,
            index=(
                stage_options.index(profile["stage"])
                if profile["stage"] in stage_options
                else 0
            ),
        )

        save_profile = st.form_submit_button(
            "Save farm profile", width="stretch"
        )

    if save_profile:
        st.session_state.profile = {
            "farmer": farmer,
            "farm": farm,
            "location": location,
            "crop": crop,
            "area": area,
            "irrigation": irrigation,
            "stage": stage,
        }
        st.rerun()

    st.divider()
    st.markdown("### AI settings")

    configured_providers = available_ai_providers()
    provider_options = configured_providers or ["Gemini", "Groq"]

    if not configured_providers:
        st.warning(
            "No AI API key detected. Configure Gemini or Groq in .env."
        )

    default_provider = st.session_state.ai_provider
    if default_provider not in provider_options:
        default_provider = provider_options[0]

    st.selectbox(
        "Chat AI provider",
        options=provider_options,
        index=provider_options.index(default_provider),
        key="ai_provider",
    )

    st.toggle("Speak MatiMitra replies", key="voice_enabled")

    st.divider()
    st.markdown("### Soil readings")

    if st.button("↻ Generate demo readings", width="stretch"):
        record_reading()
        st.rerun()

    st.caption(
        "Demo readings are simulated; they do not come from physical sensors."
    )

    current = st.session_state.readings

    with st.form("manual_readings_form"):
        st.markdown("#### Enter readings manually")
        st.caption("Use values from your measurement source or soil report.")

        manual_n = st.number_input(
            "Nitrogen (N)", min_value=0.0, max_value=1000.0,
            value=float(current.get("N", 50.0)),
        )
        manual_p = st.number_input(
            "Phosphorus (P)", min_value=0.0, max_value=1000.0,
            value=float(current.get("P", 40.0)),
        )
        manual_k = st.number_input(
            "Potassium (K)", min_value=0.0, max_value=1000.0,
            value=float(current.get("K", 50.0)),
        )
        manual_ph = st.number_input(
            "Soil pH", min_value=0.0, max_value=14.0,
            value=float(current.get("pH", 6.5)), step=0.1,
        )
        manual_temp = st.number_input(
            "Temperature (°C)", min_value=-10.0, max_value=60.0,
            value=float(current.get("temperature", 30.0)),
        )
        manual_humidity = st.number_input(
            "Humidity (%)", min_value=0.0, max_value=100.0,
            value=float(current.get("humidity", 60.0)),
        )
        manual_rainfall = st.number_input(
            "Rainfall (mm)", min_value=0.0, max_value=1000.0,
            value=float(current.get("rainfall", 0.0)),
        )

        save_manual = st.form_submit_button(
            "Save manual readings", width="stretch"
        )

    if save_manual:
        save_manual_reading({
            "N": manual_n,
            "P": manual_p,
            "K": manual_k,
            "pH": manual_ph,
            "temperature": manual_temp,
            "humidity": manual_humidity,
            "rainfall": manual_rainfall,
        })
        st.rerun()


# ---------------------------------------------------------
# CURRENT FARM DATA
# ---------------------------------------------------------

readings = st.session_state.readings
profile = st.session_state.profile
source = readings.get("source", "SIMULATED")
analysis = analyze_soil(readings)
crop_prediction = get_crop_prediction(readings)


# ---------------------------------------------------------
# HERO SECTION
# ---------------------------------------------------------

reading_timestamp = str(readings.get("timestamp", "Not available"))
if len(reading_timestamp) >= 19 and "T" in reading_timestamp:
    display_time = reading_timestamp[11:19]
else:
    display_time = reading_timestamp

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-kicker">
            MatiMitra · नमस्कार {escape(str(profile['farmer']))}
        </div>
        <h1>Your soil. Your next move.</h1>
        <p>
            माती समजून घ्या. योग्य प्रश्न विचारा.
            पुढचं पाऊल विचारपूर्वक घ्या.
        </p>
        <div class="hero-badges">
            <span class="hero-badge">📍 {escape(str(profile['location']))}</span>
            <span class="hero-badge">🌱 {escape(str(profile['crop'] or 'Crop not set'))}</span>
            <span class="hero-badge">
                Reading source: {escape(str(source))} · {escape(display_time)}
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if source == "SIMULATED":
    st.markdown(
        """
        <div class="sim-note">
            <strong>Simulation mode:</strong>
            NPK and pH values are generated by software, not physical sensors.
            They are illustrative only and must not guide real fertilizer
            applications.
        </div>
        """,
        unsafe_allow_html=True,
    )
elif source == "MANUAL":
    st.info(
        "Manual-entry mode: these values were entered by the user. "
        "Verify them against the original report or measuring device."
    )
else:
    st.info(
        f"Reading source: {source}. Confirm the measurement source and calibration."
    )


# ---------------------------------------------------------
# SOIL SNAPSHOT
# ---------------------------------------------------------

st.markdown(
    '<div class="section-kicker">Today on the plot</div>',
    unsafe_allow_html=True,
)
st.subheader(f"{profile['farm']} · Soil snapshot")

metric_cols = st.columns(4, gap="medium")

for column, title, key in zip(
    metric_cols,
    ["Nitrogen", "Phosphorus", "Potassium", "Soil pH"],
    ["N", "P", "K", "pH"],
):
    value = readings.get(key)
    status = analysis.get(key, {}).get("status", "Unknown")

    with column:
        if value is None:
            column.metric(title, "N/A")
        else:
            column.metric(title, value, help=f"Interpretation: {status}")
        column.caption(f"{status} · {str(source).lower()}")


# ---------------------------------------------------------
# ML CROP RECOMMENDATION
# ---------------------------------------------------------

st.divider()
st.markdown(
    '<div class="section-kicker">Machine learning</div>',
    unsafe_allow_html=True,
)
st.subheader("Crop recommendation")

if crop_prediction:
    st.metric(
        "Recommended crop",
        crop_prediction["predicted_crop"].replace("_", " ").title(),
    )

    st.caption(
        "Model probability is not a guarantee of crop success. "
        "Predictions depend on the current readings and the training dataset."
    )

    st.write("Other model predictions")
    for item in crop_prediction["alternatives"]:
        st.write(
            f"- {item['crop'].replace('_', ' ').title()}: "
            f"{item['model_probability']:.1%} model probability"
        )

    with st.expander("Model details"):
        st.write(
            "Held-out test accuracy: "
            f"{crop_prediction['model_test_accuracy']:.2%}"
        )
        st.caption(crop_prediction["disclaimer"])
else:
    st.info(
        "A crop prediction is not available. Check that all seven "
        "measurements are present and the trained model exists."
    )


# ---------------------------------------------------------
# FARMER ALERTS
# ---------------------------------------------------------

st.divider()
st.markdown(
    '<div class="section-kicker">Readings and warnings</div>',
    unsafe_allow_html=True,
)
st.subheader("Farmer alerts")

alerts = generate_soil_alerts(readings)

for alert in alerts:
    if alert.startswith("No configured"):
        st.success(alert)
    else:
        st.warning(alert)

st.caption(
    "These are screening checks, not confirmed diagnoses of soil conditions "
    "or physical sensor faults. Verify unusual values before taking action."
)


# ---------------------------------------------------------
# HISTORY CHART AND INTERPRETATION
# ---------------------------------------------------------

chart_col, insight_col = st.columns([1.45, 1], gap="large")

with chart_col:
    st.markdown(
        '<div class="section-kicker">Over time</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Soil signal")

    df = pd.DataFrame(st.session_state.history)
    required_chart_columns = {"time", "N", "P", "K"}

    if not df.empty and required_chart_columns.issubset(df.columns):
        chart_data = df.melt(
            id_vars=["time"],
            value_vars=["N", "P", "K"],
            var_name="Nutrient",
            value_name="Reading",
        )

        fig = px.line(
            chart_data,
            x="time",
            y="Reading",
            color="Nutrient",
            markers=True,
            color_discrete_map={
                "N": "#087f66",
                "P": "#f28b45",
                "K": "#4f72c8",
            },
        )

        fig.update_layout(
            height=310,
            margin=dict(l=8, r=8, t=12, b=8),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family="Plus Jakarta Sans, Noto Sans Devanagari",
                color="#a8b8b0",
            ),
            legend_title_text="",
            xaxis_title="Time",
            yaxis_title="Reading",
            hovermode="x unified",
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="#26383a", zeroline=False)

        st.plotly_chart(
            fig, width="stretch", config={"displayModeBar": False}
        )
    else:
        st.info("No chart history is available yet.")

with insight_col:
    st.markdown(
        '<div class="section-kicker">A useful reminder</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Read the signal carefully")

    st.markdown(
        "The NPK demo bands are **not validated agronomic thresholds**. "
        "The values have no calibrated NPK concentration units, so use them "
        "to explore the prototype—not to decide fertilizer doses."
    )

    with st.expander("See interpretation details"):
        st.json(analysis)

    if st.button("✨ Explain these readings", width="stretch"):
        st.session_state.pending_question = (
            "माझ्या सध्याच्या मातीच्या रीडिंगचा अर्थ सोप्या मराठीत समजावून "
            "सांगा. उपलब्ध ML पीक शिफारस आणि तिच्या मर्यादाही समजावून सांगा. "
            "रीडिंगचा स्रोत आणि मर्यादा स्पष्ट करा."
        )


# ---------------------------------------------------------
# CHAT PROCESSING
# ---------------------------------------------------------

def process_question(question):
    """Ask the selected AI provider and save the response."""
    question = question.strip()
    if not question:
        return

    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    current_readings = st.session_state.readings
    current_analysis = analyze_soil(current_readings)
    current_prediction = get_crop_prediction(current_readings)

    try:
        with st.spinner("MatiMitra विचार करत आहे..."):
            answer, mode = answer_question(
                question=question,
                readings=current_readings,
                profile=st.session_state.profile,
                analysis=current_analysis,
                history=st.session_state.messages[:-1],
                provider=st.session_state.get("ai_provider", "Gemini"),
                crop_prediction=current_prediction,
            )
    except Exception as exc:
        answer = (
            "प्रश्न प्रक्रिया करताना अडचण आली. कृपया पुन्हा प्रयत्न करा."
        )
        mode = f"App error: {type(exc).__name__}"

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
    })
    st.session_state.last_answer_mode = mode

    if mode.startswith("AI error:") or mode == "Configuration error":
        st.session_state.last_tts_audio = None
        st.session_state.last_voice_error = None
    elif st.session_state.voice_enabled:
        try:
            with st.spinner("MatiMitra मराठी आवाज तयार करत आहे..."):
                st.session_state.last_tts_audio = speak_marathi(answer)
            st.session_state.last_voice_error = None
        except Exception as exc:
            st.session_state.last_tts_audio = None
            st.session_state.last_voice_error = type(exc).__name__


# ---------------------------------------------------------
# CHAT INTERFACE
# ---------------------------------------------------------

st.divider()
st.markdown(
    '<div class="section-kicker">Ask anything</div>',
    unsafe_allow_html=True,
)
st.subheader("Talk to MatiMitra")
st.caption(
    "मराठीत किंवा English मध्ये विचारा — माती, पीक किंवा रीडिंगबद्दल."
)

for index, message in enumerate(st.session_state.messages[-12:]):
    with st.chat_message(
        message["role"],
        avatar="🌿" if message["role"] == "assistant" else "🧑‍🌾",
    ):
        st.markdown(message["content"])

        is_latest = index == len(st.session_state.messages[-12:]) - 1
        if message["role"] == "assistant" and is_latest:
            mode = st.session_state.get("last_answer_mode")
            if mode:
                st.caption(f"MatiMitra · {mode}")

            voice_error = st.session_state.get("last_voice_error")
            if voice_error:
                st.caption(f"Voice generation unavailable: {voice_error}")

question = st.chat_input(
    "उदा. माझ्या जमिनीतील नायट्रोजन कमी असल्यास काय विचारात घ्यावे?"
)

if question:
    process_question(question)
    st.rerun()

if st.session_state.get("pending_question"):
    pending = st.session_state.pending_question
    st.session_state.pending_question = None
    process_question(pending)
    st.rerun()


# ---------------------------------------------------------
# VOICE INPUT
# ---------------------------------------------------------

with st.expander("🎙️ Ask by voice", expanded=False):
    st.write("मराठीत प्रश्न रेकॉर्ड करा आणि Transcribe and ask दाबा.")

    audio_file = st.audio_input("Record your question")

    if st.button("🎙️ Transcribe and ask", width="stretch"):
        if audio_file is None:
            st.warning("प्रथम तुमचा प्रश्न रेकॉर्ड करा.")
        else:
            audio_bytes = audio_file.getvalue()
            audio_hash = hashlib.sha256(audio_bytes).hexdigest()

            if audio_hash == st.session_state.last_audio_hash:
                st.info("हे रेकॉर्डिंग आधीच प्रक्रिया केले आहे.")
            else:
                try:
                    with st.spinner("तुमचा आवाज समजून घेत आहे..."):
                        transcript = transcribe_marathi_audio(
                            audio_bytes,
                            filename=audio_file.name or "question.wav",
                        )

                    st.session_state.last_audio_hash = audio_hash
                    st.markdown(f"**तुमचा प्रश्न:** {transcript}")

                    process_question(transcript)
                    st.rerun()

                except Exception as exc:
                    st.error(
                        f"आवाज प्रक्रिया अयशस्वी ({type(exc).__name__}). "
                        "कृपया पुन्हा प्रयत्न करा."
                    )

if st.session_state.get("last_tts_audio"):
    with st.expander("🔊 Latest voice reply", expanded=False):
        st.audio(st.session_state.last_tts_audio, format="audio/mp3")


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.markdown(
    """
    <div style="text-align:center;color:#839087;font-size:.78rem;padding-top:1.8rem">
        MATIMITRA · FARM COMPANION · VERIFY REAL FARM DECISIONS WITH A RELIABLE SOIL TEST
    </div>
    """,
    unsafe_allow_html=True,
)
