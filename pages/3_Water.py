from pathlib import Path
import os
import tempfile

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Water Analysis", page_icon="💧", layout="wide")

# Resolve the project root from this file: <project>/pages/3_Water.py

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DATA_FILE = DATA_DIR / "water.csv"
#DATA_FILE = Path.home() / "Downloads" / "water.csv"

COLUMNS = [
    "record_id", "date", "city", "population",
    "supply_ml", "consumption_ml", "quality_index"
]
CITIES = ["Kochi", "Trivandrum", "Kozhikode", "Thrissur"]


def load_water_data():
    if not DATA_FILE.exists():
        st.error(f"Cannot find the dataset at: {DATA_FILE}")
        st.info("Place water.csv inside the project's data folder.")
        st.stop()

    try:
        df = pd.read_csv(DATA_FILE)
    except Exception as exc:
        st.error(f"Could not read water.csv: {exc}")
        st.stop()

    missing = [column for column in COLUMNS if column not in df.columns]
    if missing:
        st.error("water.csv is missing required columns: " + ", ".join(missing))
        st.stop()

    df = df[COLUMNS].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for column in ["population", "supply_ml", "consumption_ml", "quality_index"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=COLUMNS)
    df["record_id"] = df["record_id"].astype(str)
    df["city"] = df["city"].astype(str)
    df["population"] = df["population"].astype(int)
    df["quality_index"] = df["quality_index"].round().astype(int)
    return df


