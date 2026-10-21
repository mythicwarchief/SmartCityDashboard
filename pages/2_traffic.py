
"""Traffic dashboard: polished UI, CRUD, filters, charts and reports."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "traffic.csv"

import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.traffic import (
    TrafficManager,
    CITIES,
    CONGESTION_LEVELS,
    DAY_TYPES,
)
from utils.ui import apply_page_style, render_page_header


st.set_page_config(
    page_title="Traffic | Smart City Dashboard",
    page_icon="🚦",
    layout="wide",
)

apply_page_style()
render_page_header(
    "Urban Traffic Intelligence",
    "Explore traffic patterns, congestion levels, vehicle movement "
    "and district-level registration context across Kerala.",
    "🚦",
    "#D99A27",
)


@st.cache_resource
def get_manager():
    return TrafficManager(DATA_FILE)


manager = get_manager()

# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

st.info(
    "**Data transparency:** Hourly vehicle counts and speeds are simulated "
    "examples, not live traffic measurements. District vehicle-registration "
    "figures provide official historical context and are not road-level "
    "traffic counts."
)

try:
    manager.load()
except Exception as exc:
    st.error(f"Could not load traffic data: {exc}")
    st.stop()

if not DATA_FILE.exists():
    st.warning("The traffic CSV is missing.")

    if st.button("Create empty traffic CSV", type="primary"):
        ok, msg = manager.create_empty_file()
        st.success(msg) if ok else st.error(msg)
        st.rerun()

df_all = manager.data.copy()

if df_all.empty:
    st.warning("The traffic dataset is empty. Add a record to get started.")

    if manager.load_status not in ("ok", "empty"):
        st.caption(manager.load_message)

# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------

st.sidebar.markdown("## 🚦 Traffic Controls")
st.sidebar.caption("Filter the dashboard using the options below.")

selected_cities = st.sidebar.multiselect(
    "Cities",
    CITIES,
    default=CITIES,
)

selected_congestion = st.sidebar.multiselect(
    "Congestion levels",
    CONGESTION_LEVELS,
    default=CONGESTION_LEVELS,
)

selected_days = st.sidebar.multiselect(
    "Day type",
    DAY_TYPES,
    default=DAY_TYPES,
)

search_text = st.sidebar.text_input(
    "Search records",
    placeholder="Search road, city or value...",
)

if not df_all.empty and df_all["date"].notna().any():
    min_date = df_all["date"].dropna().min().date()
    max_date = df_all["date"].dropna().max().date()

    date_range = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
else:
    date_range = None

# ------------------------------------------------------------
# APPLY FILTERS
# ------------------------------------------------------------

filtered = df_all.copy()

if selected_cities:
    filtered = filtered[filtered["city"].isin(selected_cities)]
else:
    filtered = filtered.iloc[0:0]

if selected_congestion:
    filtered = filtered[
        filtered["congestion_level"].isin(selected_congestion)
    ]
else:
    filtered = filtered.iloc[0:0]

if selected_days:
    filtered = filtered[filtered["day_type"].isin(selected_days)]
else:
    filtered = filtered.iloc[0:0]

if date_range and len(date_range) == 2:
    start = pd.Timestamp(date_range[0])
    end = pd.Timestamp(date_range[1])

    filtered = filtered[
        filtered["date"].between(start, end, inclusive="both")
    ]

if search_text:
    mask = pd.Series(False, index=filtered.index)

    for col in filtered.astype(str).columns:
        mask |= filtered[col].str.contains(
            search_text,
            case=False,
            regex=False,
            na=False,
        )

    filtered = filtered[mask]

# ------------------------------------------------------------
# KPI SUMMARY
# ------------------------------------------------------------

st.markdown("### Traffic at a glance")

summary = manager.traffic_summary(filtered)

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Filtered records",
    f"{len(filtered):,}",
    help="Number of records matching the selected filters.",
)

k2.metric(
    "Vehicles recorded",
    f"{summary.get('total_vehicles', 0):,.0f}",
    help="Total simulated vehicle count in the filtered data.",
)

k3.metric(
    "Average speed",
    f"{summary.get('average_speed', 0):.1f} km/h",
    help="Average speed across the filtered records.",
)

k4.metric(
    "High/severe congestion",
    f"{summary.get('high_congestion_percent', 0):.1f}%",
    help="Percentage of filtered records classified as high or severe congestion.",
)

st.caption(
    f"Showing {len(filtered):,} of {len(df_all):,} total records."
)

# ------------------------------------------------------------
# MAIN NAVIGATION
# ------------------------------------------------------------

tab_view, tab_add, tab_edit, tab_delete, tab_charts, tab_report = st.tabs(
    [
        "📋  View Data",
        "➕  Add Record",
        "✏️  Edit Record",
        "🗑️  Delete Record",
        "📊  Charts & Insights",
        "📄  Reports",
    ]
)

# ============================================================
# 1. VIEW DATA
# ============================================================

with tab_view:
    st.subheader("Traffic records")
    st.caption("Inspect, search and sort records matching your filters.")

    if filtered.empty:
        st.info("No records match your current filters.")
    else:
        s1, s2 = st.columns([2, 1])

        sort_col = s1.selectbox(
            "Sort records by",
            list(filtered.columns),
            key="view_sort",
        )

        ascending = (
            s2.radio(
                "Sort order",
                ["Ascending", "Descending"],
                horizontal=True,
                key="view_order",
            )
            == "Ascending"
        )

        sorted_df = filtered.sort_values(
            sort_col,
            ascending=ascending,
            na_position="last",
        )

        st.dataframe(
            sorted_df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "⬇️ Download displayed records",
            data=sorted_df.to_csv(index=False).encode("utf-8"),
            file_name="traffic_records.csv",
            mime="text/csv",
        )

    missing = manager.nan_counts(filtered)

    if not missing.empty:
        with st.expander("⚠️ Missing-data details"):
            st.warning(
                "Some fields contain missing values. These values are flagged "
                "and are not automatically imputed."
            )
            st.dataframe(
                missing.rename("Missing values"),
                use_container_width=True,
            )

# ============================================================
# 2. ADD RECORD
# ============================================================

with tab_add:
    st.subheader("Add a traffic record")
    st.caption("Enter the details below to add a new observation.")

    with st.form("add_traffic_form", clear_on_submit=True):
        new_id = (
            int(manager.data["record_id"].max()) + 1
            if not manager.data.empty
            else 1
        )

        c1, c2 = st.columns(2)

        record_id = c1.number_input(
            "Record ID",
            min_value=1,
            value=new_id,
            step=1,
        )

        date = c2.date_input("Date")

        hour = c1.number_input(
            "Hour (0–23)",
            min_value=0,
            max_value=23,
            value=8,
            step=1,
        )

        city = c2.selectbox("City", CITIES)

        road = st.text_input(
            "Road",
            placeholder="e.g. MG Road",
        )

        vehicle_count = c1.number_input(
            "Vehicle count",
            min_value=0,
            value=200,
            step=1,
        )

        speed = c2.number_input(
            "Average speed (km/h)",
            min_value=0.0,
            max_value=200.0,
            value=35.0,
        )

        congestion = c1.selectbox(
            "Congestion level",
            CONGESTION_LEVELS,
            index=min(1, len(CONGESTION_LEVELS) - 1),
        )

        day_type = c2.selectbox("Day type", DAY_TYPES)

        submitted = st.form_submit_button(
            "➕ Add traffic record",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            record = {
                "record_id": record_id,
                "date": date,
                "hour": hour,
                "city": city,
                "road": road,
                "vehicle_count": vehicle_count,
                "avg_speed_kmph": speed,
                "congestion_level": congestion,
                "day_type": day_type,
                "registered_vehicles": 0,
            }

            ok, msg = manager.create(record)

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

# ============================================================
# 3. EDIT RECORD
# ============================================================

with tab_edit:
    st.subheader("Edit a traffic record")
    st.caption("Select an existing record ID, update its fields and save.")

    if manager.data.empty:
        st.info("There are no records to edit.")
    else:
        edit_id = st.number_input(
            "Record ID to edit",
            min_value=1,
            step=1,
            value=int(manager.data.iloc[0]["record_id"]),
            key="edit_id",
        )

        existing = manager.get_record(edit_id)

        if existing is None:
            st.info("Enter an existing record ID.")
        else:
            st.caption("The record ID cannot be changed.")

            with st.form("edit_traffic_form"):
                c1, c2 = st.columns(2)

                edit_date = c1.date_input(
                    "Date",
                    value=pd.Timestamp(existing["date"]).date(),
                    key="edit_date",
                )

                edit_hour = c2.number_input(
                    "Hour",
                    min_value=0,
                    max_value=23,
                    value=int(existing["hour"]),
                    key="edit_hour",
                )

                edit_city = c1.selectbox(
                    "City",
                    CITIES,
                    index=CITIES.index(existing["city"]),
                    key="edit_city",
                )

                edit_road = c2.text_input(
                    "Road",
                    value=str(existing["road"]),
                    key="edit_road",
                )

                edit_count = c1.number_input(
                    "Vehicle count",
                    min_value=0,
                    value=int(existing["vehicle_count"]),
                    key="edit_count",
                )

                edit_speed = c2.number_input(
                    "Average speed (km/h)",
                    min_value=0.0,
                    max_value=200.0,
                    value=float(existing["avg_speed_kmph"]),
                    key="edit_speed",
                )

                edit_congestion = c1.selectbox(
                    "Congestion",
                    CONGESTION_LEVELS,
                    index=CONGESTION_LEVELS.index(
                        existing["congestion_level"]
                    ),
                    key="edit_congestion",
                )

                edit_day = c2.selectbox(
                    "Day type",
                    DAY_TYPES,
                    index=DAY_TYPES.index(existing["day_type"]),
                    key="edit_day",
                )

                save_edit = st.form_submit_button(
                    "💾 Save changes",
                    type="primary",
                    use_container_width=True,
                )

                if save_edit:
                    changes = {
                        "date": edit_date,
                        "hour": edit_hour,
                        "city": edit_city,
                        "road": edit_road,
                        "vehicle_count": edit_count,
                        "avg_speed_kmph": edit_speed,
                        "congestion_level": edit_congestion,
                        "day_type": edit_day,
                    }

                    ok, msg = manager.update(edit_id, changes)

                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

# ============================================================
# 4. DELETE RECORD
# ============================================================

with tab_delete:
    st.subheader("Delete a traffic record")
    st.caption("Check the record details carefully before confirming deletion.")

    if manager.data.empty:
        st.info("There are no records to delete.")
    else:
        delete_id = st.number_input(
            "Record ID to delete",
            min_value=1,
            step=1,
            value=int(manager.data.iloc[0]["record_id"]),
            key="delete_id",
        )

        record = manager.get_record(delete_id)

        if record is None:
            st.info("Enter an existing record ID.")
        else:
            st.warning(
                f"**Record {delete_id}**\n\n"
                f"- City: {record['city']}\n"
                f"- Road: {record['road']}\n"
                f"- Time: {int(record['hour']):02d}:00\n"
                f"- Date: {pd.Timestamp(record['date']):%Y-%m-%d}"
            )

            confirm = st.checkbox(
                "I confirm that I want to delete this record.",
                key="confirm_delete_traffic",
            )

            if st.button(
                "🗑️ Delete record",
                type="primary",
                disabled=not confirm,
            ):
                ok, msg = manager.delete(delete_id)

                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

# ============================================================
# 5. CHARTS & INSIGHTS
# ============================================================

with tab_charts:
    st.subheader("Traffic analytics")
    st.caption(
        "Explore hourly trends, city-level vehicle counts and congestion distribution."
    )

    if filtered.empty:
        st.info("No records are available for visualization.")
    else:
        hourly = manager.hourly_traffic(filtered)

        if not hourly.empty:
            left, right = st.columns(2)

            with left:
                fig = px.line(
                    hourly,
                    x="hour",
                    y="vehicle_count",
                    title="Vehicle count by hour",
                    markers=True,
                    labels={
                        "hour": "Hour of day",
                        "vehicle_count": "Vehicle count",
                    },
                )
                fig.update_layout(
                    title_x=0.03,
                    margin=dict(l=20, r=20, t=60, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)

            with right:
                fig = px.line(
                    hourly,
                    x="hour",
                    y="avg_speed_kmph",
                    title="Average speed by hour",
                    markers=True,
                    labels={
                        "hour": "Hour of day",
                        "avg_speed_kmph": "Average speed (km/h)",
                    },
                )
                fig.update_layout(
                    title_x=0.03,
                    margin=dict(l=20, r=20, t=60, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)

        by_city = manager.traffic_by_city(filtered)

        if not by_city.empty:
            fig = px.bar(
                by_city,
                x="city",
                y="vehicle_count",
                color="city",
                title="Total simulated vehicle count by city",
                labels={
                    "city": "City",
                    "vehicle_count": "Vehicle count",
                },
            )
            fig.update_layout(
                title_x=0.03,
                showlegend=False,
                margin=dict(l=20, r=20, t=60, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        congestion = (
            filtered["congestion_level"]
            .value_counts()
            .rename_axis("congestion")
            .reset_index(name="records")
        )

        if not congestion.empty:
            fig = px.pie(
                congestion,
                names="congestion",
                values="records",
                title="Congestion level distribution",
                hole=0.45,
            )
            fig.update_layout(
                title_x=0.03,
                margin=dict(l=20, r=20, t=60, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        registration = manager.registration_by_city(filtered)

        if not registration.empty:
            st.markdown("#### Official vehicle-registration context")

            st.caption(
                "District-level registered vehicle totals, not road traffic counts. "
                "Values are from the official source cited in the project documentation."
            )

            fig = px.bar(
                registration,
                x="city",
                y="registered_vehicles",
                color="city",
                hover_data=["district", "registration_year"],
                title="Registered vehicles by district (2024–25)",
                labels={
                    "city": "City",
                    "registered_vehicles": "Registered vehicles",
                },
            )
            fig.update_layout(
                title_x=0.03,
                showlegend=False,
                margin=dict(l=20, r=20, t=60, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Generated insights")

        insights = manager.generate_insights(filtered)

        if insights:
            for insight in insights:
                st.markdown(f"- {insight}")
        else:
            st.info("No additional insights are available for this selection.")

# ============================================================
# 6. REPORTS
# ============================================================

with tab_report:
    st.subheader("Traffic report")
    st.caption(
        "Export a report and the filtered dataset using your current filter settings."
    )

    filter_description = {
        "Cities": ", ".join(selected_cities) or "None",
        "Congestion": ", ".join(selected_congestion) or "None",
        "Day type": ", ".join(selected_days) or "None",
        "Search": search_text or "None",
        "Date range": str(date_range) if date_range else "All dates",
    }

    report = manager.build_report(
        filtered,
        filter_description,
        len(df_all),
    )

    st.text_area(
        "Report preview",
        report,
        height=280,
    )

    d1, d2 = st.columns(2)

    with d1:
        st.download_button(
            "⬇️ Download text report",
            data=report,
            file_name="traffic_report.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with d2:
        st.download_button(
            "⬇️ Download filtered CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="traffic_filtered.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.divider()
st.caption(
    "SMART CITY DASHBOARD · TRAFFIC MODULE · "
    "Simulated hourly data + official district registration context"
)
