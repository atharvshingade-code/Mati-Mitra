"""MatiMitra — persistent farming assistant."""



import hashlib

import json

import os

from datetime import datetime

from html import escape



import pandas as pd

import plotly.express as px

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from dotenv import load_dotenv



from supabase_client import require_farmer

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

    page_title="MatiMitra",

    page_icon="🌱",

    layout="wide",

)



st.markdown(

    """

    <style>

    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap');



    :root {

        --forest: #73d2a2;

        --ink: #edf5f0;

        --muted: #a8b8b0;

        --paper: #0b1417;

        --line: #26383a;

    }



    html, body, [class*="css"] {

        font-family: 'Plus Jakarta Sans', 'Noto Sans Devanagari', sans-serif;

    }



    [data-testid="stAppViewContainer"] {

        background: radial-gradient(ellipse at 78% 0%, #142b2a 0%, transparent 34%), var(--paper);

        color: var(--ink);

    }



    [data-testid="stHeader"] { background: transparent; }



    .block-container {

        max-width: 1400px;

        padding-top: 1.5rem;

        padding-bottom: 3rem;

    }



    h1, h2, h3 {

        font-family: 'Manrope', 'Noto Sans Devanagari', sans-serif;

        color: var(--ink);

        letter-spacing: -0.025em;

    }



    [data-testid="stSidebar"] {

        background: linear-gradient(175deg, #10241f 0%, #101d25 100%);

    }



    [data-testid="stMetric"] {

        background: #121f23;

        border: 1px solid var(--line);

        border-radius: 16px;

        padding: 1rem;

    }



    [data-testid="stMetricValue"] { color: #a8e8c2; }



    .hero {

        border-radius: 24px;

        padding: 2rem;

        margin-bottom: 1.2rem;

        background: linear-gradient(125deg, #102f3c, #0f655d 65%, #20a078);

    }



    .hero h1 { color: white; }

    .hero p { color: #e1f3ee; }



    .sim-note {

        background: #2b2619;

        border: 1px solid #59482b;

        border-radius: 12px;

        padding: .9rem 1rem;

        color: #e5d3a9;

        margin-bottom: 1rem;

    }



    .section-kicker {

        color: var(--forest);

        text-transform: uppercase;

        letter-spacing: .12em;

        font-size: .72rem;

        font-weight: 800;

    }



    .stButton > button {

        border-radius: 11px;

        font-weight: 650;

    }



    [data-testid="stChatMessage"] {

        border: 1px solid var(--line);

        border-radius: 16px;

        background: #121f23;

    }



    footer { visibility: hidden; }

    </style>

    """,

    unsafe_allow_html=True,

)



# ---------------------------------------------------------
# AUTHENTICATION AND FARM
# ---------------------------------------------------------
supabase, auth_user, active_farm = require_farmer()



if not active_farm:

    st.warning("Create or select a farm to continue.")

    st.stop()



farm_id = str(active_farm["id"])

farmer_id = str(auth_user.id)



# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------
def init_state(key, value):

    if key not in st.session_state:

        st.session_state[key] = value





init_state("mm_loaded_farm_id", None)

init_state("readings", None)

init_state("history", [])

init_state("messages", [])

init_state("pending_question", None)

init_state("last_audio_hash", "")

init_state("last_tts_audio", None)

init_state("last_voice_error", None)

init_state("last_answer_mode", None)

init_state("voice_enabled", True)

init_state("last_crop_prediction", None)

init_state("last_prediction_saved_for", None)

init_state("ai_provider", os.getenv("DEFAULT_AI_PROVIDER", "Gemini"))
init_state("mm_auto_monitoring", False)
init_state("mm_auto_monitoring_interval_minutes", 5)
init_state("mm_last_auto_reading_at", {})



profile = {

    "farmer": (

        auth_user.user_metadata.get("full_name")

        if getattr(auth_user, "user_metadata", None)

        else None

    ) or auth_user.email or "Farmer",

    "farm": active_farm.get("name", "My farm"),

    "location": ", ".join(

        str(x) for x in [

            active_farm.get("village"),

            active_farm.get("district"),

        ] if x

    ) or "Location not set",

    "crop": active_farm.get("current_crop") or "",

    "area": active_farm.get("area_acres") or 0,

    "irrigation": active_farm.get("irrigation") or "Unknown",

    "stage": active_farm.get("crop_stage") or "Unknown",

}





