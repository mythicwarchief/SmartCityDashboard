"""Page 4 - Energy (owner: Kiran S Nair).

Reads and writes only data/energy.csv through EnergyManager.
"""
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.energy import CITIES, EnergyManager

DATA_FILE = ROOT / "data" / "energy.csv"

st.set_page_config(page_title="Energy | Smart City Dashboard", page_icon="⚡", layout="wide")


def flash(level: str, message: str) -> None:
    """Keep an action result visible across a Streamlit rerun."""
    st.session_state["energy_flash"] = (level, message)


def show_flash() -> None:
    message = st.session_state.pop("energy_flash", None)
    if message:
        getattr(st, message[0])(message[1])


def numeric_value(value, default: float) -> float:
    return default if pd.isna(value) else float(value)


st.title("Energy")
st.caption("Track energy consumption, renewable sources and peak demand across four Kerala cities.")
st.caption("Starter readings are illustrative modeled data, not metered utility readings.")
show_flash()

manager = EnergyManager(DATA_FILE)
loaded, load_message = manager.load()

if manager.load_status == "missing":
    st.error(load_message)
    if st.button("Create an empty energy.csv with the correct headers"):
        ok, message = manager.create_empty_file()
        flash("success" if ok else "error", message)
        st.rerun()
    st.stop()
if not loaded:
    st.error(load_message)
    st.info("Fix or replace data/energy.csv and reload this page.")
    st.stop()
if manager.load_status == "empty":
    st.warning(load_message)

all_data = manager.data
st.info("**Missing data (NaN) handling:** rows with missing values are flagged; each statistic and chart uses only rows with the values it needs. Missing values are not imputed.")

st.sidebar.header("Filters")
selected_cities = st.sidebar.multiselect("City", CITIES, default=CITIES)
if all_data["date"].notna().any():
    min_date = all_data["date"].min().date()
    max_date = all_data["date"].max().date()
else:
    min_date = max_date = date.today()
picked_range = st.sidebar.date_input("Date range", (min_date, max_date))
date_range = tuple(picked_range) if isinstance(picked_range, (tuple, list)) and len(picked_range) == 2 else None
if date_range is None:
    st.sidebar.info("Choose an end date to apply the date filter.")

filtered = manager.filter_data(selected_cities, date_range)
summary = manager.energy_summary(filtered)
metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric("Records (filtered / total)", f"{len(filtered)} / {len(all_data)}")
metric_2.metric("Consumption", f"{summary['consumption_mwh']:,.1f} MWh" if summary else "n/a")
metric_3.metric("Renewable share", f"{summary['renewable_percent']:.1f}%" if summary else "n/a")
metric_4.metric("Maximum peak demand", f"{summary['max_peak_demand_mw']:.2f} MW" if summary else "n/a")

tab_view, tab_add, tab_edit, tab_delete, tab_charts, tab_report = st.tabs(
    ["View Data", "Add Record", "Edit Record", "Delete Record", "Charts and Insights", "Report"]
)

with tab_view:
    search = st.text_input("Search (any column)", placeholder="e.g. Kochi, 2024-06", key="energy_search")
    sort_column = st.selectbox("Sort by", manager.columns, index=1)
    ascending = st.radio("Order", ["Ascending", "Descending"], horizontal=True) == "Ascending"
    view_data = manager.filter_data(selected_cities, date_range, search)
    if sort_column in view_data.columns:
        view_data = view_data.sort_values(sort_column, ascending=ascending, na_position="last")
    st.write(f"Showing **{len(view_data)}** of {len(all_data)} records")
    st.dataframe(view_data, hide_index=True, width="stretch")

    st.subheader("Summary statistics")
    left, middle, right = st.columns(3)
    with left:
        st.markdown("**Consumption and renewable share by city**")
        city_summary = manager.consumption_by_city(view_data)
        st.dataframe(city_summary, hide_index=True, width="stretch")
    with middle:
        st.markdown("**Selected-period energy summary**")
        stats = manager.energy_summary(view_data)
        if stats:
            st.write(f"Consumption: {stats['consumption_mwh']:,.1f} MWh")
            st.write(f"Renewable: {stats['renewable_mwh']:,.1f} MWh ({stats['renewable_percent']:.1f}%)")
            st.write(f"Non-renewable: {stats['non_renewable_mwh']:,.1f} MWh")
        else:
            st.write("No complete consumption data.")
    with right:
        st.markdown("**Peak demand**")
        peak = manager.peak_demand_record(view_data)
        st.write(f"{peak['value']:.2f} MW in {peak['city']} on {peak['date']}" if peak else "No peak-demand data.")
        st.write(f"Mean peak demand: {stats['mean_peak_demand_mw']:.2f} MW" if stats else "")

    missing_rows = manager.flagged_rows(view_data)
    with st.expander(f"Rows flagged for missing values ({len(missing_rows)})"):
        if missing_rows.empty:
            st.write("No missing values in the current view.")
        else:
            st.write("Missing cells per column:", manager.nan_counts(view_data).to_dict())
            st.dataframe(missing_rows, hide_index=True, width="stretch")

