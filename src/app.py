import re
from pathlib import Path

import pandas as pd
import streamlit as st

from metrics import load_data, calculate_metrics, aggregate_campaign_level
from prompt_builder import build_compact_text, build_prompt
from groq_client import generate_response


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="AdIntel Copilot",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -----------------------------
# Utility helpers
# -----------------------------
def get_data_path() -> Path:
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    return project_root / "data" / "synthetic_campaigns.csv"


def format_percent(x):
    return f"{x:.2%}"


def format_number(x):
    return f"{x:,.0f}"


def format_currency(x):
    return f"${x:,.2f}"


def assign_dna_tag(row):
    if row["ROI"] > 2.0 and row["CPA"] < 25:
        return "Scaler 🚀"
    elif row["ROI"] < 0:
        return "Budget Leaker ⚠️"
    elif row["CTR"] > 0.05 and row["CVR"] < 0.045:
        return "Attention Trap 👀"
    elif row["CVR"] > 0.07:
        return "Conversion Engine 🎯"
    else:
        return "Steady Performer ✅"


def get_risk_level(row):
    if row["ROI"] < 0 or row["CPA"] > 50:
        return "High"
    elif row["ROI"] < 1.0 or row["CVR"] < 0.04:
        return "Medium"
    return "Low"


def style_table(df: pd.DataFrame):
    styled_df = df.copy()
    styled_df["Click-Through Rate (CTR)"] = styled_df["Click-Through Rate (CTR)"].apply(format_percent)
    styled_df["Conversion Rate (CVR)"] = styled_df["Conversion Rate (CVR)"].apply(format_percent)
    styled_df["Cost Per Acquisition (CPA)"] = styled_df["Cost Per Acquisition (CPA)"].apply(format_currency)
    styled_df["Return on Investment (ROI)"] = styled_df["Return on Investment (ROI)"].apply(lambda x: f"{x:.2f}x")
    styled_df["Impressions"] = styled_df["Impressions"].apply(format_number)
    styled_df["Clicks"] = styled_df["Clicks"].apply(format_number)
    styled_df["Conversions"] = styled_df["Conversions"].apply(format_number)
    styled_df["Spend"] = styled_df["Spend"].apply(format_currency)
    styled_df["Revenue"] = styled_df["Revenue"].apply(format_currency)
    return styled_df


def format_bullets(text: str) -> str:
    cleaned_lines = []

    for line in text.split("\n"):
        line = line.strip()

        if not line:
            continue

        line = re.sub(r"^\d+\.\s*", "", line)
        line = re.sub(r"^[-•]\s*", "", line)
        line = re.sub(r"\*\*", "", line)
        line = line.strip(" :-")

        if len(line) < 4:
            continue

        lower_line = line.lower()
        if lower_line in {
            "growth marketer",
            "finance analyst",
            "risk analyst",
            "final recommendation",
            "executive decision",
            "final strategic recommendation",
        }:
            continue

        cleaned_lines.append(line)

    if not cleaned_lines:
        return "<ul><li>No output generated.</li></ul>"

    return "<ul>" + "".join(f"<li>{line}</li>" for line in cleaned_lines) + "</ul>"


def parse_debate_output(text: str):
    final_patterns = [
        r"Final Strategic Recommendation:\s*(.*)$",
        r"Executive Decision:\s*(.*)$",
        r"Final Recommendation:\s*(.*)$",
    ]

    executive_text = ""
    for pattern in final_patterns:
        match = re.search(pattern, text, flags=re.S | re.I)
        if match:
            executive_text = match.group(1).strip()
            break

    debate_text = text
    for pattern in final_patterns:
        debate_text = re.sub(pattern, "", debate_text, flags=re.S | re.I).strip()

    debate_text = re.sub(r"^Debate Transcript:\s*", "", debate_text, flags=re.I).strip()

    return debate_text, executive_text


