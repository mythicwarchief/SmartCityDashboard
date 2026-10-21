
"""Air Quality dashboard — Smart City Dashboard."""
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.air_quality import CATEGORIES, CITIES, AirQualityManager
from utils.ui import apply_page_style, render_page_header

DATA_FILE = ROOT / "data" / "air_quality.csv"

st.set_page_config(
    page_title="Air Quality | Smart City Dashboard",
    page_icon="🌫️",
    layout="wide",
)

apply_page_style()
render_page_header(
    "Air Quality Intelligence",
    "Monitor AQI and pollutant levels across Kochi, Trivandrum, Kozhikode and Thrissur.",
    "🌫️",
    "#0F9D8A",
)


# ------------------------------- Helpers -------------------------------
def flash(level: str, message: str) -> None:
    """Preserve an action message across a Streamlit rerun."""
    st.session_state["aq_flash"] = (level, message)


def show_flash() -> None:
    item = st.session_state.pop("aq_flash", None)
    if item:
        getattr(st, item[0])(item[1])


def num(value, default: float) -> float:
    return default if pd.isna(value) else float(value)


# ------------------------------- Load data -------------------------------
show_flash()

manager = AirQualityManager(DATA_FILE)
loaded, load_msg = manager.load()

if manager.load_status == "missing":
    st.error(load_msg)
    st.info("Place air_quality.csv inside the project's data folder.")
    if st.button("Create empty air_quality.csv"):
        ok, msg = manager.create_empty_file()
        flash("success" if ok else "error", msg)
        st.rerun()
    st.stop()

if not loaded:
    st.error(load_msg)
    st.info("Fix or replace data/air_quality.csv, then reload this page.")
    st.stop()

if manager.load_status == "empty":
    st.warning(load_msg)

all_data = manager.data

# ------------------------------- Sidebar filters -------------------------------
with st.sidebar:
    st.markdown("## 🌫️ Air Quality")
    st.caption("Pollutant monitoring and AQI analysis")
    st.divider()
    st.subheader("Filters")

    sel_cities = st.multiselect(
        "City",
        CITIES,
        default=CITIES,
        key="aq_filter_cities",
    )

    if all_data["date"].notna().any():
        d_min = all_data["date"].min().date()
        d_max = all_data["date"].max().date()
    else:
        d_min = d_max = date.today()

    picked = st.date_input(
        "Date range",
        value=(d_min, d_max),
        key="aq_filter_dates",
    )

    date_range = (
        tuple(picked)
        if isinstance(picked, (tuple, list)) and len(picked) == 2
        else None
    )

    if date_range is None:
        st.info("Select both a start date and an end date to apply the date filter.")

filtered = manager.filter_data(sel_cities, date_range)

st.info(
    "**Data quality:** missing values are flagged and counted. "
    "Statistics and charts exclude missing values where necessary; "
    "missing values are not imputed."
)

# ------------------------------- KPI cards -------------------------------
summary = manager.aqi_summary(filtered)
missing_rows = manager.flagged_rows(filtered)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Records", f"{len(filtered):,}", help="Records matching the current filters")
c2.metric("Average AQI", f"{summary['mean']:.1f}" if summary else "N/A")
c3.metric("Maximum AQI", f"{summary['max']:.0f}" if summary else "N/A")
c4.metric("Rows with missing values", f"{len(missing_rows):,}")

st.caption(
    f"Showing data for {len(sel_cities)} selected cities · "
    f"{len(filtered):,} of {len(all_data):,} total records"
)

# ------------------------------- Main tabs -------------------------------
tab_view, tab_add, tab_edit, tab_del, tab_charts, tab_report = st.tabs(
    [
        "📋 View Data",
        "➕ Add Record",
        "✏️ Edit Record",
        "🗑️ Delete Record",
        "📊 Charts & Insights",
        "📄 Report",
    ]
)

