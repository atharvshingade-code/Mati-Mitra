
"""Supabase authentication and farm selection for MatiMitra."""

import os

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client
from i18n import t

load_dotenv()


def get_client():
    """Create one Supabase client per Streamlit session."""
    if "mm_supabase_client" not in st.session_state:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            st.error(
                "Supabase credentials are missing. "
                "Check SUPABASE_URL and SUPABASE_KEY in .env."
            )
            st.stop()

        try:
            st.session_state.mm_supabase_client = create_client(url, key)
        except Exception as exc:
            st.error("Could not connect to Supabase.")
            st.code(f"{type(exc).__name__}: {exc}")
            st.stop()

    return st.session_state.mm_supabase_client


def render_authentication(client):
    """Show login and registration until a farmer is authenticated."""
    if st.session_state.get("mm_user") is not None:
        return st.session_state.mm_user

    st.selectbox("Language / भाषा", ["English", "मराठी"], key="mm_language")
    st.title("MatiMitra")
    st.subheader(t('Your farm, monitored intelligently'))
    st.write(t('Sign in or create a farmer account to continue.'))

    login_tab, register_tab = st.tabs([t("Login"), t("Create account")])

    with login_tab:
        with st.form("mm_login_form"):
            email = st.text_input(t('Email'), key="mm_login_email")
            password = st.text_input(
                t('Password'),
                type="password",
                key="mm_login_password",
            )
            login_submitted = st.form_submit_button(
                t('Login'),
                type="primary",
                width="stretch",
            )

        if login_submitted:
            if not email.strip() or not password:
                st.error(t('Enter your email and password.'))
            else:
                try:
                    response = client.auth.sign_in_with_password(
                        {
                            "email": email.strip(),
                            "password": password,
                        }
                    )

                    if response.user:
                        st.session_state.mm_user = response.user
                        st.rerun()
                    else:
                        st.error("Login failed. Please try again.")

                except Exception as exc:
                    st.error("Login failed.")
                    st.code(f"{type(exc).__name__}: {exc}")

    with register_tab:
        with st.form("mm_register_form"):
            full_name = st.text_input(
                t('Full name'),
                key="mm_register_name",
            )
            email = st.text_input(
                t('Email'),
                key="mm_register_email",
            )
            password = st.text_input(
                t('Password'),
                type="password",
                key="mm_register_password",
                help="Use a strong password.",
            )
            register_submitted = st.form_submit_button(
                t('Create account'),
                type="primary",
                width="stretch",
            )

        if register_submitted:
            if not full_name.strip() or not email.strip() or not password:
                st.error(t('Complete all fields.'))
            elif len(password) < 8:
                st.error(t('Use a password with at least 8 characters.'))
            else:
                try:
                    response = client.auth.sign_up(
                        {
                            "email": email.strip(),
                            "password": password,
                            "options": {
                                "data": {"full_name": full_name.strip()}
                            },
                        }
                    )

                    if response.user and response.session:
                        st.session_state.mm_user = response.user
                        st.rerun()
                    elif response.user:
                        st.success(
                            t('Account created. Sign in with your email and password if confirmation is not required.')
                        )
                    else:
                        st.error("Registration did not return a user.")

                except Exception as exc:
                    st.error("Registration failed.")
                    st.code(f"{type(exc).__name__}: {exc}")

    st.stop()


def clear_farm_state():
    """Clear data that belongs to the previously active farm."""
    keys_to_clear = (
        "mm_loaded_farm_id",
        "mm_profile_farm_id",
        "profile",
        "readings",
        "history",
        "messages",
        "last_crop_prediction",
        "last_prediction_saved_for",
        "pending_question",
        "last_tts_audio",
        "last_voice_error",
        "last_answer_mode",
        "last_audio_hash",
    )

    for key in keys_to_clear:
        st.session_state.pop(key, None)