# ---------------------------------------------------------
# SUPABASE HELPERS
# ---------------------------------------------------------
def from_db(row):

    """Convert a Supabase reading into the application's reading format."""

    return {

        "id": row.get("id"),

        "N": row.get("nitrogen"),

        "P": row.get("phosphorus"),

        "K": row.get("potassium"),

        "pH": row.get("ph"),

        "temperature": row.get("temperature"),

        "humidity": row.get("humidity"),

        "rainfall": row.get("rainfall"),

        "moisture": row.get("moisture"),

        "timestamp": row.get("created_at") or datetime.now().isoformat(),

        "source": row.get("source", "SIMULATED"),

    }





def to_db(reading):

    """Convert an application reading into the database schema."""

    payload = {

        "farm_id": farm_id,

        "nitrogen": float(reading["N"]),

        "phosphorus": float(reading["P"]),

        "potassium": float(reading["K"]),

        "ph": float(reading["pH"]),

        "temperature": float(reading["temperature"]),

        "humidity": float(reading["humidity"]),

        "rainfall": float(reading["rainfall"]),

        "source": reading.get("source", "SIMULATED"),

    }



    if reading.get("moisture") is not None:

        payload["moisture"] = float(reading["moisture"])



    return payload





def save_reading(reading):

    """Persist a reading and return the saved database row."""

    result = (

        supabase.table("sensor_readings")

        .insert(to_db(reading))

        .execute()

    )

    if not result.data:

        raise RuntimeError("Supabase did not return the saved reading.")

    return from_db(result.data[0])





def load_readings():

    """Load up to 100 latest readings for the active farm."""

    result = (

        supabase.table("sensor_readings")

        .select("*")

        .eq("farm_id", farm_id)

        .order("created_at", desc=True)

        .limit(100)

        .execute()

    )

    return [from_db(row) for row in reversed(result.data or [])]





def load_chat():

    """Load the recent conversation for the current user and farm."""

    result = (

        supabase.table("chat_history")

        .select("role,content,created_at")

        .eq("farmer_id", farmer_id)

        .eq("farm_id", farm_id)

        .order("created_at", desc=True)

        .limit(30)

        .execute()

    )

    rows = list(reversed(result.data or []))

    return [

        {"role": row["role"], "content": row["content"]}

        for row in rows

    ]





def save_chat(role, content):

    supabase.table("chat_history").insert({

        "farmer_id": farmer_id,

        "farm_id": farm_id,

        "role": role,

        "content": content,

    }).execute()





def load_alerts():

    result = (

        supabase.table("agro_alerts")

        .select("*")

        .eq("farm_id", farm_id)

        .order("created_at", desc=True)

        .limit(100)

        .execute()

    )

    return result.data or []





def create_alert(alert_type, severity, title, message):

    """Avoid duplicate open alerts with the same title."""

    existing = (

        supabase.table("agro_alerts")

        .select("id")

        .eq("farm_id", farm_id)

        .eq("title", title)

        .eq("status", "OPEN")

        .limit(1)

        .execute()

    )

    if existing.data:

        return



    supabase.table("agro_alerts").insert({

        "farm_id": farm_id,

        "alert_type": alert_type,

        "severity": severity,

        "title": title,

        "message": message,

        "status": "OPEN",

    }).execute()





def detect_trends(history):

    """

    Demonstration trend detection only.

    These percentage changes are not agronomic thresholds.

    """

    if len(history) < 3:

        return



    first = history[-3]

    latest = history[-1]



    for key, label in [("N", "Nitrogen"), ("P", "Phosphorus"), ("K", "Potassium")]:

        try:

            start = float(first[key])

            end = float(latest[key])

        except (TypeError, ValueError, KeyError):

            continue



        if start > 0 and end <= start * 0.85:

            create_alert(

                alert_type="DEMO_TREND",

                severity="WARNING",

                title=f"Simulated {label} trend",

                message=(

                    f"The latest three stored readings show a simulated "

                    f"{label} decrease of at least 15%. This is a software "

                    f"trend alert, not a confirmed soil deficiency. "

                    f"Verify with a calibrated measurement or soil test."

                ),

            )