# =============================== VIEW DATA ===============================
with tab_view:
    st.subheader("Air quality records")
    st.caption("Search, sort and inspect the readings selected by your filters.")

    s1, s2, s3 = st.columns([2, 1, 1])
    search = s1.text_input(
        "Search any column",
        placeholder="e.g. Kochi, 2024-07, Moderate",
        key="aq_search",
    )
    sort_col = s2.selectbox(
        "Sort by",
        manager.columns,
        index=1,
        key="aq_sort_col",
    )
    ascending = (
        s3.radio(
            "Sort order",
            ["Ascending", "Descending"],
            horizontal=True,
            key="aq_sort_order",
        )
        == "Ascending"
    )

    view_df = manager.filter_data(sel_cities, date_range, search)
    if sort_col in view_df.columns:
        view_df = view_df.sort_values(
            sort_col,
            ascending=ascending,
            na_position="last",
        )

    st.write(f"Showing **{len(view_df):,}** of {len(all_data):,} records")

    if view_df.empty:
        st.info("No records match your current search and filters.")
    else:
        st.dataframe(
            view_df,
            hide_index=True,
            use_container_width=True,
        )

    st.divider()
    st.subheader("Summary statistics")

    left, middle, right = st.columns(3)

    with left:
        st.markdown("**Mean AQI by city**")
        avg_city = manager.avg_aqi_by_city(view_df)
        st.dataframe(
            avg_city.rename("Mean AQI"),
            use_container_width=True,
        )

    with middle:
        st.markdown("**Maximum PM2.5 reading**")
        peak = manager.max_pm25(view_df)
        if peak:
            st.metric("Maximum PM2.5", f"{peak['value']} µg/m³")
            st.caption(f"{peak['city']} · {peak['date']}")
        else:
            st.info("No PM2.5 data is available.")

        st.markdown("**AQI statistical summary**")
        stats = manager.aqi_summary(view_df)
        if stats:
            for key, value in stats.items():
                st.write(f"**{key.title()}:** {value:.1f}")
        else:
            st.caption("No AQI statistics are available.")

    with right:
        st.markdown("**Readings by AQI category**")
        categories = manager.category_counts(view_df)
        st.dataframe(
            categories.rename("Readings"),
            use_container_width=True,
        )

    flagged = manager.flagged_rows(view_df)
    with st.expander(f"Missing-data review · {len(flagged)} flagged rows"):
        if flagged.empty:
            st.success("No rows with missing values in this view.")
        else:
            st.warning("These records contain missing values. They have not been imputed.")
            st.write("Missing cells by column:", manager.nan_counts(view_df).to_dict())
            st.dataframe(flagged, use_container_width=True, hide_index=True)


# =============================== ADD RECORD ===============================
with tab_add:
    st.subheader("Add an air quality reading")
    st.caption("Enter a new record. The manager validates the values and calculates the AQI category.")

    with st.form("aq_add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        new_id = col1.number_input(
            "Record ID",
            min_value=1,
            value=int(manager.next_id()),
            step=1,
        )
        new_date = col2.date_input("Date", value=date.today())
        new_city = col1.selectbox("City", CITIES)
        new_aqi = col2.number_input(
            "AQI (0–500)",
            min_value=0,
            max_value=500,
            value=50,
            step=1,
        )
        new_pm25 = col1.number_input(
            "PM2.5 (µg/m³)",
            min_value=0.0,
            max_value=1000.0,
            value=25.0,
            step=0.1,
        )
        new_pm10 = col2.number_input(
            "PM10 (µg/m³)",
            min_value=0.0,
            max_value=1500.0,
            value=45.0,
            step=0.1,
        )
        new_no2 = col1.number_input(
            "NO2 (µg/m³)",
            min_value=0.0,
            max_value=1000.0,
            value=20.0,
            step=0.1,
        )
        new_so2 = col2.number_input(
            "SO2 (µg/m³)",
            min_value=0.0,
            max_value=1000.0,
            value=8.0,
            step=0.1,
        )
        new_co = col1.number_input(
            "CO (mg/m³)",
            min_value=0.0,
            max_value=50.0,
            value=0.8,
            step=0.01,
        )

        st.caption("The AQI category is calculated automatically from the AQI value.")
        add_clicked = st.form_submit_button("Add reading", type="primary", use_container_width=True)

    if add_clicked:
        ok, msg = manager.create(
            {
                "record_id": new_id,
                "date": new_date,
                "city": new_city,
                "aqi": new_aqi,
                "pm25": new_pm25,
                "pm10": new_pm10,
                "no2": new_no2,
                "so2": new_so2,
                "co": new_co,
            }
        )
        if ok:
            flash("success", msg)
            st.rerun()
        else:
            st.error(msg)