with tab_add:
    st.subheader("Add an energy reading")
    with st.form("energy_add_form"):
        col_1, col_2 = st.columns(2)
        new_id = col_1.number_input("Record ID", min_value=1, value=manager.next_id(), step=1)
        new_date = col_2.date_input("Date", value=date.today())
        new_city = col_1.selectbox("City", CITIES)
        consumption = col_2.number_input("Consumption (MWh)", min_value=0.0, value=100.0, step=1.0)
        renewable = col_1.number_input("Renewable energy (MWh)", min_value=0.0, value=40.0, step=1.0)
        non_renewable = col_2.number_input("Non-renewable energy (MWh)", min_value=0.0, value=60.0, step=1.0)
        peak_demand = col_1.number_input("Peak demand (MW)", min_value=0.0, value=5.0, step=0.1)
        st.caption("Renewable and non-renewable energy must sum to total consumption.")
        add_clicked = st.form_submit_button("Add record")
    if add_clicked:
        ok, message = manager.create({
            "record_id": new_id,
            "date": new_date,
            "city": new_city,
            "consumption_mwh": consumption,
            "renewable_mwh": renewable,
            "non_renewable_mwh": non_renewable,
            "peak_demand_mw": peak_demand,
        })
        if ok:
            flash("success", message)
            st.rerun()
        else:
            st.error(message)

with tab_edit:
    st.subheader("Edit an energy reading")
    if all_data.empty:
        st.info("There are no records to edit yet.")
    else:
        valid_ids = all_data["record_id"].dropna()
        if valid_ids.empty:
            st.error("No valid record IDs are available to edit.")
        else:
            edit_id = st.number_input("Record ID to edit", min_value=1, value=int(valid_ids.min()), step=1, key="energy_edit_id")
            record = manager.get_record(edit_id)
            if record is None:
                st.error(f"Record not found: there is no record with ID {edit_id}.")
            else:
                form_key = f"energy_edit_form_{edit_id}"
                with st.form(form_key):
                    st.write(f"Editing record **{edit_id}** (the ID cannot be changed)")
                    col_1, col_2 = st.columns(2)
                    stored_date = record["date"].date() if pd.notna(record["date"]) else date.today()
                    edit_date = col_1.date_input("Date", value=stored_date, key=f"energy_edit_date_{edit_id}")
                    edit_city = col_2.selectbox("City", CITIES, index=CITIES.index(record["city"]) if record["city"] in CITIES else 0,
                                                key=f"energy_edit_city_{edit_id}")
                    edit_consumption = col_1.number_input("Consumption (MWh)", min_value=0.0,
                        value=numeric_value(record["consumption_mwh"], 100.0), step=1.0, key=f"energy_edit_consumption_{edit_id}")
                    edit_renewable = col_2.number_input("Renewable energy (MWh)", min_value=0.0,
                        value=numeric_value(record["renewable_mwh"], 40.0), step=1.0, key=f"energy_edit_renewable_{edit_id}")
                    edit_non_renewable = col_1.number_input("Non-renewable energy (MWh)", min_value=0.0,
                        value=numeric_value(record["non_renewable_mwh"], 60.0), step=1.0, key=f"energy_edit_nonrenewable_{edit_id}")
                    edit_peak = col_2.number_input("Peak demand (MW)", min_value=0.0,
                        value=numeric_value(record["peak_demand_mw"], 5.0), step=0.1, key=f"energy_edit_peak_{edit_id}")
                    save_clicked = st.form_submit_button("Save changes")
                if save_clicked:
                    ok, message = manager.update(edit_id, {
                        "date": edit_date,
                        "city": edit_city,
                        "consumption_mwh": edit_consumption,
                        "renewable_mwh": edit_renewable,
                        "non_renewable_mwh": edit_non_renewable,
                        "peak_demand_mw": edit_peak,
                    })
                    if ok:
                        flash("success", message)
                        st.rerun()
                    else:
                        st.error(message)