# ---------------------------------------------------------
# LOAD DATA WHEN THE FARM CHANGES
# ---------------------------------------------------------
if st.session_state.mm_loaded_farm_id != farm_id:

    st.session_state.mm_loaded_farm_id = farm_id

    st.session_state.last_crop_prediction = None

    st.session_state.last_prediction_saved_for = None



    try:

        history = load_readings()



        # If no reading exists yet, create one clearly labelled as simulated.
        if not history:

            initial = initial_readings()

            initial["source"] = "SIMULATED"

            saved = save_reading(initial)

            history = [saved]



        st.session_state.history = history

        st.session_state.readings = history[-1]

        st.session_state.messages = load_chat()



        if not st.session_state.messages:

            st.session_state.messages = [{

                "role": "assistant",

                "content": (

                    "नमस्कार! मी MatiMitra आहे. तुमच्या शेतीबद्दल "

                    "मराठीत किंवा English मध्ये प्रश्न विचारा."

                ),

            }]



        detect_trends(history)



    except Exception as exc:

        st.error("Could not load farm data from Supabase.")

        st.code(f"{type(exc).__name__}: {exc}")

        st.stop()





readings = st.session_state.readings

history = st.session_state.history





# ---------------------------------------------------------
# READING HELPERS
# ---------------------------------------------------------
def record_reading(nitrogen_decline=False):
    """Generate and persist the next simulated reading."""
    new_reading = next_readings(
        st.session_state.readings,
        nitrogen_decline=nitrogen_decline,
    )
    new_reading["source"] = "SIMULATED"

    try:
        saved = save_reading(new_reading)
        st.session_state.readings = saved
        st.session_state.history.append(saved)
        st.session_state.history = st.session_state.history[-100:]
        detect_trends(st.session_state.history)

        if nitrogen_decline:
            st.success(
                "Simulated nitrogen decline saved. "
                "Check AgroAlert for the trend alert."
            )
        else:
            st.success("Simulated reading saved to Supabase.")
        return True
    except Exception as exc:
        st.error("Could not save the simulated reading.")
        st.code(f"{type(exc).__name__}: {exc}")
        return False


def get_crop_prediction(reading):

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

        st.warning(f"Prediction unavailable: {exc}")

        return None





# ---------------------------------------------------------
# SIDEBAR NAVIGATION
# ---------------------------------------------------------
def navigate_to_page(page_name):
    """Update the navigation radio value from a Streamlit callback."""
    st.session_state.mm_page = page_name


with st.sidebar:

    st.markdown("# 🌱 MatiMitra")

    st.caption("YOUR FARM. YOUR NEXT MOVE.")

    st.divider()



    st.markdown(f"**Selected farm:** {profile['farm']}")

    st.caption(profile["location"])

    st.caption(f"Crop: {profile['crop'] or 'Not set'}")

    # In-app notification summary: only alerts for the selected farm.
    try:
        sidebar_alerts = load_alerts()
        open_alert_count = sum(
            1 for alert in sidebar_alerts
            if alert.get("status") == "OPEN"
        )
        st.caption(f"Open AgroAlerts: {open_alert_count}")
        if open_alert_count:
            st.warning(
                f"{open_alert_count} open alert(s) need your attention.",
                icon="🔔",
            )
    except Exception:
        # Keep navigation available even if the alerts table is temporarily unavailable.
        st.caption("AgroAlert status is currently unavailable.")

    pages = [

        "Dashboard",

        "AgroAlert",

        "Crop Intelligence",

        "AI Farming Assistant",

    ]



    sensor_lab_enabled = (

        os.getenv("MATIMITRA_ENABLE_SENSOR_LAB", "false").lower()

        in ("1", "true", "yes")

    )

    if sensor_lab_enabled:

        pages.append("Sensor Lab")



    page = st.radio("Navigation", pages, key="mm_page")

    st.divider()
    st.subheader("Automatic monitoring")
    st.checkbox(
        "Enable simulated monitoring",
        key="mm_auto_monitoring",
        help=(
            "When enabled, MatiMitra generates clearly labelled simulated readings "
            "while this app is open on the Dashboard. This is not a physical sensor feed."
        ),
    )
    st.selectbox(
        "Reading interval",
        options=[1, 5, 10],
        format_func=lambda minutes: f"Every {minutes} minute(s)",
        key="mm_auto_monitoring_interval_minutes",
        disabled=not st.session_state.mm_auto_monitoring,
    )
    if st.session_state.mm_auto_monitoring:
        st_autorefresh(
            interval=60_000,
            limit=None,
            key=f"mm_auto_refresh_{farm_id}",
        )
        st.caption("Monitoring refreshes while the app is open. Readings are simulated.")



    st.divider()

    configured_providers = available_ai_providers()

    provider_options = configured_providers or ["Gemini", "Groq"]



    if not configured_providers:

        st.warning("Configure a Gemini or Groq API key in .env to use chat.")



    selected_provider = st.session_state.ai_provider

    if selected_provider not in provider_options:

        selected_provider = provider_options[0]



    st.selectbox(

        "Chat AI provider",

        options=provider_options,

        index=provider_options.index(selected_provider),

        key="ai_provider",

    )

    st.toggle("Speak MatiMitra replies", key="voice_enabled")