# =============================== EDIT RECORD ===============================
with tab_edit:
    st.subheader("Edit an existing reading")
    st.caption("Choose a record ID, update its measurements and save your changes.")

    valid_ids = all_data["record_id"].dropna() if not all_data.empty else pd.Series(dtype=float)

    if valid_ids.empty:
        st.info("There are no valid records to edit.")
    else:
        edit_id = st.number_input(
            "Record ID to edit",
            min_value=1,
            value=int(valid_ids.min()),
            step=1,
            key="aq_edit_id",
        )

        record = manager.get_record(edit_id)

        if record is None:
            st.warning(f"No record was found with ID {edit_id}.")
        else:
            with st.form(f"aq_edit_form_{edit_id}"):
                st.info(f"Editing record **{edit_id}**. The record ID cannot be changed.")

                e1, e2 = st.columns(2)
                rec_date = (
                    record["date"].date()
                    if pd.notna(record["date"])
                    else date.today()
                )

                e_date = e1.date_input(
                    "Date",
                    value=rec_date,
                    key=f"aq_edit_date_{edit_id}",
                )
                e_city = e2.selectbox(
                    "City",
                    CITIES,
                    index=CITIES.index(record["city"])
                    if record["city"] in CITIES else 0,
                    key=f"aq_edit_city_{edit_id}",
                )
                e_aqi = e1.number_input(
                    "AQI (0–500)",
                    min_value=0,
                    max_value=500,
                    value=int(num(record["aqi"], 50)),
                    step=1,
                    key=f"aq_edit_aqi_{edit_id}",
                )
                e_pm25 = e2.number_input(
                    "PM2.5 (µg/m³)",
                    min_value=0.0,
                    max_value=1000.0,
                    value=num(record["pm25"], 25.0),
                    step=0.1,
                    key=f"aq_edit_pm25_{edit_id}",
                )
                e_pm10 = e1.number_input(
                    "PM10 (µg/m³)",
                    min_value=0.0,
                    max_value=1500.0,
                    value=num(record["pm10"], 45.0),
                    step=0.1,
                    key=f"aq_edit_pm10_{edit_id}",
                )
                e_no2 = e2.number_input(
                    "NO2 (µg/m³)",
                    min_value=0.0,
                    max_value=1000.0,
                    value=num(record["no2"], 20.0),
                    step=0.1,
                    key=f"aq_edit_no2_{edit_id}",
                )
                e_so2 = e1.number_input(
                    "SO2 (µg/m³)",
                    min_value=0.0,
                    max_value=1000.0,
                    value=num(record["so2"], 8.0),
                    step=0.1,
                    key=f"aq_edit_so2_{edit_id}",
                )
                e_co = e2.number_input(
                    "CO (mg/m³)",
                    min_value=0.0,
                    max_value=50.0,
                    value=num(record["co"], 0.8),
                    step=0.01,
                    key=f"aq_edit_co_{edit_id}",
                )

                save_clicked = st.form_submit_button(
                    "Save changes",
                    type="primary",
                    use_container_width=True,
                )

            if save_clicked:
                ok, msg = manager.update(
                    edit_id,
                    {
                        "date": e_date,
                        "city": e_city,
                        "aqi": e_aqi,
                        "pm25": e_pm25,
                        "pm10": e_pm10,
                        "no2": e_no2,
                        "so2": e_so2,
                        "co": e_co,
                    },
                )
                if ok:
                    flash("success", msg)
                    st.rerun()
                else:
                    st.error(msg)


# =============================== DELETE RECORD ===============================
with tab_del:
    st.subheader("Delete a reading")
    st.caption("Review the selected record before confirming deletion.")

    valid_ids = all_data["record_id"].dropna() if not all_data.empty else pd.Series(dtype=float)

    if valid_ids.empty:
        st.info("There are no valid records to delete.")
    else:
        del_id = st.number_input(
            "Record ID to delete",
            min_value=1,
            value=int(valid_ids.min()),
            step=1,
            key="aq_delete_id",
        )
        record = manager.get_record(del_id)

        if record is None:
            st.warning(f"No record was found with ID {del_id}.")
        else:
            st.dataframe(
                pd.DataFrame([record]),
                hide_index=True,
                use_container_width=True,
            )

            if st.session_state.get("aq_pending_delete") != del_id:
                if st.button("Continue to delete", key="aq_start_delete"):
                    st.session_state["aq_pending_delete"] = del_id
                    st.rerun()
            else:
                st.warning(
                    f"Are you sure you want to permanently delete record {del_id}? "
                    "This action cannot be undone."
                )
                b1, b2, _ = st.columns([1, 1, 4])

                if b1.button("Yes, delete", type="primary", key="aq_confirm_delete"):
                    ok, msg = manager.delete(del_id)
                    st.session_state.pop("aq_pending_delete", None)
                    flash("success" if ok else "error", msg)
                    st.rerun()

                if b2.button("Cancel", key="aq_cancel_delete"):
                    st.session_state.pop("aq_pending_delete", None)
                    st.rerun()


