import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime

# ==========================================================
# CONFIG
# ==========================================================

ENDPOINT = "https://michal-unboarded-erna.ngrok-free.dev/generate"
LOCAL_LOG_FILE = "research_logs.jsonl"
SNAPSHOT_FILE = "stability_snapshots.jsonl"

TEST_SUITE = [
    {"name": "Uplifting English", "prompt": "Tell me something uplifting."},
    {"name": "Hindi Emotional", "prompt": "मुझे बहुत निराशा महसूस हो रही है।"},
    {"name": "Mixed Mode", "prompt": "I feel stuck yaar."},
    {"name": "Factual English", "prompt": "What are the long-term benefits of daily exercise?"}
]

st.set_page_config(
    page_title="Research Command Center • v2.5",
    layout="wide",
    page_icon="🧠"
)

st.markdown("""
<style>

/* ============================= */
/* BASE LAYER */
/* ============================= */

.stApp {
    background: radial-gradient(circle at 15% 20%, #141a2f, #0b0f19 60%);
    color: #e5e7eb;
}

.block-container {
    padding-top: 1.8rem !important;
    max-width: 1450px;
}

/* ============================= */
/* GLASS CARDS */
/* ============================= */

.card {
    background: linear-gradient(145deg, rgba(20,26,43,0.85), rgba(15,20,36,0.85));
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 18px;
    padding: 1.6rem;
    margin-bottom: 1.2rem;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    box-shadow: 0 0 25px rgba(99,102,241,0.08);
    transition: 0.25s ease;
}

.card:hover {
    box-shadow: 0 0 35px rgba(139,92,246,0.18);
}

/* ============================= */
/* OUTPUT */
/* ============================= */

.output-box {
    background: #0d1323;
    border: 1px solid rgba(139,92,246,0.35);
    border-radius: 14px;
    padding: 1.2rem;
    white-space: pre-wrap;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    line-height: 1.6;
}

/* ============================= */
/* METRIC HUD */
/* ============================= */

.metric-hud {
    display: flex;
    gap: 14px;
    margin-top: 14px;
}

.metric-box {
    flex: 1;
    background: linear-gradient(145deg, rgba(15,20,36,0.85), rgba(12,16,28,0.85));
    border: 1px solid rgba(139,92,246,0.25);
    padding: 14px;
    border-radius: 16px;
    backdrop-filter: blur(10px);
}

.metric-label {
    font-size: 0.75rem;
    color: #9ca3af;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.metric-value {
    font-size: 1.4rem;
    font-weight: 600;
    color: #a78bfa;
}

/* ============================= */
/* BUTTONS */
/* ============================= */

.stButton > button {
    border-radius: 14px;
    font-weight: 600;
    padding: 0.8rem 1rem;
    transition: 0.2s ease;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    border: none;
    color: white;
    box-shadow: 0 0 20px rgba(139,92,246,0.5);
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 30px rgba(139,92,246,0.8);
    transform: translateY(-2px);
}

/* ============================= */
/* STATUS BAR */
/* ============================= */

.status-bar {
    background: linear-gradient(90deg, #1f2937, #111827);
    padding: 0.9rem 1.2rem;
    border-radius: 14px;
    border: 1px solid rgba(99,102,241,0.25);
    margin-bottom: 1.2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.badge {
    background: rgba(139,92,246,0.18);
    padding: 5px 12px;
    border-radius: 999px;
    font-size: 0.8rem;
    border: 1px solid rgba(139,92,246,0.45);
}

</style>
""", unsafe_allow_html=True)

# ==========================================================
# UTILITIES
# ==========================================================