# ---------------------------------------------------------
# SHARED HEADER
# ---------------------------------------------------------
st.markdown(

    f"""

    <div class="hero">

      <div style="font-size:.75rem;letter-spacing:.13em;font-weight:800;color:#d9f27e">

        MATIMITRA · FARM COMPANION

      </div>

      <h1>{escape(page)}</h1>

      <p>

        नमस्कार {escape(str(profile['farmer']))}.

        Understand your farm data and make informed decisions.

      </p>


    </div>

    """,

    unsafe_allow_html=True,

)



# ---------------------------------------------------------
# AUTOMATIC SIMULATED MONITORING
# ---------------------------------------------------------
# Generate no more often than the configured interval, and only while the
# farmer has enabled monitoring and is viewing the Dashboard.
if st.session_state.get("mm_auto_monitoring") and page == "Dashboard":
    now = datetime.now()
    last_by_farm = st.session_state.get("mm_last_auto_reading_at", {})
    last_value = last_by_farm.get(farm_id)
    interval_minutes = int(
        st.session_state.get("mm_auto_monitoring_interval_minutes", 5)
    )
    elapsed_seconds = (
        (now - last_value).total_seconds()
        if isinstance(last_value, datetime)
        else None
    )
    if elapsed_seconds is not None and elapsed_seconds >= interval_minutes * 60:
        if record_reading():
            last_by_farm[farm_id] = now
            st.session_state.mm_last_auto_reading_at = last_by_farm
            st.info(
                "Automatic simulated reading saved. No physical sensor is connected."
            )
    elif last_value is None:
        # Start the interval timer on first enable; do not generate immediately.
        last_by_farm[farm_id] = now
        st.session_state.mm_last_auto_reading_at = last_by_farm


