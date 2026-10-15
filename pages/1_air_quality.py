"""Page 1 - Air Quality (owner: Vaishnav Sunil Nair).

Reads/writes ONLY data/air_quality.csv through AirQualityManager.
Tabs: View Data | Add Record | Edit Record | Delete Record | Charts and Insights | Report
"""
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # project root (relative, no hardcoded paths)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.air_quality import CATEGORIES, CITIES, AirQualityManager

DATA_FILE = ROOT / "data" / "air_quality.csv"

st.set_page_config(page_title="Air Quality | Smart City Dashboard", page_icon="🌫️", layout="wide")


# ------------------------------------------------------------------ helpers
def flash(level: str, message: str) -> None:
    """Keep a message across st.rerun() so the user sees the result of an action."""
    st.session_state["aq_flash"] = (level, message)


def show_flash() -> None:
    item = st.session_state.pop("aq_flash", None)
    if item:
        getattr(st, item[0])(item[1])


def num(value, default: float) -> float:
    return default if pd.isna(value) else float(value)


# --------------------------------------------------------------- load fresh
st.title("Air Quality")
st.caption("Monitor AQI and pollutants (PM2.5, PM10, NO2, SO2, CO) for Kochi, Trivandrum, "
           "Kozhikode and Thrissur. Data file: data/air_quality.csv")
show_flash()

manager = AirQualityManager(DATA_FILE)
loaded, load_msg = manager.load()  # fresh read on every run

if manager.load_status == "missing":
    st.error(load_msg)
    if st.button("Create an empty air_quality.csv with the correct headers"):
        ok, msg = manager.create_empty_file()
        flash("success" if ok else "error", msg)
        st.rerun()
    st.stop()
if not loaded:
    st.error(load_msg)
    st.info("Fix or replace data/air_quality.csv and reload this page.")
    st.stop()
if manager.load_status == "empty":
    st.warning(load_msg)

all_data = manager.data

# ------------------------------------------------------------ sidebar filters
st.sidebar.header("Filters")
sel_cities = st.sidebar.multiselect("City", CITIES, default=CITIES)
if all_data["date"].notna().any():
    d_min, d_max = all_data["date"].min().date(), all_data["date"].max().date()
else:
    d_min = d_max = date.today()
picked = st.sidebar.date_input("Date range", (d_min, d_max))
date_range = tuple(picked) if isinstance(picked, (tuple, list)) and len(picked) == 2 else None
if date_range is None:
    st.sidebar.info("Pick an end date to apply the date filter.")

filtered = manager.filter_data(sel_cities, date_range)

st.info("**Missing data (NaN) handling:** rows with missing values are flagged and counted; "
        "statistics and charts exclude NaN values (nothing is imputed).")

# ------------------------------------------------------------ summary metrics
summary = manager.aqi_summary(filtered)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Records (filtered / total)", f"{len(filtered)} / {len(all_data)}")
c2.metric("Average AQI", f"{summary['mean']:.1f}" if summary else "n/a")
c3.metric("Maximum AQI", f"{summary['max']:.0f}" if summary else "n/a")
c4.metric("Rows with missing values", len(manager.flagged_rows(filtered)))

tab_view, tab_add, tab_edit, tab_del, tab_charts, tab_report = st.tabs(
    ["View Data", "Add Record", "Edit Record", "Delete Record", "Charts and Insights", "Report"])

# ------------------------------------------------------------------ VIEW (Read)
with tab_view:
    s1, s2, s3 = st.columns([2, 1, 1])
    search = s1.text_input("Search (any column)", placeholder="e.g. Kochi, 2024-07, Moderate")
    sort_col = s2.selectbox("Sort by", manager.columns, index=1)
    ascending = s3.radio("Order", ["Ascending", "Descending"], horizontal=True) == "Ascending"

    view_df = manager.filter_data(sel_cities, date_range, search)
    if sort_col in view_df.columns:
        view_df = view_df.sort_values(sort_col, ascending=ascending, na_position="last")
    st.write(f"Showing **{len(view_df)}** of {len(all_data)} records")
    st.dataframe(view_df, hide_index=True)

    st.subheader("Summary statistics")
    left, mid, right = st.columns(3)
    with left:
        st.markdown("**Mean AQI by city** (group-by)")
        st.dataframe(manager.avg_aqi_by_city(view_df).rename("Mean AQI"))
    with mid:
        st.markdown("**Maximum PM2.5**")
        peak = manager.max_pm25(view_df)
        if peak:
            st.write(f"{peak['value']} ug/m3 in {peak['city']} on {peak['date']}")
        else:
            st.write("No PM2.5 data.")
        st.markdown("**AQI summary (NumPy)**")
        stats = manager.aqi_summary(view_df)
        st.write(", ".join(f"{k}: {v:.1f}" for k, v in stats.items()) if stats else "No AQI data.")
    with right:
        st.markdown("**Readings per AQI category**")
        st.dataframe(manager.category_counts(view_df).rename("Readings"))

    flagged = manager.flagged_rows(view_df)
    with st.expander(f"Rows flagged for missing values ({len(flagged)})"):
        if flagged.empty:
            st.write("No missing values in the current view.")
        else:
            st.write("Missing cells per column:", manager.nan_counts(view_df).to_dict())
            st.dataframe(flagged, hide_index=True)