def log_to_file(entry: dict):
    with open(LOCAL_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def load_snapshots():
    try:
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []

def run_inference(prompt, temperature, top_p, max_tokens, do_sample):
    if not prompt.strip():
        st.error("Prompt cannot be empty.")
        return None

    payload = {
        "prompt": prompt,
        "temperature": temperature,
        "top_p": top_p,
        "max_new_tokens": max_tokens,
        "do_sample": do_sample
    }

    try:
        response = requests.post(ENDPOINT, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()

        return {
            "output": data.get("response_text", ""),
            "latency_ms": data.get("latency_ms", "?"),
            "input_tokens": data.get("input_tokens", "?"),
            "output_tokens": data.get("output_tokens", "?"),
            "config": payload,
            "raw": data
        }

    except Exception as e:
        st.error(f"Inference failed → {e}")
        return None

def append_history(mode, prompt, res_a=None, res_b=None):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "mode": mode,
        "prompt": prompt,
        "prompt_short": prompt[:90] + "…" if len(prompt) > 90 else prompt
    }

    if res_a:
        entry.update({
            "temp_a": res_a["config"]["temperature"],
            "top_p_a": res_a["config"]["top_p"],
            "latency_a_ms": res_a["latency_ms"],
            "out_tokens_a": res_a["output_tokens"],
            "output_a": res_a["output"][:280]
        })

    if res_b:
        entry.update({
            "temp_b": res_b["config"]["temperature"],
            "top_p_b": res_b["config"]["top_p"],
            "latency_b_ms": res_b["latency_ms"],
            "out_tokens_b": res_b["output_tokens"],
            "output_b": res_b["output"][:280]
        })

    st.session_state.history.append(entry)
    log_to_file(entry)

def render_result(res):
    if not res:
        return

    st.markdown("### Response")
    st.markdown(
        f"""
        <div style='background:#11151f;padding:1rem;border-radius:8px;
        border:1px solid #2d3748;white-space:pre-wrap;'>
        {res['output']}
        </div>
        """,
        unsafe_allow_html=True
    )

    cols = st.columns(4)
    cols[0].metric("Latency (ms)", res["latency_ms"])
    cols[1].metric("Input Tokens", res["input_tokens"])
    cols[2].metric("Output Tokens", res["output_tokens"])
    cols[3].markdown(
        f"**Temp:** {res['config']['temperature']}  \n"
        f"**Top-p:** {res['config']['top_p']}  \n"
        f"**Sampling:** {'Yes' if res['config']['do_sample'] else 'No'}"
    )

# ==========================================================
# SESSION STATE
# ==========================================================

if "history" not in st.session_state:
    st.session_state.history = []

if "last_single" not in st.session_state:
    st.session_state.last_single = None

if "last_a" not in st.session_state:
    st.session_state.last_a = None

if "last_b" not in st.session_state:
    st.session_state.last_b = None

if "drift_flag" not in st.session_state:
    st.session_state.drift_flag = "stable"

# ==========================================================
# HEADER & STATUS BAR
# ==========================================================

status_label = {
    "stable": "🟢 Stable",
    "warning": "🟡 Drift Detected",
    "critical": "🔴 Major Drift"
}[st.session_state.drift_flag]

st.markdown(f"""
<div class="status-bar">
    <div>AI Command Center • Live</div>
    <div class="badge">{status_label}</div>
</div>
""", unsafe_allow_html=True)


tab1, tab2 = st.tabs(["Research & Compare", "Stability Regression Suite"])

with tab1:
    left_panel, right_panel = st.columns([1, 1.2], gap="large")

    with left_panel:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        prompt_input = st.text_area("Prompt", height=160, key="main_prompt")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        temp = st.slider("Temperature", 0.0, 2.0, 0.7, 0.05, key="main_temp")
        top_p = st.slider("Top-p", 0.0, 1.0, 0.9, 0.05, key="main_topp")
        max_tokens = st.number_input("Max Tokens", 64, 4096, 512, key="main_max")
        st.markdown('</div>', unsafe_allow_html=True)

        run = st.button("🚀 Execute Inference", type="primary", use_container_width=True)

        if run:
            result = run_inference(prompt_input, temp, top_p, max_tokens, True)
            if result:
                st.session_state.last_single = result
                append_history("single", prompt_input, res_a=result)

    with right_panel:
        result = st.session_state.last_single
        if result:
            st.markdown('<div class="card">', unsafe_allow_html=True)

            st.markdown(
                f'<div class="output-box">{result["output"]}</div>',
                unsafe_allow_html=True
            )

            st.markdown(f"""
            <div class="metric-hud">
                <div class="metric-box">
                    <div class="metric-label">Latency</div>
                    <div class="metric-value">{result['latency_ms']} ms</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Tokens</div>
                    <div class="metric-value">{result['input_tokens']} / {result['output_tokens']}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">Temperature</div>
                    <div class="metric-value">{result['config']['temperature']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

    # HISTORY
    with st.expander("Experiment History", expanded=False):
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.download_button(
                "↓ Export JSON",
                data=json.dumps(st.session_state.history, indent=2, ensure_ascii=False),
                file_name=f"research_log_{datetime.now():%Y%m%d_%H%M}.json",
                mime="application/json"
            )
        else:
            st.info("No experiments yet.")

with tab2:
    st.subheader("🧪 Stability Regression Suite")

    col1, col2 = st.columns(2)

    with col1:
        stable_temp = st.slider("Temperature (locked)", 0.0, 2.0, 0.7, 0.05, key="stab_temp")

    with col2:
        stable_top_p = st.slider("Top-p (locked)", 0.0, 1.0, 0.9, 0.05, key="stab_topp")

    stable_max_tokens = st.number_input("Max Tokens (locked)", 64, 4096, 512, key="stab_max")

    if st.button("🚀 Run Stability Suite", use_container_width=True):

        snapshots = load_snapshots()
        previous_snapshot = snapshots[-1] if snapshots else None

        current_snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "config": {
                "temperature": stable_temp,
                "top_p": stable_top_p,
                "max_tokens": stable_max_tokens
            },
            "results": []
        }

        for test in TEST_SUITE:
            test_res = run_inference(
                test["prompt"],
                stable_temp,
                stable_top_p,
                stable_max_tokens,
                True
            )

            if test_res:
                current_snapshot["results"].append({
                    "name": test["name"],
                    "prompt": test["prompt"],
                    "output": test_res["output"],
                    "latency_ms": test_res["latency_ms"] if isinstance(test_res["latency_ms"], (int, float)) else 0,
                    "input_tokens": test_res["input_tokens"] if isinstance(test_res["input_tokens"], (int, float)) else 0,
                    "output_tokens": test_res["output_tokens"] if isinstance(test_res["output_tokens"], (int, float)) else 0
                })

        # Save snapshot
        with open(SNAPSHOT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(current_snapshot, ensure_ascii=False) + "\n")

        st.success("Snapshot saved.")

        # ===============================
        # Drift Comparison
        # ===============================

        if previous_snapshot:
            st.divider()
            st.subheader("📊 Drift vs Previous Snapshot")

            drift_rows = []
            
            # Reset drift flag before calculation
            st.session_state.drift_flag = "stable"

            for i, new_res in enumerate(current_snapshot["results"]):
                if i < len(previous_snapshot["results"]):
                    old_res = previous_snapshot["results"][i]

                    latency_delta = new_res["latency_ms"] - old_res.get("latency_ms", 0)
                    token_delta = new_res["output_tokens"] - old_res.get("output_tokens", 0)
                    length_delta = len(new_res["output"]) - len(old_res.get("output", ""))

                    drift_rows.append({
                        "Test": new_res["name"],
                        "Latency Δ (ms)": round(latency_delta, 1),
                        "Output Tokens Δ": token_delta,
                        "Text Length Δ": length_delta
                    })

                    # Update drift flag safely
                    try:
                        lat_val = float(latency_delta)
                        tok_val = float(token_delta)
                        if abs(lat_val) > 300:
                            st.session_state.drift_flag = "warning"
                        if abs(tok_val) > 100:
                            st.session_state.drift_flag = "critical"
                    except Exception:
                        pass

            df = pd.DataFrame(drift_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Basic Alerting
            if st.session_state.drift_flag == "warning":
                st.warning("⚠️ Significant latency drift detected.")
            elif st.session_state.drift_flag == "critical":
                st.error("🔴 Major verbosity/token drift detected.")

            st.divider()

            # Side-by-side view
            for i, new_res in enumerate(current_snapshot["results"]):
                if i < len(previous_snapshot["results"]):
                    old_res = previous_snapshot["results"][i]

                    st.markdown(f"### {new_res['name']}")

                    col_old, col_new = st.columns(2)

                    with col_old:
                        st.caption("Previous")
                        st.markdown(
                            f"<div style='background:#11151f;padding:1rem;border-radius:8px;border:1px solid #2d3748;white-space:pre-wrap;'>{old_res.get('output', '')}</div>",
                            unsafe_allow_html=True
                        )

                    with col_new:
                        st.caption("Current")
                        st.markdown(
                            f"<div style='background:#11151f;padding:1rem;border-radius:8px;border:1px solid #2d3748;white-space:pre-wrap;'>{new_res['output']}</div>",
                            unsafe_allow_html=True
                        )

                    st.divider()
            
            # Auto-rerun if status changed
            st.rerun()

        else:
            st.info("No previous snapshot found. Run suite again to enable drift comparison.")
