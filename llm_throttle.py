import time

import streamlit as st


def throttle_llm_call(provider, model):
    throttle_interval = float(
        st.session_state.get(
            "llm_throttle_interval_seconds",
            0.0
        ) or 0.0
    )

    if throttle_interval <= 0:
        remember_llm_call_start(provider, model)
        return

    last_call_times = st.session_state.setdefault(
        "llm_last_call_times",
        {}
    )

    throttle_key = f"{provider}:{model}"
    now = time.monotonic()
    last_call_time = last_call_times.get(throttle_key)

    if last_call_time is not None:
        elapsed = now - last_call_time
        wait_seconds = throttle_interval - elapsed

        if wait_seconds > 0:
            st.info(
                f"Waiting {wait_seconds:.1f} seconds before calling "
                f"{provider} / {model}."
            )
            time.sleep(wait_seconds)

    remember_llm_call_start(provider, model)


def remember_llm_call_start(provider, model):
    last_call_times = st.session_state.setdefault(
        "llm_last_call_times",
        {}
    )

    last_call_times[f"{provider}:{model}"] = time.monotonic()