# DASHBOARD
# ---------------------------------------------------------
if page == "Dashboard":

    st.markdown('<div class="section-kicker">Farm overview</div>', unsafe_allow_html=True)

    # Prominent farmer-facing notification for unresolved alerts.
    try:
        dashboard_open_alerts = [
            alert for alert in load_alerts()
            if alert.get("status") == "OPEN"
        ]
        if dashboard_open_alerts:
            st.warning(
                f"You have {len(dashboard_open_alerts)} open AgroAlert(s). "
                "Review them before making farm decisions.",
                icon="🔔",
            )
            st.button(
                "View AgroAlerts",
                key="mm_dashboard_view_alerts",
                on_click=navigate_to_page,
                args=("AgroAlert",),
            )
    except Exception as exc:
        st.caption(f"AgroAlert notifications are temporarily unavailable: {exc}")

    st.subheader("Latest stored readings")



    cols = st.columns(4)

    for col, label, key in zip(

        cols,

        ["Nitrogen (N)", "Phosphorus (P)", "Potassium (K)", "Soil pH"],

        ["N", "P", "K", "pH"],

    ):

        value = readings.get(key)

        col.metric(label, "N/A" if value is None else value)



    st.caption(

        f"Source: {readings.get('source', 'Unknown')} · "

        f"Timestamp: {readings.get('timestamp', 'Not available')}"

    )



    analysis = analyze_soil(readings)

    st.divider()

    st.subheader("Screening checks")



    screening_alerts = generate_soil_alerts(readings)

    if not screening_alerts:

        st.info("No screening messages were generated.")

    else:

        for item in screening_alerts:

            if item.startswith("No configured"):

                st.success(item)

            else:

                st.warning(item)



    st.caption(

        "These checks are not confirmed soil diagnoses. Demo NPK bands "

        "are not validated agronomic thresholds."

    )



    st.divider()

    st.subheader("Reading history")



    df = pd.DataFrame(st.session_state.history)

    if not df.empty and {"timestamp", "N", "P", "K"}.issubset(df.columns):

        df["time"] = df["timestamp"].astype(str)

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

        )

        fig.update_layout(

            height=350,

            paper_bgcolor="rgba(0,0,0,0)",

            plot_bgcolor="rgba(0,0,0,0)",

            font_color="#a8b8b0",

            margin=dict(l=10, r=10, t=20, b=10),

        )

        st.plotly_chart(fig, width="stretch")

    else:

        st.info("No reading history is available.")



    st.divider()

    st.subheader("Open AgroAlerts")



    try:

        open_alerts = [

            a for a in load_alerts()

            if a.get("status") == "OPEN"

        ]

        if not open_alerts:

            st.success("There are no open AgroAlerts.")

        else:

            for alert in open_alerts[:5]:

                st.warning(

                    f"**{alert.get('title', 'Alert')}** — "

                    f"{alert.get('message', '')}"

                )

    except Exception as exc:

        st.error(f"Could not load AgroAlerts: {exc}")





# ---------------------------------------------------------
# AGROALERT
# ---------------------------------------------------------
elif page == "AgroAlert":

    st.subheader("Persistent alerts")

    st.write(

        "AgroAlert stores trend notifications independently of the chatbot "

        "and crop prediction model."

    )



    try:

        alerts = load_alerts()



        if not alerts:

            st.info("No saved alerts yet. Alerts appear when a supported trend is detected.")

        else:

            for alert in alerts:

                status = alert.get("status", "OPEN")

                severity = alert.get("severity", "INFO")



                with st.container(border=True):

                    st.markdown(

                        f"**{alert.get('title', 'Alert')}** · "

                        f"{severity} · {status}"

                    )

                    st.write(alert.get("message", ""))

                    st.caption(

                        f"Created: {alert.get('created_at', 'Unknown')}"

                    )



                    if status == "OPEN":

                        c1, c2 = st.columns(2)



                        if c1.button(

                            "Acknowledge",

                            key=f"ack_{alert['id']}",

                        ):

                            supabase.table("agro_alerts").update({

                                "status": "ACKNOWLEDGED"

                            }).eq("id", alert["id"]).eq("farm_id", farm_id).execute()

                            st.rerun()



                        if c2.button(

                            "Resolve",

                            key=f"resolve_{alert['id']}",

                        ):

                            supabase.table("agro_alerts").update({

                                "status": "RESOLVED",

                                "resolved_at": datetime.now().astimezone().isoformat(),

                            }).eq("id", alert["id"]).eq("farm_id", farm_id).execute()

                            st.rerun()



    except Exception as exc:

        st.error("Could not load or update AgroAlerts.")

        st.code(f"{type(exc).__name__}: {exc}")





