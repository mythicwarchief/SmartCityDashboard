
"""Water dashboard: polished UI, analytics, record management and export."""

from pathlib import Path
import os
import sys
import tempfile

import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.ui import apply_page_style, render_page_header


DATA_DIR = PROJECT_ROOT / "data"
DATA_FILE = DATA_DIR / "water.csv"

COLUMNS = [
    "record_id",
    "date",
    "city",
    "population",
    "supply_ml",
    "consumption_ml",
    "quality_index",
]

CITIES = ["Kochi", "Trivandrum", "Kozhikode", "Thrissur"]


st.set_page_config(
    page_title="Water | Smart City Dashboard",
    page_icon="💧",
    layout="wide",
)

apply_page_style()

render_page_header(
    "Water Resource Intelligence",
    "Monitor water supply, consumption, quality scores and per-capita "
    "usage across four cities in Kerala.",
    "💧",
    "#3987D7",
)


# ------------------------------------------------------------
# DATA MANAGEMENT
# ------------------------------------------------------------

def load_water_data():
    """Load and validate the water dataset."""

    if not DATA_FILE.exists():
        st.error(f"Cannot find the dataset at: {DATA_FILE}")
        st.info("Place water.csv inside the project's data folder.")

        if st.button(
            "Create an empty water.csv",
            type="primary",
        ):
            empty_df = pd.DataFrame(columns=COLUMNS)
            try:
                save_water_data(empty_df)
                st.session_state.water_data = empty_df.copy()
                st.success("Created water.csv. Add your first record below.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not create water.csv: {exc}")

        st.stop()

    try:
        df = pd.read_csv(DATA_FILE)
    except Exception as exc:
        st.error(f"Could not read water.csv: {exc}")
        st.stop()

    missing = [column for column in COLUMNS if column not in df.columns]

    if missing:
        st.error(
            "water.csv is missing required columns: "
            + ", ".join(missing)
        )
        st.stop()

    df = df[COLUMNS].copy()

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    for column in [
        "population",
        "supply_ml",
        "consumption_ml",
        "quality_index",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # Preserve the existing behavior: invalid rows are excluded.
    df = df.dropna(subset=COLUMNS).copy()

    df["record_id"] = df["record_id"].astype(str)
    df["city"] = df["city"].astype(str)
    df["population"] = df["population"].astype(int)
    df["quality_index"] = df["quality_index"].round().astype(int)

    return df


def save_water_data(df):
    """Write CSV atomically to reduce the risk of file corruption."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        prefix="water_",
        suffix=".csv",
        dir=DATA_DIR,
    )

    os.close(fd)

    try:
        df[COLUMNS].to_csv(
            temp_name,
            index=False,
            date_format="%Y-%m-%d",
        )

        os.replace(temp_name, DATA_FILE)

    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


if "water_data" not in st.session_state:
    st.session_state.water_data = load_water_data()

df = st.session_state.water_data.copy()

# ------------------------------------------------------------
# DATA TRANSPARENCY
# ------------------------------------------------------------

st.warning(
    "**Data transparency:** These are synthetic demonstration records, "
    "not official water measurements. The quality index is a project-defined "
    "score from 0–100. It is not a regulatory water-quality index and does "
    "not establish whether water is safe to drink."
)

if df.empty:
    st.info(
        "There are no valid records in water.csv yet. "
        "Use the record-management section to add your first record."
    )

    # Allow the user to add data even when the dataset is empty.
    min_date = pd.Timestamp.today().normalize().date()
    max_date = min_date
    available_cities = CITIES.copy()

else:
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    available_cities = sorted(df["city"].dropna().unique().tolist())


# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------

st.sidebar.markdown("## 💧 Water Controls")
st.sidebar.caption("Adjust the filters to update the dashboard.")

selected_cities = st.sidebar.multiselect(
    "Select cities",
    available_cities,
    default=available_cities,
)

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# ------------------------------------------------------------
# FILTER DATA
# ------------------------------------------------------------

filtered = df[df["city"].isin(selected_cities)].copy()

if (
    isinstance(date_range, (tuple, list))
    and len(date_range) == 2
):
    start_date, end_date = date_range

    filtered = filtered[
        filtered["date"].dt.date.between(
            start_date,
            end_date,
        )
    ]

if filtered.empty:
    st.info(
        "No records match the selected filters. "
        "Choose another city or date range."
    )

    st.markdown("### Manage water records")

    st.caption(
        "You can still add, update or delete records below."
    )

else:
    # --------------------------------------------------------
    # DERIVED METRICS
    # --------------------------------------------------------

    filtered["per_capita_lpd"] = (
        filtered["consumption_ml"]
        * 1_000_000
        / filtered["population"]
    )

    filtered["supply_gap_ml"] = (
        filtered["supply_ml"]
        - filtered["consumption_ml"]
    )

    filtered["month"] = (
        filtered["date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    total_supply = filtered["supply_ml"].sum()
    total_consumption = filtered["consumption_ml"].sum()
    avg_per_capita = filtered["per_capita_lpd"].mean()
    avg_quality = filtered["quality_index"].mean()

    # --------------------------------------------------------
    # KPI CARDS
    # --------------------------------------------------------

    st.markdown("### Water resource overview")

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Recorded supply",
        f"{total_supply:,.1f} ML",
        help="Sum of supply values across the selected records.",
    )

    m2.metric(
        "Recorded consumption",
        f"{total_consumption:,.1f} ML",
        help="Sum of consumption values across the selected records.",
    )

    m3.metric(
        "Per-capita usage",
        f"{avg_per_capita:,.1f} L/day",
        help="Average calculated litres per person per day.",
    )

    m4.metric(
        "Average quality score",
        f"{avg_quality:.1f}/100",
        help="Synthetic, project-defined quality score.",
    )

    st.caption(
        "Supply and consumption totals sum daily ML/day records across "
        "the selected dates and cities. They represent dataset-period "
        "totals, not a single-day rate."
    )

    # --------------------------------------------------------
    # MONTHLY SUPPLY VS CONSUMPTION
    # --------------------------------------------------------

    st.divider()
    st.markdown("### Supply vs. consumption")
    st.caption(
        "Compare average daily supply and consumption by month and city."
    )

    monthly = (
        filtered.groupby(
            ["month", "city"],
            as_index=False,
        )[["supply_ml", "consumption_ml"]]
        .mean()
        .melt(
            id_vars=["month", "city"],
            value_vars=["supply_ml", "consumption_ml"],
            var_name="measure",
            value_name="average_ml_per_day",
        )
    )

    monthly["measure"] = monthly["measure"].map(
        {
            "supply_ml": "Average supply",
            "consumption_ml": "Average consumption",
        }
    )

    fig_supply = px.bar(
        monthly,
        x="month",
        y="average_ml_per_day",
        color="measure",
        barmode="group",
        facet_col="city",
        facet_col_wrap=2,
        labels={
            "month": "Month",
            "average_ml_per_day": "Average ML/day",
            "measure": "Measure",
            "city": "City",
        },
        color_discrete_sequence=["#3987D7", "#48B89A"],
    )

    fig_supply.update_layout(
        title="Monthly water supply and consumption",
        title_x=0.03,
        legend_title_text="",
        height=560,
        margin=dict(l=20, r=20, t=80, b=20),
    )

    st.plotly_chart(
        fig_supply,
        use_container_width=True,
    )

    # --------------------------------------------------------
    # QUALITY AND PER-CAPITA CHARTS
    # --------------------------------------------------------

    left, right = st.columns(2)

    with left:
        st.markdown("### Water quality trend")
        st.caption("Synthetic quality scores over time.")

        quality_daily = (
            filtered.groupby(
                ["date", "city"],
                as_index=False,
            )["quality_index"]
            .mean()
        )

        fig_quality = px.line(
            quality_daily,
            x="date",
            y="quality_index",
            color="city",
            markers=True,
            labels={
                "date": "Date",
                "quality_index": "Synthetic quality score (0–100)",
                "city": "City",
            },
            color_discrete_sequence=[
                "#3987D7",
                "#48B89A",
                "#D99A27",
                "#8B6BD6",
            ],
        )

        fig_quality.update_yaxes(range=[0, 100])

        fig_quality.update_layout(
            title="Quality score over time",
            title_x=0.03,
            margin=dict(l=15, r=15, t=60, b=15),
        )

        st.plotly_chart(
            fig_quality,
            use_container_width=True,
        )

    with right:
        st.markdown("### Per-capita water use")
        st.caption("Compare average daily usage by city.")

        per_city = (
            filtered.groupby(
                "city",
                as_index=False,
            )["per_capita_lpd"]
            .mean()
            .sort_values(
                "per_capita_lpd",
                ascending=False,
            )
        )

        fig_pc = px.bar(
            per_city,
            x="city",
            y="per_capita_lpd",
            color="city",
            labels={
                "city": "City",
                "per_capita_lpd": "Litres/person/day",
            },
            color_discrete_sequence=[
                "#3987D7",
                "#48B89A",
                "#D99A27",
                "#8B6BD6",
            ],
        )

        fig_pc.update_layout(
            title="Average per-capita usage by city",
            title_x=0.03,
            showlegend=False,
            margin=dict(l=15, r=15, t=60, b=15),
        )

        st.plotly_chart(
            fig_pc,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # KEY STATISTICS
    # --------------------------------------------------------

    st.divider()
    st.markdown("### Key statistics")

    s1, s2, s3 = st.columns(3)

    s1.metric(
        "Records in view",
        f"{len(filtered):,}",
    )

    s2.metric(
        "Records where supply is below consumption",
        f"{int((filtered['supply_gap_ml'] < 0).sum()):,}",
    )

    average_gap_by_city = (
        filtered.groupby("city")["supply_gap_ml"].mean()
    )

    s3.metric(
        "Largest average supply deficit",
        f"{average_gap_by_city.min():.2f} ML/day",
        help=(
            "The lowest average supply-minus-consumption value among "
            "the cities in the selected records. A negative value "
            "indicates consumption exceeds supply."
        ),
    )

    # --------------------------------------------------------
    # FILTERED DATA TABLE
    # --------------------------------------------------------

    with st.expander(
        "📋 View filtered water records",
        expanded=True,
    ):
        display_df = filtered[COLUMNS].copy()

        display_df["date"] = (
            display_df["date"].dt.strftime("%Y-%m-%d")
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "⬇️ Download filtered records",
            data=display_df.to_csv(index=False).encode("utf-8"),
            file_name="water_filtered.csv",
            mime="text/csv",
        )


# ============================================================
# RECORD MANAGEMENT
# ============================================================

st.divider()
st.markdown("### Manage water records")

st.caption(
    "Changes are saved to data/water.csv. "
    "Keep a backup before editing project data."
)

tab_add, tab_update, tab_delete = st.tabs(
    [
        "➕ Add record",
        "✏️ Update record",
        "🗑️ Delete record",
    ]
)

# ------------------------------------------------------------
# ADD RECORD
# ------------------------------------------------------------

with tab_add:
    st.subheader("Add a water record")

    with st.form(
        "add_water_record",
        clear_on_submit=True,
    ):
        c1, c2 = st.columns(2)

        new_id = c1.text_input(
            "Record ID",
            placeholder="e.g. W2000",
        )

        new_date = c2.date_input(
            "Date",
            value=max_date,
        )

        c3, c4 = st.columns(2)

        new_city = c3.selectbox(
            "City",
            CITIES,
        )

        new_population = c4.number_input(
            "Population",
            min_value=1,
            value=500000,
            step=1000,
        )

        c5, c6, c7 = st.columns(3)

        new_supply = c5.number_input(
            "Supply (ML/day)",
            min_value=0.01,
            value=75.0,
            step=1.0,
        )

        new_consumption = c6.number_input(
            "Consumption (ML/day)",
            min_value=0.01,
            value=70.0,
            step=1.0,
        )

        new_quality = c7.number_input(
            "Quality score (0–100)",
            min_value=0,
            max_value=100,
            value=82,
            step=1,
        )

        submitted = st.form_submit_button(
            "➕ Add water record",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        new_id = new_id.strip()

        current_df = st.session_state.water_data.copy()

        if not new_id:
            st.error("Record ID cannot be blank.")

        elif current_df["record_id"].astype(str).str.casefold().eq(
            new_id.casefold()
        ).any():
            st.error(
                "That record ID already exists. Please use a unique ID."
            )

        elif new_city not in CITIES:
            st.error("Choose one of the four supported cities.")

        else:
            new_row = {
                "record_id": new_id,
                "date": pd.Timestamp(new_date),
                "city": new_city,
                "population": int(new_population),
                "supply_ml": float(new_supply),
                "consumption_ml": float(new_consumption),
                "quality_index": int(new_quality),
            }

            updated = pd.concat(
                [
                    current_df,
                    pd.DataFrame([new_row]),
                ],
                ignore_index=True,
            )

            try:
                save_water_data(updated)
                st.session_state.water_data = updated
                st.success("Water record added successfully.")
                st.rerun()

            except Exception as exc:
                st.error(f"Could not save record: {exc}")


# ------------------------------------------------------------
# UPDATE RECORD
# ------------------------------------------------------------

with tab_update:
    current_df = st.session_state.water_data.copy()

    if current_df.empty:
        st.info("No records are available to update.")

    else:
        record_to_update = st.selectbox(
            "Choose record ID to update",
            current_df["record_id"].tolist(),
            key="update_id",
        )

        old = current_df.loc[
            current_df["record_id"] == record_to_update
        ].iloc[0]

        with st.form("update_water_record"):
            u1, u2 = st.columns(2)

            upd_date = u1.date_input(
                "Date",
                value=old["date"].date(),
                key="upd_date",
            )

            city_options = (
                CITIES
                if old["city"] in CITIES
                else CITIES + [old["city"]]
            )

            upd_city = u2.selectbox(
                "City",
                city_options,
                index=city_options.index(old["city"]),
                key="upd_city",
            )

            u3, u4 = st.columns(2)

            upd_population = u3.number_input(
                "Population",
                min_value=1,
                value=int(old["population"]),
                step=1000,
                key="upd_pop",
            )

            upd_supply = u4.number_input(
                "Supply (ML/day)",
                min_value=0.01,
                value=float(old["supply_ml"]),
                step=1.0,
                key="upd_supply",
            )

            u5, u6 = st.columns(2)

            upd_consumption = u5.number_input(
                "Consumption (ML/day)",
                min_value=0.01,
                value=float(old["consumption_ml"]),
                step=1.0,
                key="upd_cons",
            )

            upd_quality = u6.number_input(
                "Quality score (0–100)",
                min_value=0,
                max_value=100,
                value=int(old["quality_index"]),
                step=1,
                key="upd_quality",
            )

            update_submitted = st.form_submit_button(
                "💾 Save changes",
                type="primary",
                use_container_width=True,
            )

        if update_submitted:
            updated = current_df.copy()

            mask = (
                updated["record_id"] == record_to_update
            )

            updated.loc[mask, "date"] = pd.Timestamp(upd_date)
            updated.loc[mask, "city"] = upd_city
            updated.loc[mask, "population"] = int(upd_population)
            updated.loc[mask, "supply_ml"] = float(upd_supply)
            updated.loc[mask, "consumption_ml"] = float(
                upd_consumption
            )
            updated.loc[mask, "quality_index"] = int(upd_quality)

            try:
                save_water_data(updated)
                st.session_state.water_data = updated
                st.success("Water record updated successfully.")
                st.rerun()

            except Exception as exc:
                st.error(f"Could not update record: {exc}")


# ------------------------------------------------------------
# DELETE RECORD
# ------------------------------------------------------------

with tab_delete:
    current_df = st.session_state.water_data.copy()

    if current_df.empty:
        st.info("No records are available to delete.")

    else:
        record_to_delete = st.selectbox(
            "Choose record ID to delete",
            current_df["record_id"].tolist(),
            key="delete_id",
        )

        record = current_df.loc[
            current_df["record_id"] == record_to_delete
        ].iloc[0]

        st.warning(
            f"**Record {record_to_delete}**\n\n"
            f"- City: {record['city']}\n"
            f"- Date: {record['date'].date()}\n"
            f"- Supply: {record['supply_ml']:.2f} ML/day\n"
            f"- Consumption: {record['consumption_ml']:.2f} ML/day"
        )

        confirm_delete = st.checkbox(
            f"I confirm deletion of record {record_to_delete}.",
            key="confirm_delete",
        )

        if st.button(
            "🗑️ Delete selected record",
            type="primary",
            disabled=not confirm_delete,
        ):
            updated = current_df[
                current_df["record_id"] != record_to_delete
            ].copy()

            try:
                save_water_data(updated)
                st.session_state.water_data = updated
                st.success("Water record deleted successfully.")
                st.rerun()

            except Exception as exc:
                st.error(f"Could not delete record: {exc}")


# ============================================================
# EXPORT COMPLETE DATASET
# ============================================================

st.divider()
st.markdown("### Export water dataset")

export_df = st.session_state.water_data.copy()

if not export_df.empty:
    export_df["date"] = (
        pd.to_datetime(export_df["date"])
        .dt.strftime("%Y-%m-%d")
    )

st.caption(
    f"Export the current complete dataset ({len(export_df):,} records)."
)

st.download_button(
    "⬇️ Download current water.csv",
    data=export_df[COLUMNS].to_csv(index=False).encode("utf-8"),
    file_name="water.csv",
    mime="text/csv",
    use_container_width=True,
)

st.divider()

st.caption(
    "SMART CITY DASHBOARD · WATER MODULE · "
    "Synthetic demonstration data for four Kerala cities"
)