def render_chat_bubbles(debate_text: str):
    lines = [line.strip() for line in debate_text.split("\n") if line.strip()]
    valid = ["growth marketer", "finance analyst", "risk analyst"]

    for line in lines:
        if ":" not in line:
            continue

        speaker, message = line.split(":", 1)
        speaker_clean = speaker.strip().lower()

        if speaker_clean not in valid:
            continue

        message = message.strip()

        if speaker_clean == "growth marketer":
            color = "#e0f2fe"
            border = "#0284c7"
            icon = "📈"
            label = "Growth Marketer"
        elif speaker_clean == "finance analyst":
            color = "#ecfdf5"
            border = "#059669"
            icon = "💰"
            label = "Finance Analyst"
        else:
            color = "#fff7ed"
            border = "#ea580c"
            icon = "⚠️"
            label = "Risk Analyst"

        st.markdown(
            f"""
            <div style="
                background:{color};
                color:#0f172a;
                padding:14px 16px;
                border-radius:16px;
                margin-bottom:10px;
                border-left:6px solid {border};">
                <b>{icon} {label}</b><br>{message}
            </div>
            """,
            unsafe_allow_html=True
        )


def fallback_recommendation(df: pd.DataFrame) -> str:
    scale_row = df.sort_values("ROI", ascending=False).iloc[0]

    cut_candidates = df[df["campaign_name"] != scale_row["campaign_name"]].copy()
    cut_row = cut_candidates.sort_values(["ROI", "CPA"], ascending=[True, False]).iloc[0]

    scale_text = (
        f"Scale: {scale_row['campaign_name']} | "
        f"Reason: highest ROI in selected set with favorable efficiency signals."
    )

    cut_text = (
        f"Cut/Optimize: {cut_row['campaign_name']} | "
        f"Reason: weakest return or inefficient spend in selected set."
    )

    return scale_text + "\n" + cut_text


def recommendation_is_broken(executive_text: str) -> bool:
    if not executive_text or executive_text.strip() == "":
        return True

    lowered = executive_text.lower()

    if lowered.count("not the one to cut") > 0:
        return True

    if lowered.count("however") > 6:
        return True

    for phrase in [
        "video awareness sprint",
        "brand display push",
        "spring search boost",
        "retargeting revival",
        "email lead funnel",
        "prospecting test",
    ]:
        if lowered.count(phrase) > 8:
            return True

    if "scale:" not in lowered or "cut/optimize:" not in lowered:
        return True

    return False