# ---------------------------------------------------------
# CROP INTELLIGENCE
# ---------------------------------------------------------
elif page == "Crop Intelligence":

    st.subheader("ML crop recommendation")

    st.write(

        "This page runs the trained crop model independently of the "

        "AI Farming Assistant."

    )



    st.markdown("**Inputs from the latest saved reading**")

    cols = st.columns(4)

    for col, label, key in zip(

        cols,

        ["Nitrogen", "Phosphorus", "Potassium", "pH"],

        ["N", "P", "K", "pH"],

    ):

        col.metric(label, "N/A" if readings.get(key) is None else readings[key])



    if st.button("Run crop prediction", type="primary"):

        prediction = get_crop_prediction(readings)



        if prediction is None:

            st.error("Prediction unavailable. Check the seven model inputs.")

        else:

            st.session_state.last_crop_prediction = prediction



            try:

                alternatives = prediction.get("alternatives", [])

                supabase.table("crop_predictions").insert({

                    "farm_id": farm_id,

                    "predicted_crop": prediction["predicted_crop"],

                    "model_probability": prediction["model_probability"],

                    "alternatives": alternatives,

                    "input_reading_id": readings.get("id"),

                }).execute()

                st.session_state.last_prediction_saved_for = readings.get("id")

            except Exception as exc:

                st.warning(f"Prediction ran, but saving its history failed: {exc}")



    prediction = st.session_state.last_crop_prediction



    if prediction:

        st.divider()

        st.metric(

            "Recommended crop",

            prediction["predicted_crop"].replace("_", " ").title(),

        )

        st.metric(

            "Model probability",

            f"{prediction['model_probability']:.1%}",

        )



        st.caption(

            f"Held-out test accuracy: {prediction['model_test_accuracy']:.2%}. "

            "This is a dataset-based model estimate, not a guarantee of crop success."

        )



        st.subheader("Other model predictions")

        for item in prediction.get("alternatives", []):

            st.write(

                f"- {item['crop'].replace('_', ' ').title()}: "

                f"{item['model_probability']:.1%}"

            )



        st.caption(prediction.get("disclaimer", ""))



        def prepare_assistant_question():
            st.session_state.pending_question = (
                "Explain this crop model result in simple Marathi. "
                f"The predicted crop is {prediction['predicted_crop']}. "
                "Explain model probability, limitations, and what real-world "
                "information should be checked before choosing a crop."
            )
            navigate_to_page("AI Farming Assistant")

        st.button(
            "Ask the assistant about this result",
            on_click=prepare_assistant_question,
        )



    st.divider()

    st.subheader("Previous predictions")



    try:

        result = (

            supabase.table("crop_predictions")

            .select("predicted_crop,model_probability,created_at")

            .eq("farm_id", farm_id)

            .order("created_at", desc=True)

            .limit(20)

            .execute()

        )

        if result.data:

            st.dataframe(pd.DataFrame(result.data), width="stretch")

        else:

            st.info("No saved predictions yet.")

    except Exception as exc:

        st.warning(f"Could not load prediction history: {exc}")