def save_water_data(df):
    """Write CSV atomically so an interrupted write is less likely to corrupt it."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="water_", suffix=".csv", dir=DATA_DIR)
    os.close(fd)
    try:
        df[COLUMNS].to_csv(temp_name, index=False, date_format="%Y-%m-%d")
        os.replace(temp_name, DATA_FILE)
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


if "water_data" not in st.session_state:
    st.session_state.water_data = load_water_data()

df = st.session_state.water_data.copy()
if df.empty:
    st.warning("There are no valid records in water.csv yet.")
    st.stop()

st.title("💧 Water Analysis")
st.caption("Synthetic demonstration data • 2025 • Four cities")
st.warning(
    "These are synthetic records, not official water measurements. "
    "The quality index is a project-defined score from 0–100; it is not a "
    "regulatory water-quality index and does not establish drinking-water safety."
)

# Sidebar filters
st.sidebar.header("Filter data")
available_cities = sorted(df["city"].dropna().unique().tolist())
selected_cities = st.sidebar.multiselect(
    "Select city/cities", available_cities, default=available_cities
)
min_date = df["date"].min().date()
max_date = df["date"].max().date()
date_range = st.sidebar.date_input(
    "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)

filtered = df[df["city"].isin(selected_cities)].copy()
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["date"].dt.date.between(start_date, end_date)
    ]

if filtered.empty:
    st.info("No records match the selected filters. Choose another city or date range.")
    st.stop()

# Derived metric: consumption_ml is ML/day, so multiply by 1,000,000 to convert to litres.
filtered["per_capita_lpd"] = (
    filtered["consumption_ml"] * 1_000_000 / filtered["population"]
)
filtered["supply_gap_ml"] = filtered["supply_ml"] - filtered["consumption_ml"]
filtered["month"] = filtered["date"].dt.to_period("M").dt.to_timestamp()

total_supply = filtered["supply_ml"].sum()
total_consumption = filtered["consumption_ml"].sum()
avg_per_capita = filtered["per_capita_lpd"].mean()
avg_quality = filtered["quality_index"].mean()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total recorded supply", f"{total_supply:,.1f} ML")
m2.metric("Total recorded consumption", f"{total_consumption:,.1f} ML")
m3.metric("Average per-capita use", f"{avg_per_capita:,.1f} L/person/day")
m4.metric("Average quality score", f"{avg_quality:.1f}/100")

st.caption(
    "Supply and consumption totals sum daily ML/day records across the selected "
    "dates and cities; they are dataset-period totals, not a single-day rate."
)

# Monthly supply vs consumption
st.subheader("Supply vs. consumption by month")
monthly = (
    filtered.groupby(["month", "city"], as_index=False)[["supply_ml", "consumption_ml"]]
    .mean()
    .melt(
        id_vars=["month", "city"],
        value_vars=["supply_ml", "consumption_ml"],
        var_name="measure",
        value_name="average_ml_per_day",
    )
)
monthly["measure"] = monthly["measure"].map({
    "supply_ml": "Average supply",
    "consumption_ml": "Average consumption",
})
fig_supply = px.bar(
    monthly, x="month", y="average_ml_per_day", color="measure",
    barmode="group", facet_col="city", facet_col_wrap=2,
    labels={"month": "Month", "average_ml_per_day": "Average ML/day", "measure": "Measure"},
)
fig_supply.update_layout(legend_title_text="", height=560)
st.plotly_chart(fig_supply, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("Water quality score trend")
    quality_daily = filtered.groupby(["date", "city"], as_index=False)["quality_index"].mean()
    fig_quality = px.line(
        quality_daily, x="date", y="quality_index", color="city",
        labels={"date": "Date", "quality_index": "Synthetic quality score (0–100)", "city": "City"},
    )
    fig_quality.update_yaxes(range=[0, 100])
    st.plotly_chart(fig_quality, use_container_width=True)

with right:
    st.subheader("Average per-capita use by city")
    per_city = (
        filtered.groupby("city", as_index=False)["per_capita_lpd"]
        .mean()
        .sort_values("per_capita_lpd", ascending=False)
    )
    fig_pc = px.bar(
        per_city, x="city", y="per_capita_lpd", color="city",
        labels={"city": "City", "per_capita_lpd": "Litres/person/day"},
    )
    fig_pc.update_layout(showlegend=False)
    st.plotly_chart(fig_pc, use_container_width=True)

# Additional useful statistics
st.subheader("Key statistics")
s1, s2, s3 = st.columns(3)
s1.metric("Days/city records in view", f"{len(filtered):,}")
s2.metric("Days with supply below consumption", f"{int((filtered['supply_gap_ml'] < 0).sum()):,}")
s3.metric("Largest average daily supply gap", f"{filtered.groupby('city')['supply_gap_ml'].mean().min():.2f} ML/day")

with st.expander("View filtered water records", expanded=True):
    display_df = filtered[COLUMNS].copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# CRUD section
st.divider()
st.subheader("Manage water records")
st.caption("Changes are saved to data/water.csv. Keep a backup before editing project data.")

tab_add, tab_update, tab_delete = st.tabs(["➕ Add record", "✏️ Update record", "🗑️ Delete record"])

with tab_add:
    with st.form("add_water_record", clear_on_submit=True):
        c1, c2 = st.columns(2)
        new_id = c1.text_input("Record ID", placeholder="e.g. W2000")
        new_date = c2.date_input("Date", value=max_date)
        c3, c4 = st.columns(2)
        new_city = c3.selectbox("City", CITIES)
        new_population = c4.number_input("Population", min_value=1, value=500000, step=1000)
        c5, c6, c7 = st.columns(3)
        new_supply = c5.number_input("Supply (ML/day)", min_value=0.01, value=75.0, step=1.0)
        new_consumption = c6.number_input("Consumption (ML/day)", min_value=0.01, value=70.0, step=1.0)
        new_quality = c7.number_input("Quality score (0–100)", min_value=0, max_value=100, value=82, step=1)
        submitted = st.form_submit_button("Add record")
    if submitted:
        new_id = new_id.strip()
        if not new_id:
            st.error("Record ID cannot be blank.")
        elif df["record_id"].astype(str).str.casefold().eq(new_id.casefold()).any():
            st.error("That record ID already exists. Use a unique ID.")
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
            updated = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            try:
                save_water_data(updated)
                st.session_state.water_data = updated
                st.success("Record added. Reloading the page…")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save record: {exc}")

with tab_update:
    if df.empty:
        st.info("No records to update.")
    else:
        record_to_update = st.selectbox("Choose record ID to update", df["record_id"].tolist(), key="update_id")
        old = df.loc[df["record_id"] == record_to_update].iloc[0]
        with st.form("update_water_record"):
            u1, u2 = st.columns(2)
            upd_date = u1.date_input("Date", value=old["date"].date(), key="upd_date")
            city_options = CITIES if old["city"] in CITIES else CITIES + [old["city"]]
            upd_city = u2.selectbox("City", city_options, index=city_options.index(old["city"]), key="upd_city")
            u3, u4 = st.columns(2)
            upd_population = u3.number_input("Population", min_value=1, value=int(old["population"]), step=1000, key="upd_pop")
            upd_supply = u4.number_input("Supply (ML/day)", min_value=0.01, value=float(old["supply_ml"]), step=1.0, key="upd_supply")
            u5, u6 = st.columns(2)
            upd_consumption = u5.number_input("Consumption (ML/day)", min_value=0.01, value=float(old["consumption_ml"]), step=1.0, key="upd_cons")
            upd_quality = u6.number_input("Quality score (0–100)", min_value=0, max_value=100, value=int(old["quality_index"]), step=1, key="upd_quality")
            update_submitted = st.form_submit_button("Save changes")
        if update_submitted:
            updated = df.copy()
            mask = updated["record_id"] == record_to_update
            updated.loc[mask, "date"] = pd.Timestamp(upd_date)
            updated.loc[mask, "city"] = upd_city
            updated.loc[mask, "population"] = int(upd_population)
            updated.loc[mask, "supply_ml"] = float(upd_supply)
            updated.loc[mask, "consumption_ml"] = float(upd_consumption)
            updated.loc[mask, "quality_index"] = int(upd_quality)
            try:
                save_water_data(updated)
                st.session_state.water_data = updated
                st.success("Record updated. Reloading the page…")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not update record: {exc}")

with tab_delete:
    if df.empty:
        st.info("No records to delete.")
    else:
        record_to_delete = st.selectbox("Choose record ID to delete", df["record_id"].tolist(), key="delete_id")
        confirm_delete = st.checkbox(f"I confirm deletion of {record_to_delete}", key="confirm_delete")
        if st.button("Delete selected record", type="primary", disabled=not confirm_delete):
            updated = df[df["record_id"] != record_to_delete].copy()
            try:
                save_water_data(updated)
                st.session_state.water_data = updated
                st.success("Record deleted. Reloading the page…")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not delete record: {exc}")

# Download current complete dataset
st.divider()
st.subheader("Export")
export_df = st.session_state.water_data.copy()
export_df["date"] = pd.to_datetime(export_df["date"]).dt.strftime("%Y-%m-%d")
st.download_button(
    "Download current water.csv",
    data=export_df[COLUMNS].to_csv(index=False).encode("utf-8"),
    file_name="water.csv",
    mime="text/csv",
)
