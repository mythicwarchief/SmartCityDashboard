
"""Smart City Dashboard — Kerala urban intelligence platform."""

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Smart City Dashboard | Kerala",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Shared visual styling
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    :root {
        --city-navy: #14283F;
        --city-teal: #16A895;
        --city-muted: #77869A;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F3F6FA 0%, #EAF0F6 100%);
        border-right: 1px solid #DCE4EC;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.4rem;
    }

    .brand-card {
        padding: 1rem 0.85rem 1.15rem 0.85rem;
        border-radius: 16px;
        background: linear-gradient(135deg, #14283F 0%, #24516A 100%);
        color: white;
        margin-bottom: 1.25rem;
    }

    .brand-row {
        display: flex;
        align-items: center;
        gap: 0.7rem;
    }

    .brand-icon {
        width: 42px;
        height: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        background: rgba(255,255,255,0.12);
        font-size: 1.45rem;
    }

    .brand-name {
        font-size: 1.04rem;
        font-weight: 750;
        letter-spacing: -0.025em;
        line-height: 1.25;
    }

    .brand-subtitle {
        margin-top: 0.2rem;
        font-size: 0.74rem;
        color: #D4E3EF;
    }

    .brand-location {
        margin-top: 0.9rem;
        padding-top: 0.75rem;
        border-top: 1px solid rgba(255,255,255,0.16);
        color: #C5D8E6;
        font-size: 0.75rem;
        letter-spacing: 0.035em;
    }

    .side-section {
        margin: 1.2rem 0 0.55rem 0;
        color: #748399;
        font-size: 0.69rem;
        font-weight: 750;
        letter-spacing: 0.12em;
    }

    .side-note {
        padding: 0.85rem 0.9rem;
        border: 1px solid #DCE5EC;
        border-radius: 12px;
        background: rgba(255,255,255,0.72);
        color: #536479;
        font-size: 0.82rem;
        line-height: 1.55;
    }

    .side-note strong {
        color: #20364D;
    }

    [data-testid="stSidebar"] hr {
        margin: 1.1rem 0;
        border-color: #D8E1E9;
    }

    [data-testid="stSidebar"] [data-testid="stMetric"] {
        background: rgba(255,255,255,0.72);
        border: 1px solid #DCE5EC;
        border-radius: 12px;
        padding: 0.65rem 0.8rem;
    }

    .hero {
        padding: 2.25rem 2.2rem;
        border-radius: 20px;
        background: linear-gradient(115deg, #14283F 0%, #24546D 100%);
        color: white;
        margin-bottom: 1.8rem;
        border-bottom: 4px solid #16A895;
    }

    .hero-eyebrow {
        color: #8BE2D5;
        font-size: 0.73rem;
        font-weight: 750;
        letter-spacing: 0.15em;
        margin-bottom: 0.7rem;
    }

    .hero-title {
        font-size: clamp(2rem, 4vw, 2.8rem);
        line-height: 1.12;
        font-weight: 800;
        letter-spacing: -0.045em;
        margin: 0;
    }

    .hero-description {
        color: #DCEAF2;
        font-size: 1rem;
        line-height: 1.65;
        max-width: 760px;
        margin-top: 0.8rem;
    }

    .module-card {
        padding: 1.2rem;
        border: 1px solid #E0E7ED;
        border-radius: 16px;
        background: var(--background-color);
        min-height: 150px;
    }

    .module-icon {
        font-size: 1.6rem;
        margin-bottom: 0.65rem;
    }

    .module-title {
        font-size: 1.08rem;
        font-weight: 750;
        color: var(--text-color);
        margin-bottom: 0.35rem;
    }

    .module-description {
        font-size: 0.87rem;
        color: var(--city-muted);
        line-height: 1.5;
    }

    @media (max-width: 768px) {
        .hero {
            padding: 1.5rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Sidebar branding
# ---------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="brand-card">
            <div class="brand-row">
                <div class="brand-icon">🏙️</div>
                <div>
                    <div class="brand-name">Smart City</div>
                    <div class="brand-subtitle">Urban Intelligence Platform</div>
                </div>
            </div>
            <div class="brand-location">
                ◉ &nbsp; KERALA, INDIA
            </div>
        </div>

        <div class="side-section">NAVIGATION</div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("Choose a page from the navigation menu above.")

    st.markdown(
        """
        <div class="side-section">CITY COVERAGE</div>
        <div class="side-note">
            <strong>📍 Kochi</strong><br>
            <strong>📍 Trivandrum</strong><br>
            <strong>📍 Kozhikode</strong><br>
            <strong>📍 Thrissur</strong>
        </div>

        <div class="side-section">PLATFORM MODULES</div>
        <div class="side-note">
            🌫️ &nbsp; Air quality monitoring<br>
            🚦 &nbsp; Traffic analysis<br>
            💧 &nbsp; Water management<br>
            ⚡ &nbsp; Energy intelligence
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.caption("Smart City Dashboard · Academic Project")


# ---------------------------------------------------------
# Count records safely from the existing CSV files
# ---------------------------------------------------------
def count_records(filename):
    path = ROOT / "data" / filename

    if not path.exists():
        return None

    try:
        return len(pd.read_csv(path))
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <div class="hero-eyebrow">URBAN INTELLIGENCE &nbsp; / &nbsp; KERALA</div>
        <h1 class="hero-title">Smart City Dashboard</h1>
        <div class="hero-description">
            One place to explore urban air quality, traffic, water, and
            energy indicators across four cities in Kerala.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Your city at a glance")
st.caption(
    "Choose a module to explore its data, manage records, visualize trends, "
    "and generate reports."
)

air_count = count_records("air_quality.csv")
traffic_count = count_records("traffic.csv")
water_count = count_records("water.csv")
energy_count = count_records("energy.csv")

metric_columns = st.columns(4)

metrics = [
    ("🌫️ Air Quality", air_count),
    ("🚦 Traffic", traffic_count),
    ("💧 Water", water_count),
    ("⚡ Energy", energy_count),
]

for column, (label, count) in zip(metric_columns, metrics):
    with column:
        value = f"{count:,}" if count is not None else "—"
        st.metric(label, value)

st.markdown("---")
st.subheader("Explore the modules")

modules = [
    (
        "🌫️",
        "Air Quality",
        "Explore AQI, pollutant levels, trends, and air-quality records.",
        "#0F9D8A",
    ),
    (
        "🚦",
        "Traffic",
        "Review congestion, vehicle counts, speeds, and traffic trends.",
        "#D99A27",
    ),
    (
        "💧",
        "Water",
        "Explore water supply, consumption, and project-defined quality scores.",
        "#3987D7",
    ),
    (
        "⚡",
        "Energy",
        "Review energy consumption, renewable share, and peak demand.",
        "#8B6BD6",
    ),
]

for start in range(0, len(modules), 2):
    columns = st.columns(2)

    for column, module in zip(columns, modules[start:start + 2]):
        icon, title, description, accent = module

        with column:
            st.markdown(
                f"""
                <div class="module-card"
                     style="border-top: 3px solid {accent};">
                    <div class="module-icon">{icon}</div>
                    <div class="module-title">{title}</div>
                    <div class="module-description">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.write("")

st.caption(
    "Data note: record counts reflect CSV rows. The presence of records "
    "does not establish that the underlying measurements are live or official."
)
