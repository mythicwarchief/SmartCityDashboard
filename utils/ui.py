
"""Shared UI styling and page headers for the Smart City Dashboard."""

import streamlit as st


PALETTE = {
    "Air Quality": "#0F9D8A",
    "Traffic": "#D99A27",
    "Water": "#3987D7",
    "Energy": "#8B6BD6",
}


def apply_page_style():
    """Apply consistent styling across all dashboard pages."""

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1440px;
            padding-top: 1.8rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            letter-spacing: -0.025em;
        }

        [data-testid="stMetric"] {
            background: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.20);
            border-radius: 14px;
            padding: 1.05rem 1.2rem;
            min-height: 108px;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.88rem;
        }

        [data-testid="stMetricValue"] {
            font-size: clamp(1.35rem, 2vw, 2rem);
            font-weight: 650;
        }

        [data-testid="stTabs"] [role="tab"] {
            padding: 0.72rem 0.95rem;
            font-weight: 550;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 12px;
            overflow: hidden;
        }

        div[data-testid="stForm"] {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 14px;
            padding: 1.15rem;
        }

        div.stButton > button,
        div.stDownloadButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            border-radius: 9px;
            font-weight: 600;
            min-height: 2.55rem;
            transition: border-color 0.2s ease;
        }

        div.stButton > button:hover,
        div.stDownloadButton > button:hover {
            border-color: #3987D7;
        }

        [data-testid="stAlert"] {
            border-radius: 12px;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(128, 128, 128, 0.16);
        }

        [data-testid="stPlotlyChart"] {
            border: 1px solid rgba(128, 128, 128, 0.15);
            border-radius: 14px;
            padding: 0.25rem;
        }

        [data-testid="stExpander"] {
            border-radius: 12px;
        }

        @media (max-width: 768px) {
            .block-container {
                padding: 1rem 0.8rem 2rem;
            }

            [data-testid="stMetric"] {
                padding: 0.75rem;
                min-height: 88px;
            }

            [data-testid="stMetricValue"] {
                font-size: 1.3rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def render_page_header(title, subtitle, icon, accent):
    st.markdown(
        f"## {icon} {title}\n\n{subtitle}"
    )

