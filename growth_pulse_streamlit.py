"""
Growth Pulse — TACHBULAH GROW tool (Python / Streamlit version)

Same tool, same scoring logic as the React version — rewritten in Python
so you can compare the two languages side by side.

To run this on your own machine:
    pip install streamlit pandas plotly
    streamlit run growth_pulse_streamlit.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------- Page setup ----------
st.set_page_config(page_title="Growth Pulse", layout="centered")

st.markdown(
    """
    <style>
        .stApp { background-color: #101820; color: #EDE8DD; }
        [data-testid="stMetricValue"] { color: #EDE8DD; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.caption("TACHBULAH · GROW")
st.title("Growth Pulse")
st.caption(
    "Enter revenue and costs for each year to see how the business is actually doing."
)

SAMPLE = [
    {"revenue": 100, "cost": 82},
    {"revenue": 112, "cost": 90},
    {"revenue": 126, "cost": 102},
    {"revenue": 138, "cost": 118},
    {"revenue": 150, "cost": 140},
]


# ---------- Scoring functions ----------
# These four functions are the exact same logic as the JS version —
# just written with Python's `def name(args):` + indentation instead
# of JS's `function name(args) { }`.

def clamp_map(value, x1, y1, x2, y2):
    """Map `value` from the range [x1, x2] onto [y1, y2], clamped at the ends."""
    if x1 == x2:
        return y1
    t = (value - x1) / (x2 - x1)
    t = max(0, min(1, t))  # clamp t between 0 and 1
    return y1 + t * (y2 - y1)


def profitability_score(margin):
    if margin <= 0:
        return 0
    if margin >= 0.25:
        return 100
    return clamp_map(margin, 0, 0, 0.25, 100)


def three_point_score(v):
    """Used for both Revenue Growth and Cost Discipline scores."""
    if v <= -0.1:
        return 0
    if v <= 0:
        return clamp_map(v, -0.1, 0, 0, 50)
    if v <= 0.1:
        return clamp_map(v, 0, 50, 0.1, 100)
    return 100


def cagr(first, last, n):
    if not first or first <= 0 or n <= 1:
        return 0
    return (last / first) ** (1 / (n - 1)) - 1


# ---------- Inputs ----------
years = st.number_input("Years of data", min_value=2, max_value=10, value=5, step=1)

# st.session_state is Streamlit's equivalent of React's useState —
# it's how data survives between re-runs of the script.
if "data" not in st.session_state:
    st.session_state.data = SAMPLE.copy()

col1, col2, _ = st.columns([1, 1, 3])
if col1.button("Load sample"):
    st.session_state.data = SAMPLE.copy()
if col2.button("Clear all"):
    st.session_state.data = [{"revenue": 0, "cost": 0} for _ in range(years)]

# Pad or trim to match the chosen number of years
data = st.session_state.data
if len(data) < years:
    data = data + [{"revenue": 0, "cost": 0}] * (years - len(data))
else:
    data = data[:years]
st.session_state.data = data

# ---------- Editable table ----------
df = pd.DataFrame(st.session_state.data)
df.index = [f"Y{i + 1}" for i in range(len(df))]
edited = st.data_editor(df, use_container_width=True, key="editor")

# ---------- Derived calculations ----------
# Nothing here is stored separately — it's all recalculated from
# `edited` every time the app re-runs, same as the `rows`/`total`
# variables in the React version.
edited["profit"] = edited["revenue"] - edited["cost"]
edited["margin"] = edited.apply(
    lambda r: r["profit"] / r["revenue"] if r["revenue"] else 0, axis=1
)

n = len(edited)
rev_cagr = cagr(edited["revenue"].iloc[0], edited["revenue"].iloc[-1], n)
cost_cagr = cagr(edited["cost"].iloc[0], edited["cost"].iloc[-1], n)
avg_margin = edited["margin"].mean()
profitable_years = int((edited["profit"] > 0).sum())

s_profitability = profitability_score(avg_margin)
s_revenue = three_point_score(rev_cagr)
s_cost_eff = three_point_score(rev_cagr - cost_cagr)
s_consistency = (profitable_years / n) * 100

components = [
    ("Profitability", 0.35, s_profitability),
    ("Revenue Growth", 0.25, s_revenue),
    ("Cost Discipline", 0.25, s_cost_eff),
    ("Consistency", 0.15, s_consistency),
]
total = sum(weight * score for _, weight, score in components)

if total >= 80:
    band, color = "THRIVING", "green"
elif total >= 60:
    band, color = "HEALTHY", "orange"
elif total >= 40:
    band, color = "FRAGILE", "orange"
else:
    band, color = "AT RISK", "red"

if s_cost_eff < 45 and s_revenue >= 50:
    narrative = "Revenue is growing, but costs are growing faster — margins are being squeezed."
elif s_profitability < 45:
    narrative = "Margins are thin or negative — costs are consuming most of what the business earns."
elif s_consistency < 50:
    narrative = "Profitability swings year to year — some good years are covering for weaker ones."
elif s_revenue < 45:
    narrative = "Revenue growth has stalled — the top line isn't expanding much year over year."
else:
    narrative = "Growth, cost discipline and profitability are all moving in the right direction."

# ---------- Chart ----------
fig = go.Figure()
fig.add_trace(go.Scatter(x=edited.index, y=edited["revenue"], name="Revenue",
                          line=dict(color="#C9A227", width=2), fill="tozeroy"))
fig.add_trace(go.Scatter(x=edited.index, y=edited["cost"], name="Cost",
                          line=dict(color="#C1524B", width=2), fill="tozeroy"))
fig.add_trace(go.Scatter(x=edited.index, y=edited["profit"], name="Profit",
                          line=dict(color="#8FBF7F", width=2, dash="dash")))
fig.update_layout(
    paper_bgcolor="#101820",
    plot_bgcolor="#101820",
    font_color="#EDE8DD",
    height=320,
    margin=dict(t=20, l=0, r=0, b=0),
    legend=dict(orientation="h", y=1.1),
)
st.plotly_chart(fig, use_container_width=True)

# ---------- Score tally ----------
st.subheader("Health Score Tally")
tally_df = pd.DataFrame(
    [
        (label, f"×{int(w * 100)}%", f"{s:.0f}", f"{w * s:.1f}")
        for label, w, s in components
    ],
    columns=["Signal", "Weight", "Score", "Contribution"],
)
st.table(tally_df)

st.markdown(f"## {total:.0f} — :{color}[{band}]")
st.write(narrative)