with tab_delete:
    st.subheader("Delete an energy reading")
    if all_data.empty:
        st.info("There are no records to delete yet.")
    else:
        valid_ids = all_data["record_id"].dropna()
        if valid_ids.empty:
            st.error("No valid record IDs are available to delete.")
        else:
            delete_id = st.number_input("Record ID to delete", min_value=1, value=int(valid_ids.min()), step=1, key="energy_delete_id")
            record = manager.get_record(delete_id)
            if record is None:
                st.error(f"Record not found: there is no record with ID {delete_id}.")
            else:
                st.dataframe(pd.DataFrame([record]), hide_index=True, width="stretch")
                if st.session_state.get("energy_pending_delete") != delete_id:
                    if st.button("Delete this record"):
                        st.session_state["energy_pending_delete"] = delete_id
                        st.rerun()
                else:
                    st.warning(f"Are you sure you want to delete record {delete_id}?")
                    confirm, cancel, _ = st.columns([1, 1, 4])
                    if confirm.button("Yes, delete", type="primary"):
                        ok, message = manager.delete(delete_id)
                        st.session_state.pop("energy_pending_delete", None)
                        flash("success" if ok else "error", message)
                        st.rerun()
                    if cancel.button("Cancel"):
                        st.session_state.pop("energy_pending_delete", None)
                        st.rerun()

with tab_charts:
    st.subheader("Charts and insights")
    chart_data = filtered.dropna(subset=["date", "consumption_mwh", "renewable_mwh", "non_renewable_mwh"])
    if chart_data.empty:
        st.info("No complete Energy data is available for the current filters.")
    else:
        monthly = manager.monthly_energy(filtered)
        if not monthly.empty:
            st.plotly_chart(px.line(monthly, x="month", y="consumption_mwh", color="city", markers=True,
                                    title="Monthly energy consumption by city",
                                    labels={"month": "Month", "consumption_mwh": "Consumption (MWh)"}),
                            width="stretch")
            chart_1, chart_2 = st.columns(2)
            sources = monthly.groupby("city", as_index=False)[["renewable_mwh", "non_renewable_mwh"]].sum()
            melted = sources.melt(id_vars="city", var_name="source", value_name="energy_mwh")
            melted["source"] = melted["source"].map({"renewable_mwh": "Renewable", "non_renewable_mwh": "Non-renewable"})
            chart_1.plotly_chart(px.bar(melted, x="city", y="energy_mwh", color="source", barmode="stack",
                                        title="Renewable vs non-renewable energy",
                                        labels={"energy_mwh": "Energy (MWh)", "source": "Source"}),
                                width="stretch")
            if monthly["peak_demand_mw"].notna().any():
                chart_2.plotly_chart(px.line(monthly, x="month", y="peak_demand_mw", color="city", markers=True,
                                             title="Monthly maximum peak demand",
                                             labels={"month": "Month", "peak_demand_mw": "Peak demand (MW)"}),
                                     width="stretch")
        st.subheader("Generated insights")
        for insight in manager.generate_insights(filtered):
            st.write(f"• {insight}")

with tab_report:
    st.subheader("Export summary report")
    search_term = search or ""
    filters_used = {
        "Cities": ", ".join(selected_cities) if selected_cities else "none selected",
        "Date range": f"{date_range[0]} to {date_range[1]}" if date_range else "not applied",
        "Search term": search_term or "none",
    }
    report_data = manager.filter_data(selected_cities, date_range, search_term)
    report = manager.build_report(report_data, filters_used, total_rows=len(all_data))
    st.text_area("Report preview", report, height=380)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_report, download_csv = st.columns(2)
    download_report.download_button("Download report (.txt)", report,
                                    file_name=f"energy_report_{timestamp}.txt", mime="text/plain")
    download_csv.download_button("Download filtered data (.csv)", report_data.to_csv(index=False),
                                 file_name=f"energy_filtered_{timestamp}.csv", mime="text/csv")