def render_farm_selector(client, user):
    """Allow a farmer to create and switch between their farms."""
    with st.sidebar:
        st.divider()
        st.subheader(t('Farmer account'))
        st.caption(user.email or "Signed-in farmer")

        if st.button(
            t('Log out'),
            key="mm_logout_farm_selector",
            width="stretch",
        ):
            try:
                client.auth.sign_out()
            except Exception as exc:
                st.warning(f"Sign-out message: {exc}")

            for key in (
                "mm_user",
                "mm_active_farm",
                "mm_selected_farm_id",
                "mm_supabase_client",
                "ai_provider",
                "voice_enabled",
            ):
                st.session_state.pop(key, None)

            clear_farm_state()
            st.rerun()

        st.divider()
        st.subheader(t('My farms'))

        try:
            result = (
                client.table("farms")
                .select(
                    "id,name,village,district,area_acres,"
                    "current_crop,irrigation,crop_stage,created_at"
                )
                .order("created_at")
                .execute()
            )
            farms = result.data or []

        except Exception as exc:
            st.error("Could not load your farms.")
            st.code(f"{type(exc).__name__}: {exc}")
            st.stop()

        with st.expander(t('＋ Add a farm'), expanded=not farms):
            with st.form("mm_add_farm_form"):
                farm_name = st.text_input(t('Farm name'))
                village = st.text_input(t('Village'))
                district = st.text_input(t('District'))
                area = st.number_input(
                    t('Area (acres)'),
                    min_value=0.0,
                    value=1.0,
                    step=0.5,
                )
                crop = st.text_input(t('Current crop'))
                irrigation = st.selectbox(
                    t('Irrigation'),
                    ["Unknown", "Rainfed", "Drip", "Sprinkler", "Flood"],
                )
                stage = st.selectbox(
                    t('Crop stage'),
                    [
                        "Unknown",
                        "Before sowing",
                        "Vegetative",
                        "Flowering",
                        "Fruiting",
                        "Harvest",
                    ],
                )

                create_farm = st.form_submit_button(
                    t('Save farm'),
                    type="primary",
                    width="stretch",
                )

            if create_farm:
                if not farm_name.strip():
                    st.error("Enter a farm name.")
                else:
                    try:
                        result = client.table("farms").insert(
                            {
                                "owner_id": str(user.id),
                                "name": farm_name.strip(),
                                "village": village.strip() or None,
                                "district": district.strip() or None,
                                "area_acres": area,
                                "current_crop": crop.strip() or None,
                                "irrigation": irrigation,
                                "crop_stage": stage,
                            }
                        ).execute()

                        if result.data:
                            new_farm = result.data[0]
                            clear_farm_state()
                            st.session_state.mm_selected_farm_id = str(
                                new_farm["id"]
                            )
                            st.success("Farm created.")
                            st.rerun()
                        else:
                            st.error(
                                "Farm creation returned no record. "
                                "Check your Supabase policies."
                            )

                    except Exception as exc:
                        st.error("Could not create the farm.")
                        st.code(f"{type(exc).__name__}: {exc}")

        if not farms:
            st.info(t('Create your first farm to open the dashboard.'))
            st.stop()

        farm_by_id = {str(farm["id"]): farm for farm in farms}
        farm_ids = list(farm_by_id.keys())

        current_id = str(
            st.session_state.get("mm_selected_farm_id", "")
        )

        if current_id not in farm_by_id:
            current_id = farm_ids[0]
            st.session_state.mm_selected_farm_id = current_id

        st.selectbox(
            t('Active farm'),
            options=farm_ids,
            format_func=lambda farm_id: farm_by_id[farm_id]["name"],
            key="mm_selected_farm_id",
        )

        selected_id = str(st.session_state.mm_selected_farm_id)
        active_farm = farm_by_id[selected_id]

    # Clear cached readings, alerts-related context, chat, and predictions
    # when switching farms. app.py will load the selected farm's records.
    if str(st.session_state.get("mm_profile_farm_id", "")) != str(
        active_farm["id"]
    ):
        clear_farm_state()
        st.session_state.mm_profile_farm_id = str(active_farm["id"])

    st.session_state.mm_active_farm = active_farm
    return active_farm


def require_farmer():
    """Return the Supabase client, authenticated user, and selected farm."""
    client = get_client()
    user = render_authentication(client)
    farm = render_farm_selector(client, user)
    return client, user, farm