# ------------------------------------------------------------------ ADD (Create)
with tab_add:
    st.subheader("Add a new reading")
    with st.form("add_form"):
        a1, a2 = st.columns(2)
        new_id = a1.number_input("Record ID", min_value=1, value=manager.next_id(), step=1)
        new_date = a2.date_input("Date", value=date.today())
        new_city = a1.selectbox("City", CITIES)
        new_aqi = a2.number_input("AQI (0-500)", min_value=0, max_value=500, value=50, step=1)
        new_pm25 = a1.number_input("PM2.5 (ug/m3)", min_value=0.0, max_value=1000.0, value=25.0, step=0.1)
        new_pm10 = a2.number_input("PM10 (ug/m3)", min_value=0.0, max_value=1500.0, value=45.0, step=0.1)
        new_no2 = a1.number_input("NO2 (ug/m3)", min_value=0.0, max_value=1000.0, value=20.0, step=0.1)
        new_so2 = a2.number_input("SO2 (ug/m3)", min_value=0.0, max_value=1000.0, value=8.0, step=0.1)
        new_co = a1.number_input("CO (mg/m3)", min_value=0.0, max_value=50.0, value=0.8, step=0.01)
        st.caption("The AQI category is calculated automatically from the AQI value.")
        add_clicked = st.form_submit_button("Add record")
    if add_clicked:
        ok, msg = manager.create({
            "record_id": new_id, "date": new_date, "city": new_city, "aqi": new_aqi,
            "pm25": new_pm25, "pm10": new_pm10, "no2": new_no2, "so2": new_so2, "co": new_co})
        if ok:
            flash("success", msg)
            st.rerun()
        else:
            st.error(msg)

# ---------------------------------------------------------------- EDIT (Update)
with tab_edit:
    st.subheader("Edit an existing reading")
    if all_data.empty:
        st.info("There are no records to edit yet.")
    else:
        edit_id = st.number_input("Record ID to edit", min_value=1, value=int(all_data["record_id"].dropna().min()),
                                  step=1, key="edit_id")
        record = manager.get_record(edit_id)
        if record is None:
            st.error(f"Record not found: there is no record with ID {edit_id}.")
        else:
            k = f"edit_{edit_id}"
            with st.form(f"edit_form_{edit_id}"):
                st.write(f"Editing record **{edit_id}** (the ID cannot be changed)")
                e1, e2 = st.columns(2)
                rec_date = record["date"].date() if pd.notna(record["date"]) else date.today()
                e_date = e2.date_input("Date", value=rec_date, key=f"{k}_date")
                e_city = e1.selectbox("City", CITIES, key=f"{k}_city",
                                      index=CITIES.index(record["city"]) if record["city"] in CITIES else 0)
                e_aqi = e2.number_input("AQI (0-500)", min_value=0, max_value=500,
                                        value=int(num(record["aqi"], 50)), step=1, key=f"{k}_aqi")
                e_pm25 = e1.number_input("PM2.5 (ug/m3)", min_value=0.0, max_value=1000.0,
                                         value=num(record["pm25"], 25.0), step=0.1, key=f"{k}_pm25")
                e_pm10 = e2.number_input("PM10 (ug/m3)", min_value=0.0, max_value=1500.0,
                                         value=num(record["pm10"], 45.0), step=0.1, key=f"{k}_pm10")
                e_no2 = e1.number_input("NO2 (ug/m3)", min_value=0.0, max_value=1000.0,
                                        value=num(record["no2"], 20.0), step=0.1, key=f"{k}_no2")
                e_so2 = e2.number_input("SO2 (ug/m3)", min_value=0.0, max_value=1000.0,
                                        value=num(record["so2"], 8.0), step=0.1, key=f"{k}_so2")
                e_co = e1.number_input("CO (mg/m3)", min_value=0.0, max_value=50.0,
                                       value=num(record["co"], 0.8), step=0.01, key=f"{k}_co")
                save_clicked = st.form_submit_button("Save changes")
            if save_clicked:
                ok, msg = manager.update(edit_id, {
                    "date": e_date, "city": e_city, "aqi": e_aqi, "pm25": e_pm25,
                    "pm10": e_pm10, "no2": e_no2, "so2": e_so2, "co": e_co})
                if ok:
                    flash("success", msg)
                    st.rerun()
                else:
                    st.error(msg)