# -----------------------------
# Custom styling
# -----------------------------
st.markdown(
    """
    <style>
        .main {
            padding-top: 1rem;
        }

        [data-testid="stSidebar"] {
            background-color: #f4f6f9;
        }

        .hero-box {
            background: linear-gradient(135deg, #081225 0%, #0a1730 45%, #172d5a 100%);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 24px;
            padding: 30px 32px 24px 32px;
            margin-bottom: 18px;
            box-shadow: 0 10px 26px rgba(0,0,0,0.16);
        }

        .hero-title {
            font-size: 2.35rem;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 0.3rem;
            letter-spacing: -0.5px;
        }

        .hero-subtitle {
            font-size: 1.08rem;
            color: #dbe4f0;
            margin-bottom: 1rem;
        }

        .hero-body {
            color: #edf2f7;
            font-size: 1rem;
            line-height: 1.75;
            margin-bottom: 0.8rem;
        }

        .hero-pill {
            display: inline-block;
            padding: 0.38rem 0.78rem;
            margin: 0.2rem 0.35rem 0.2rem 0;
            border-radius: 999px;
            background: rgba(255,255,255,0.08);
            color: #f8fafc;
            font-size: 0.86rem;
            border: 1px solid rgba(255,255,255,0.08);
        }

        .metric-card {
            background: #081225;
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 18px;
            padding: 18px;
            min-height: 112px;
        }

        .metric-label {
            color: #a8b3c7;
            font-size: 0.88rem;
            margin-bottom: 0.35rem;
        }

        .metric-value {
            color: #f8fafc;
            font-size: 1.65rem;
            font-weight: 780;
        }

        .section-title {
            font-size: 1.2rem;
            font-weight: 800;
            color: #111827;
            margin-top: 0.25rem;
            margin-bottom: 0.75rem;
        }

        .card-title {
            font-size: 1.2rem;
            font-weight: 800;
            color: #ffffff;
            margin-top: 0.25rem;
            margin-bottom: 0.75rem;
        }

        .final-card {
            background: linear-gradient(135deg, #09152b 0%, #172d63 100%);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 18px;
            padding: 22px;
            margin-top: 10px;
        }

        .small-caption {
            color: #d9e1ee;
            font-size: 0.95rem;
            line-height: 1.75;
        }

        .small-caption ul {
            margin-top: 0.15rem;
            margin-bottom: 0.2rem;
            padding-left: 1.1rem;
        }

        .small-caption li {
            margin-bottom: 0.45rem;
        }

        .signal-card-success,
        .signal-card-warning,
        .signal-card-danger {
            border-radius: 14px;
            padding: 14px 16px;
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 10px;
        }

        .signal-card-success {
            background: rgba(16, 185, 129, 0.10);
            border: 1px solid rgba(16, 185, 129, 0.25);
            color: #065f46;
        }

        .signal-card-warning {
            background: rgba(245, 158, 11, 0.10);
            border: 1px solid rgba(245, 158, 11, 0.25);
            color: #92400e;
        }

        .signal-card-danger {
            background: rgba(239, 68, 68, 0.10);
            border: 1px solid rgba(239, 68, 68, 0.22);
            color: #991b1b;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Load and prepare data
# -----------------------------
data_path = get_data_path()

df = load_data(str(data_path))
df = calculate_metrics(df)
agg = aggregate_campaign_level(df)

agg["DNA Tag"] = agg.apply(assign_dna_tag, axis=1)
agg["Risk Level"] = agg.apply(get_risk_level, axis=1)


# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.title("AdIntel Controls")

selected_channels = st.sidebar.multiselect(
    "Filter by channel",
    options=sorted(agg["channel"].unique().tolist()),
    default=sorted(agg["channel"].unique().tolist())
)

selected_campaigns = st.sidebar.multiselect(
    "Filter by campaign",
    options=agg["campaign_name"].tolist(),
    default=agg["campaign_name"].tolist()
)

sort_by = st.sidebar.selectbox(
    "Sort campaigns by",
    options=["ROI", "CPA", "CTR", "CVR", "spend", "revenue"],
    index=0
)

top_n = st.sidebar.slider(
    "Campaigns to send into AI debate",
    min_value=2,
    max_value=min(4, len(agg)),
    value=min(3, len(agg))
)

show_prompt = st.sidebar.checkbox("Show AI prompt payload", value=False)

filtered = agg[
    agg["channel"].isin(selected_channels) &
    agg["campaign_name"].isin(selected_campaigns)
].copy()

ascending = True if sort_by == "CPA" else False
filtered = filtered.sort_values(by=sort_by, ascending=ascending)

if filtered.empty:
    st.warning("No campaigns match the selected filters.")
    st.stop()

llm_input_df = filtered.head(top_n).copy()


# -----------------------------
# Hero section
# -----------------------------
st.markdown(
    """
    <div class="hero-box">
        <div class="hero-title">AdIntel Copilot</div>
        <div class="hero-subtitle">AI Marketing Decision Simulator</div>
        <div class="hero-body">
            Campaign performance doesn’t fail because of bad data — it fails because teams can’t agree on what to do next.
            <br><br>
            In real organizations, <b>Growth Team</b> wants to scale, <b>Finance Team</b> wants efficiency, and <b>Risk Team</b> wants stability.
            The same campaign can look promising to one team and dangerous to another.
            <br><br>
            AdIntel Copilot simulates that real-world tension by turning campaign metrics into a short & structured stakeholder debate,
            helping teams move from conflicting interpretations to a clear, defensible action plan.
        </div>
        <span class="hero-pill">Cross-Functional Alignment</span>
        <span class="hero-pill">Stakeholder Debate Simulation</span>
        <span class="hero-pill">Decision Friction Reduction</span>
        <span class="hero-pill">Actionable Recommendations</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption("Built to reduce decision friction when Growth, Finance, and Risk teams interpret the same campaign differently.")

st.markdown(
    """
    <div style="color:#94a3b8; font-size:0.95rem; margin-bottom:16px;">
        <b>Real problem:</b> teams don’t struggle with seeing campaign data — they struggle with agreeing on what action to take.<br>
        <b>AdIntel Copilot</b> helps resolve that conflict faster through structured AI-simulated debate.
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# KPI cards
# -----------------------------
total_spend = filtered["spend"].sum()
total_revenue = filtered["revenue"].sum()
overall_roi = (total_revenue - total_spend) / total_spend if total_spend else 0
best_campaign = filtered.sort_values("ROI", ascending=False).iloc[0]["campaign_name"]
high_risk_count = (filtered["Risk Level"] == "High").sum()

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Total Spend</div>
            <div class="metric-value">{format_currency(total_spend)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Total Revenue</div>
            <div class="metric-value">{format_currency(total_revenue)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Portfolio ROI</div>
            <div class="metric-value">{overall_roi:.2f}x</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Top ROI Campaign</div>
            <div class="metric-value" style="font-size:1.12rem;">{best_campaign}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("### ⚡ Key Signals")

top_scaler = filtered.sort_values("ROI", ascending=False).iloc[0]
worst_campaign = filtered.sort_values("ROI", ascending=True).iloc[0]
highest_cpa = filtered.sort_values("CPA", ascending=False).iloc[0]

sig1, sig2, sig3 = st.columns(3)

with sig1:
    st.markdown(
        f'<div class="signal-card-success">🚀 Scale Candidate: {top_scaler["campaign_name"]}</div>',
        unsafe_allow_html=True
    )

with sig2:
    st.markdown(
        f'<div class="signal-card-danger">⚠️ Budget Risk: {worst_campaign["campaign_name"]}</div>',
        unsafe_allow_html=True
    )

with sig3:
    st.markdown(
        f'<div class="signal-card-warning">💸 Inefficient Spend: {highest_cpa["campaign_name"]}</div>',
        unsafe_allow_html=True
    )


# -----------------------------
# Data overview
# -----------------------------
left, right = st.columns([1.65, 1])

with left:
    st.markdown('<div class="section-title">📊 Campaign Performance Overview</div>', unsafe_allow_html=True)

    display_df = filtered.copy().rename(columns={
        "campaign_name": "Campaign Name",
        "channel": "Channel",
        "impressions": "Impressions",
        "clicks": "Clicks",
        "conversions": "Conversions",
        "spend": "Spend",
        "revenue": "Revenue",
        "CTR": "Click-Through Rate (CTR)",
        "CVR": "Conversion Rate (CVR)",
        "CPA": "Cost Per Acquisition (CPA)",
        "ROI": "Return on Investment (ROI)",
    })

    display_cols = [
        "Campaign Name",
        "Channel",
        "Impressions",
        "Clicks",
        "Conversions",
        "Spend",
        "Revenue",
        "Click-Through Rate (CTR)",
        "Conversion Rate (CVR)",
        "Cost Per Acquisition (CPA)",
        "Return on Investment (ROI)",
        "DNA Tag",
        "Risk Level",
    ]

    st.dataframe(
        style_table(display_df[display_cols]),
        use_container_width=True,
        hide_index=True
    )

with right:
    st.markdown('<div class="section-title">🧬 Campaign Signals</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">High-Risk Campaigns</div>
            <div class="metric-value">{high_risk_count}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("**Current AI input set**")
    st.caption(f"Top {top_n} campaigns by selected sort logic will be sent into the debate engine.")

    signal_preview = llm_input_df[["campaign_name", "DNA Tag", "Risk Level"]].copy()
    signal_preview = signal_preview.rename(columns={"campaign_name": "Campaign Name"})
    st.dataframe(signal_preview, use_container_width=True, hide_index=True)


# -----------------------------
# Prompt section
# -----------------------------
compact_text = build_compact_text(llm_input_df)
prompt = build_prompt(compact_text)

if show_prompt:
    st.markdown('<div class="section-title">📝 Prompt Payload</div>', unsafe_allow_html=True)
    st.code(prompt, language="text")


# -----------------------------
# Debate / Recommendation
# -----------------------------
st.markdown("---")
st.markdown('<div class="section-title">🧠 Copilot Debate Mode</div>', unsafe_allow_html=True)
st.caption("Generate Growth, Finance, and Risk viewpoints, then synthesize a final action plan.")

run = st.button("🚀 Generate Strategic Analysis", use_container_width=True)

if run:
    with st.spinner("Generating stakeholder analysis..."):
        raw_response = generate_response(prompt)

    debate_text, executive_text = parse_debate_output(raw_response)

    if recommendation_is_broken(executive_text):
        executive_text = fallback_recommendation(llm_input_df)

    st.markdown("### 🎙️ Simulated Boardroom Debate")
    st.caption(f"Debating top {top_n} campaigns based on {sort_by}.")

    render_chat_bubbles(debate_text)

    st.markdown(
        f"""
        <div class="final-card">
            <div class="card-title">🎯 Final Strategic Recommendation</div>
            <div class="small-caption">{format_bullets(executive_text)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("See raw model output"):
        st.write(raw_response)

else:
    st.info("Run the debate engine to generate a live multi-persona strategy discussion.")