# ---------------------------------------------------------
# AI FARMING ASSISTANT
# ---------------------------------------------------------
elif page == "AI Farming Assistant":

    st.subheader("Talk to MatiMitra")

    st.caption(

        "मराठीत किंवा English मध्ये विचारा — माती, पीक किंवा शेतीबद्दल."

    )



    for message in st.session_state.messages[-20:]:

        with st.chat_message(

            message["role"],

            avatar="🌿" if message["role"] == "assistant" else "🧑‍🌾",

        ):

            st.markdown(message["content"])



    def process_question(question):

        question = question.strip()

        if not question:

            return



        st.session_state.messages.append({

            "role": "user",

            "content": question,

        })



        try:

            save_chat("user", question)

        except Exception as exc:

            st.warning(f"Could not save your question to chat history: {exc}")



        try:

            with st.spinner("MatiMitra विचार करत आहे..."):

                answer, mode = answer_question(

                    question=question,

                    readings=st.session_state.readings,

                    profile=profile,

                    analysis=analyze_soil(st.session_state.readings),

                    history=st.session_state.messages[:-1],

                    provider=st.session_state.get("ai_provider", "Gemini"),

                    # Crop prediction is deliberately not passed by default.
                )

        except Exception as exc:

            answer = "प्रश्न प्रक्रिया करताना अडचण आली. कृपया पुन्हा प्रयत्न करा."

            mode = f"App error: {type(exc).__name__}"



        st.session_state.messages.append({

            "role": "assistant",

            "content": answer,

        })

        st.session_state.last_answer_mode = mode



        try:

            save_chat("assistant", answer)

        except Exception as exc:

            st.warning(f"Could not save the assistant reply: {exc}")



        st.session_state.last_tts_audio = None

        st.session_state.last_voice_error = None



        if st.session_state.voice_enabled and not mode.startswith("AI error:"):

            try:

                with st.spinner("मराठी आवाज तयार करत आहे..."):

                    st.session_state.last_tts_audio = speak_marathi(answer)

            except Exception as exc:

                st.session_state.last_voice_error = type(exc).__name__



    question = st.chat_input("तुमचा प्रश्न येथे लिहा...")



    if question:

        process_question(question)

        st.rerun()



    if st.session_state.get("pending_question"):

        pending = st.session_state.pending_question

        st.session_state.pending_question = None

        process_question(pending)

        st.rerun()



    with st.expander("Ask by voice"):

        st.write("मराठीत प्रश्न रेकॉर्ड करा.")

        audio_file = st.audio_input("Record your question")



        if st.button("Transcribe and ask"):

            if audio_file is None:

                st.warning("प्रथम तुमचा प्रश्न रेकॉर्ड करा.")

            else:

                audio_bytes = audio_file.getvalue()

                audio_hash = hashlib.sha256(audio_bytes).hexdigest()



                if audio_hash == st.session_state.last_audio_hash:

                    st.info("This recording has already been processed.")

                else:

                    try:

                        with st.spinner("आवाज समजून घेत आहे..."):

                            transcript = transcribe_marathi_audio(

                                audio_bytes,

                                filename=audio_file.name or "question.wav",

                            )



                        st.session_state.last_audio_hash = audio_hash

                        st.write(f"**तुमचा प्रश्न:** {transcript}")

                        process_question(transcript)

                        st.rerun()



                    except Exception as exc:

                        st.error(

                            f"Voice processing failed: {type(exc).__name__}"

                        )



    if st.session_state.get("last_tts_audio"):

        st.audio(st.session_state.last_tts_audio, format="audio/mp3")



    if st.session_state.get("last_answer_mode"):

        st.caption(f"MatiMitra · {st.session_state.last_answer_mode}")



    if st.session_state.get("last_voice_error"):

        st.caption(

            "Voice generation unavailable: "

            + st.session_state.last_voice_error

        )





# ---------------------------------------------------------
# SENSOR LAB — LOCAL DEMO ONLY
# ---------------------------------------------------------
elif page == "Sensor Lab":

    st.subheader("Sensor Lab")

    st.warning(

        "Demonstration controls only. These values are simulated and are "

        "not physical sensor measurements."

    )



    st.write(

        "Use this page to generate additional readings for the selected farm. "

        "Generated records are stored in Supabase and appear in its history."

    )



    if st.button(
        "Generate and save simulated reading",
        type="primary",
        key="mm_generate_reading",
    ):
        if record_reading():
            st.rerun()

    st.divider()
    st.subheader("AgroAlert test")
    st.caption(
        "Test mode: each click reduces simulated nitrogen by 10%. "
        "This is a software test, not a real soil diagnosis."
    )

    if st.button(
        "Simulate declining nitrogen",
        key="mm_nitrogen_decline",
    ):
        if record_reading(nitrogen_decline=True):
            st.rerun()



    st.divider()

    st.subheader("Recent simulated readings")



    simulated = [

        item for item in st.session_state.history

        if item.get("source") == "SIMULATED"

    ]



    if simulated:

        display_rows = []

        for item in reversed(simulated[-20:]):

            display_rows.append({

                "Timestamp": item.get("timestamp"),

                "N": item.get("N"),

                "P": item.get("P"),

                "K": item.get("K"),

                "pH": item.get("pH"),

                "Temperature": item.get("temperature"),

                "Humidity": item.get("humidity"),

                "Rainfall": item.get("rainfall"),

            })

        st.dataframe(pd.DataFrame(display_rows), width="stretch")

    else:

        st.info("No simulated readings have been recorded.")





# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------
st.divider()

st.caption(

    "MATIMITRA · FARM COMPANION · Verify real farm decisions with reliable "

    "measurements and appropriate agricultural guidance."

)