# -------------------------------------------------------------- DELETE (Delete)
with tab_del:
    st.subheader("Delete a reading")
    if all_data.empty:
        st.info("There are no records to delete yet.")
    else:
        del_id = st.number_input("Record ID to delete", min_value=1,
                                 value=int(all_data["record_id"].dropna().min()), step=1, key="del_id")
        record = manager.get_record(del_id)
        if record is None:
            st.error(f"Record not found: there is no record with ID {del_id}.")
        else:
            st.dataframe(pd.DataFrame([record]), hide_index=True)
            if st.session_state.get("aq_pending_delete") != del_id:
                if st.button("Delete this record"):
                    st.session_state["aq_pending_delete"] = del_id
                    st.rerun()
            else:
                st.warning(f"Are you sure you want to permanently delete record {del_id}? This cannot be undone.")
                b1, b2, _ = st.columns([1, 1, 4])
                if b1.button("Yes, delete", type="primary"):
                    ok, msg = manager.delete(del_id)
                    st.session_state.pop("aq_pending_delete", None)
                    flash("success" if ok else "error", msg)
                    st.rerun()
                if b2.button("Cancel"):
                    st.session_state.pop("aq_pending_delete", None)
                    st.rerun()

# ------------------------------------------------------- CHARTS AND INSIGHTS
with tab_charts:
    st.subheader("Charts and insights")
    st.caption("Charts are rebuilt from the current CSV and the sidebar filters. NaN values are excluded.")
    chart_df = filtered.dropna(subset=["aqi"])
    if chart_df.empty:
        st.info("No AQI data for the current filters.")
    else:
        monthly = manager.monthly_aqi(chart_df)
        st.plotly_chart(px.line(monthly, x="month", y="aqi", color="city", markers=True,
                                title="Monthly average AQI by city",
                                labels={"month": "Month", "aqi": "Average AQI", "city": "City"}))
        ch1, ch2 = st.columns(2)
        by_city = manager.avg_aqi_by_city(chart_df).reset_index()
        by_city.columns = ["city", "avg_aqi"]
        ch1.plotly_chart(px.bar(by_city, x="city", y="avg_aqi", color="city", text="avg_aqi",
                                title="Average AQI by city",
                                labels={"city": "City", "avg_aqi": "Average AQI"}))
        cats = manager.category_counts(chart_df).reset_index()
        cats.columns = ["category", "readings"]
        cats = cats[cats["readings"] > 0]
        ch2.plotly_chart(px.pie(cats, names="category", values="readings", title="AQI category share",
                                category_orders={"category": CATEGORIES}))
        pm = chart_df.dropna(subset=["pm25"])
        if not pm.empty:
            st.plotly_chart(px.histogram(pm, x="pm25", color="city", nbins=40, barmode="overlay",
                                         opacity=0.7, title="PM2.5 distribution",
                                         labels={"pm25": "PM2.5 (ug/m3)"}))
    st.subheader("Generated insights")
    for text in manager.generate_insights(filtered):
        st.write(f"• {text}")

# ------------------------------------------------------------------- REPORT
with tab_report:
    st.subheader("Export summary report")
    filters_used = {
        "Cities": ", ".join(sel_cities) if sel_cities else "none selected",
        "Date range": f"{date_range[0]} to {date_range[1]}" if date_range else "not applied",
        "Search term": search if search else "none",
    }
    report_df = manager.filter_data(sel_cities, date_range, search)
    report_text = manager.build_report(report_df, filters_used, total_rows=len(all_data))
    st.text_area("Report preview", report_text, height=380)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    d1, d2 = st.columns(2)
    d1.download_button("Download report (.txt)", report_text, file_name=f"air_quality_report_{stamp}.txt",
                       mime="text/plain")
    d2.download_button("Download filtered data (.csv)", report_df.to_csv(index=False),
                       file_name=f"air_quality_filtered_{stamp}.csv", mime="text/csv")