# =============================== CHARTS & INSIGHTS ===============================
with tab_charts:
    st.subheader("Air quality analytics")
    st.caption("Visualizations update according to the selected cities and date range.")

    chart_df = filtered.dropna(subset=["aqi"])

    if chart_df.empty:
        st.info("No AQI data is available for the current filters.")
    else:
        monthly = manager.monthly_aqi(chart_df)

        if not monthly.empty:
            fig_monthly = px.line(
                monthly,
                x="month",
                y="aqi",
                color="city",
                markers=True,
                title="Monthly average AQI by city",
                labels={
                    "month": "Month",
                    "aqi": "Average AQI",
                    "city": "City",
                },
            )
            fig_monthly.update_layout(legend_title_text="")
            st.plotly_chart(fig_monthly, use_container_width=True)

        ch1, ch2 = st.columns(2)

        by_city = manager.avg_aqi_by_city(chart_df).reset_index()
        by_city.columns = ["city", "avg_aqi"]

        with ch1:
            fig_city = px.bar(
                by_city,
                x="city",
                y="avg_aqi",
                color="city",
                text="avg_aqi",
                title="Average AQI by city",
                labels={"city": "City", "avg_aqi": "Average AQI"},
            )
            fig_city.update_layout(showlegend=False)
            st.plotly_chart(fig_city, use_container_width=True)

        cats = manager.category_counts(chart_df).reset_index()
        cats.columns = ["category", "readings"]
        cats = cats[cats["readings"] > 0]

        with ch2:
            if not cats.empty:
                fig_categories = px.pie(
                    cats,
                    names="category",
                    values="readings",
                    title="AQI category distribution",
                    category_orders={"category": CATEGORIES},
                    hole=0.42,
                )
                fig_categories.update_layout(legend_title_text="")
                st.plotly_chart(fig_categories, use_container_width=True)
            else:
                st.info("No AQI categories are available.")

        pm = chart_df.dropna(subset=["pm25"])
        if not pm.empty:
            fig_pm = px.histogram(
                pm,
                x="pm25",
                color="city",
                nbins=40,
                barmode="overlay",
                opacity=0.7,
                title="PM2.5 distribution by city",
                labels={"pm25": "PM2.5 (µg/m³)", "city": "City"},
            )
            st.plotly_chart(fig_pm, use_container_width=True)

    st.divider()
    st.subheader("Generated insights")
    for insight in manager.generate_insights(filtered):
        st.markdown(f"- {insight}")


# =============================== REPORT ===============================
with tab_report:
    st.subheader("Export air quality report")
    st.caption("Download a summary of the current selection or export the filtered records.")

    filters_used = {
        "Cities": ", ".join(sel_cities) if sel_cities else "None selected",
        "Date range": (
            f"{date_range[0]} to {date_range[1]}"
            if date_range else "Not applied"
        ),
        "Search term": search if search else "None",
    }

    report_df = manager.filter_data(sel_cities, date_range, search)
    report_text = manager.build_report(
        report_df,
        filters_used,
        total_rows=len(all_data),
    )

    st.text_area("Report preview", report_text, height=300)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    d1, d2 = st.columns(2)

    d1.download_button(
        "Download report (.txt)",
        report_text,
        file_name=f"air_quality_report_{stamp}.txt",
        mime="text/plain",
        use_container_width=True,
    )

    d2.download_button(
        "Download filtered data (.csv)",
        report_df.to_csv(index=False),
        file_name=f"air_quality_filtered_{stamp}.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption("Smart City Dashboard · Air Quality module")
