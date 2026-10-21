
"""Energy dashboard: polished UI, analytics, CRUD and report downloads."""

import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.energy import CITIES, EnergyManager
from utils.ui import apply_page_style, render_page_header

DATA_FILE = ROOT / "data" / "energy.csv"


# ------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------

st.set_page_config(
    page_title="Energy | Smart City Dashboard",
    page_icon="⚡",
    layout="wide",
)

apply_page_style()

render_page_header(
    "Energy Intelligence",
    "Understand energy consumption, renewable contribution and peak "
    "demand across Kochi, Trivandrum, Kozhikode and Thrissur.",
    "⚡",
    "#8B6BD6",
)


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def flash(level: str, message: str) -> None:
    """Keep action feedback visible across Streamlit reruns."""
    st.session_state["energy_flash"] = (level, message)


def show_flash() -> None:
    """Display and clear a saved action message."""
    message = st.session_state.pop("energy_flash", None)

    if message:
        getattr(st, message[0])(message[1])


def numeric_value(value, default: float) -> float:
    """Use a safe default for missing numeric values."""
    return default if pd.isna(value) else float(value)


show_flash()


# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

manager = EnergyManager(DATA_FILE)
loaded, load_message = manager.load()

if manager.load_status == "missing":
    st.error(load_message)
    st.info("The expected file is data/energy.csv.")

    if st.button(
        "Create an empty energy.csv",
        type="primary",
    ):
        ok, message = manager.create_empty_file()
        flash("success" if ok else "error", message)
        st.rerun()

    st.stop()

if not loaded:
    st.error(load_message)
    st.info("Fix or replace data/energy.csv, then reload this page.")
    st.stop()

if manager.load_status == "empty":
    st.warning(load_message)

all_data = manager.data.copy()

st.info(
    "**Data transparency:** Starter readings are illustrative modeled "
    "data, not live or metered utility readings. Missing values are flagged "
    "and are not automatically imputed."
)


# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------

st.sidebar.markdown("## ⚡ Energy Controls")
st.sidebar.caption("Select the cities and dates to analyze.")

selected_cities = st.sidebar.multiselect(
    "Cities",
    CITIES,
    default=CITIES,
)

if all_data["date"].notna().any():
    min_date = all_data["date"].min().date()
    max_date = all_data["date"].max().date()
else:
    min_date = max_date = date.today()

picked_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
)

date_range = (
    tuple(picked_range)
    if isinstance(picked_range, (tuple, list))
    and len(picked_range) == 2
    else None
)

if date_range is None:
    st.sidebar.info("Choose an end date to apply the date filter.")


# ------------------------------------------------------------
# FILTER DATA AND CALCULATE KPIs
# ------------------------------------------------------------

filtered = manager.filter_data(selected_cities, date_range)
summary = manager.energy_summary(filtered)

st.markdown("### Energy at a glance")

metric_1, metric_2, metric_3, metric_4 = st.columns(4)

metric_1.metric(
    "Records",
    f"{len(filtered):,} / {len(all_data):,}",
    help="Filtered records compared with the complete dataset.",
)

metric_2.metric(
    "Energy consumption",
    (
        f"{summary['consumption_mwh']:,.1f} MWh"
        if summary
        else "N/A"
    ),
)

metric_3.metric(
    "Renewable share",
    (
        f"{summary['renewable_percent']:.1f}%"
        if summary
        else "N/A"
    ),
    help="Renewable energy as a percentage of recorded consumption.",
)

metric_4.metric(
    "Maximum peak demand",
    (
        f"{summary['max_peak_demand_mw']:.2f} MW"
        if summary
        else "N/A"
    ),
)

st.caption(
    "Metrics reflect the selected cities and date range. "
    "They describe the supplied dataset, not live grid conditions."
)


# ------------------------------------------------------------
# TABS
# ------------------------------------------------------------

tab_view, tab_add, tab_edit, tab_delete, tab_charts, tab_report = st.tabs(
    [
        "📋 View Data",
        "➕ Add Record",
        "✏️ Edit Record",
        "🗑️ Delete Record",
        "📊 Charts & Insights",
        "📄 Reports",
    ]
)


# ============================================================
# 1. VIEW DATA
# ============================================================

with tab_view:
    st.subheader("Energy records")
    st.caption("Search, sort and inspect energy readings.")

    search = st.text_input(
        "Search any column",
        placeholder="e.g. Kochi, 2025-06",
        key="energy_search",
    )

    col_sort, col_order = st.columns([2, 1])

    sort_column = col_sort.selectbox(
        "Sort by",
        manager.columns,
        index=min(1, len(manager.columns) - 1),
        key="energy_sort_column",
    )

    ascending = (
        col_order.radio(
            "Order",
            ["Ascending", "Descending"],
            horizontal=True,
            key="energy_sort_order",
        )
        == "Ascending"
    )

    view_data = manager.filter_data(
        selected_cities,
        date_range,
        search,
    )

    if sort_column in view_data.columns:
        view_data = view_data.sort_values(
            sort_column,
            ascending=ascending,
            na_position="last",
        )

    st.caption(
        f"Showing {len(view_data):,} of {len(all_data):,} total records."
    )

    st.dataframe(
        view_data,
        hide_index=True,
        use_container_width=True,
    )

    st.download_button(
        "⬇️ Download displayed records",
        data=view_data.to_csv(index=False).encode("utf-8"),
        file_name="energy_records.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("Summary statistics")

    left, middle, right = st.columns(3)

    with left:
        st.markdown("**Consumption and renewable share by city**")

        city_summary = manager.consumption_by_city(view_data)

        st.dataframe(
            city_summary,
            hide_index=True,
            use_container_width=True,
        )

    with middle:
        st.markdown("**Selected-period energy summary**")

        stats = manager.energy_summary(view_data)

        if stats:
            st.write(
                f"**Consumption:** "
                f"{stats['consumption_mwh']:,.1f} MWh"
            )
            st.write(
                f"**Renewable:** "
                f"{stats['renewable_mwh']:,.1f} MWh "
                f"({stats['renewable_percent']:.1f}%)"
            )
            st.write(
                f"**Non-renewable:** "
                f"{stats['non_renewable_mwh']:,.1f} MWh"
            )
        else:
            st.info("No complete consumption data is available.")

    with right:
        st.markdown("**Peak demand**")

        peak = manager.peak_demand_record(view_data)

        if peak:
            st.write(
                f"**{peak['value']:.2f} MW**"
            )
            st.write(
                f"{peak['city']} · {peak['date']}"
            )
        else:
            st.info("No peak-demand data is available.")

        if stats:
            st.write(
                f"Mean peak demand: "
                f"{stats['mean_peak_demand_mw']:.2f} MW"
            )

    missing_rows = manager.flagged_rows(view_data)

    with st.expander(
        f"⚠️ Missing-data details ({len(missing_rows)} flagged rows)"
    ):
        if missing_rows.empty:
            st.success("No missing values in the current view.")
        else:
            st.write(
                "Missing cells per column:",
                manager.nan_counts(view_data).to_dict(),
            )

            st.dataframe(
                missing_rows,
                hide_index=True,
                use_container_width=True,
            )


# ============================================================
# 2. ADD RECORD
# ============================================================

with tab_add:
    st.subheader("Add an energy reading")
    st.caption(
        "Enter the consumption, energy sources and peak demand for a city."
    )

    with st.form("energy_add_form", clear_on_submit=True):
        col_1, col_2 = st.columns(2)

        new_id = col_1.number_input(
            "Record ID",
            min_value=1,
            value=int(manager.next_id()),
            step=1,
        )

        new_date = col_2.date_input(
            "Date",
            value=date.today(),
        )

        new_city = col_1.selectbox(
            "City",
            CITIES,
        )

        consumption = col_2.number_input(
            "Consumption (MWh)",
            min_value=0.0,
            value=100.0,
            step=1.0,
        )

        renewable = col_1.number_input(
            "Renewable energy (MWh)",
            min_value=0.0,
            value=40.0,
            step=1.0,
        )

        non_renewable = col_2.number_input(
            "Non-renewable energy (MWh)",
            min_value=0.0,
            value=60.0,
            step=1.0,
        )

        peak_demand = col_1.number_input(
            "Peak demand (MW)",
            min_value=0.0,
            value=5.0,
            step=0.1,
        )

        st.caption(
            "Renewable and non-renewable energy must sum to total consumption."
        )

        add_clicked = st.form_submit_button(
            "➕ Add energy record",
            type="primary",
            use_container_width=True,
        )

    if add_clicked:
        ok, message = manager.create(
            {
                "record_id": new_id,
                "date": new_date,
                "city": new_city,
                "consumption_mwh": consumption,
                "renewable_mwh": renewable,
                "non_renewable_mwh": non_renewable,
                "peak_demand_mw": peak_demand,
            }
        )

        if ok:
            flash("success", message)
            st.rerun()
        else:
            st.error(message)


# ============================================================
# 3. EDIT RECORD
# ============================================================

with tab_edit:
    st.subheader("Edit an energy reading")

    if all_data.empty:
        st.info("There are no records to edit yet.")

    else:
        valid_ids = all_data["record_id"].dropna()

        if valid_ids.empty:
            st.error("No valid record IDs are available to edit.")

        else:
            edit_id = st.number_input(
                "Record ID to edit",
                min_value=1,
                value=int(valid_ids.min()),
                step=1,
                key="energy_edit_id",
            )

            record = manager.get_record(edit_id)

            if record is None:
                st.info(
                    f"No record exists with ID {edit_id}."
                )

            else:
                st.caption(
                    "The record ID cannot be changed."
                )

                form_key = f"energy_edit_form_{edit_id}"

                with st.form(form_key):
                    st.markdown(
                        f"**Editing record {edit_id}**"
                    )

                    col_1, col_2 = st.columns(2)

                    stored_date = (
                        record["date"].date()
                        if pd.notna(record["date"])
                        else date.today()
                    )

                    edit_date = col_1.date_input(
                        "Date",
                        value=stored_date,
                        key=f"energy_edit_date_{edit_id}",
                    )

                    edit_city = col_2.selectbox(
                        "City",
                        CITIES,
                        index=(
                            CITIES.index(record["city"])
                            if record["city"] in CITIES
                            else 0
                        ),
                        key=f"energy_edit_city_{edit_id}",
                    )

                    edit_consumption = col_1.number_input(
                        "Consumption (MWh)",
                        min_value=0.0,
                        value=numeric_value(
                            record["consumption_mwh"],
                            100.0,
                        ),
                        step=1.0,
                        key=f"energy_edit_consumption_{edit_id}",
                    )

                    edit_renewable = col_2.number_input(
                        "Renewable energy (MWh)",
                        min_value=0.0,
                        value=numeric_value(
                            record["renewable_mwh"],
                            40.0,
                        ),
                        step=1.0,
                        key=f"energy_edit_renewable_{edit_id}",
                    )

                    edit_non_renewable = col_1.number_input(
                        "Non-renewable energy (MWh)",
                        min_value=0.0,
                        value=numeric_value(
                            record["non_renewable_mwh"],
                            60.0,
                        ),
                        step=1.0,
                        key=f"energy_edit_nonrenewable_{edit_id}",
                    )

                    edit_peak = col_2.number_input(
                        "Peak demand (MW)",
                        min_value=0.0,
                        value=numeric_value(
                            record["peak_demand_mw"],
                            5.0,
                        ),
                        step=0.1,
                        key=f"energy_edit_peak_{edit_id}",
                    )

                    save_clicked = st.form_submit_button(
                        "💾 Save changes",
                        type="primary",
                        use_container_width=True,
                    )

                if save_clicked:
                    ok, message = manager.update(
                        edit_id,
                        {
                            "date": edit_date,
                            "city": edit_city,
                            "consumption_mwh": edit_consumption,
                            "renewable_mwh": edit_renewable,
                            "non_renewable_mwh": edit_non_renewable,
                            "peak_demand_mw": edit_peak,
                        },
                    )

                    if ok:
                        flash("success", message)
                        st.rerun()
                    else:
                        st.error(message)


# ============================================================
# 4. DELETE RECORD
# ============================================================

with tab_delete:
    st.subheader("Delete an energy reading")

    if all_data.empty:
        st.info("There are no records to delete yet.")

    else:
        valid_ids = all_data["record_id"].dropna()

        if valid_ids.empty:
            st.error("No valid record IDs are available to delete.")

        else:
            delete_id = st.number_input(
                "Record ID to delete",
                min_value=1,
                value=int(valid_ids.min()),
                step=1,
                key="energy_delete_id",
            )

            record = manager.get_record(delete_id)

            if record is None:
                st.info(
                    f"No record exists with ID {delete_id}."
                )

            else:
                st.warning(
                    f"**Record {delete_id} selected for deletion.**"
                )

                st.dataframe(
                    pd.DataFrame([record]),
                    hide_index=True,
                    use_container_width=True,
                )

                pending_delete = st.session_state.get(
                    "energy_pending_delete"
                )

                if pending_delete != delete_id:
                    if st.button(
                        "Continue to delete",
                        type="secondary",
                    ):
                        st.session_state[
                            "energy_pending_delete"
                        ] = delete_id
                        st.rerun()

                else:
                    st.error(
                        f"Are you sure you want to permanently delete "
                        f"record {delete_id}?"
                    )

                    confirm, cancel, _ = st.columns([1, 1, 4])

                    if confirm.button(
                        "Yes, delete",
                        type="primary",
                    ):
                        ok, message = manager.delete(delete_id)

                        st.session_state.pop(
                            "energy_pending_delete",
                            None,
                        )

                        flash(
                            "success" if ok else "error",
                            message,
                        )
                        st.rerun()

                    if cancel.button("Cancel"):
                        st.session_state.pop(
                            "energy_pending_delete",
                            None,
                        )
                        st.rerun()


# ============================================================
# 5. CHARTS AND INSIGHTS
# ============================================================

with tab_charts:
    st.subheader("Energy analytics")
    st.caption(
        "Compare consumption, energy sources and peak-demand trends."
    )

    chart_data = filtered.dropna(
        subset=[
            "date",
            "consumption_mwh",
            "renewable_mwh",
            "non_renewable_mwh",
        ]
    )

    if chart_data.empty:
        st.info(
            "No complete energy data is available for the current filters."
        )

    else:
        monthly = manager.monthly_energy(filtered)

        if not monthly.empty:
            fig_consumption = px.line(
                monthly,
                x="month",
                y="consumption_mwh",
                color="city",
                markers=True,
                title="Monthly energy consumption by city",
                labels={
                    "month": "Month",
                    "consumption_mwh": "Consumption (MWh)",
                    "city": "City",
                },
                color_discrete_sequence=[
                    "#8B6BD6",
                    "#3987D7",
                    "#0F9D8A",
                    "#D99A27",
                ],
            )

            fig_consumption.update_layout(
                title_x=0.03,
                margin=dict(l=20, r=20, t=60, b=20),
            )

            st.plotly_chart(
                fig_consumption,
                use_container_width=True,
            )

            chart_1, chart_2 = st.columns(2)

            sources = monthly.groupby(
                "city",
                as_index=False,
            )[
                ["renewable_mwh", "non_renewable_mwh"]
            ].sum()

            melted = sources.melt(
                id_vars="city",
                var_name="source",
                value_name="energy_mwh",
            )

            melted["source"] = melted["source"].map(
                {
                    "renewable_mwh": "Renewable",
                    "non_renewable_mwh": "Non-renewable",
                }
            )

            fig_sources = px.bar(
                melted,
                x="city",
                y="energy_mwh",
                color="source",
                barmode="stack",
                title="Renewable vs. non-renewable energy",
                labels={
                    "city": "City",
                    "energy_mwh": "Energy (MWh)",
                    "source": "Source",
                },
                color_discrete_map={
                    "Renewable": "#0F9D8A",
                    "Non-renewable": "#8B6BD6",
                },
            )

            fig_sources.update_layout(
                title_x=0.03,
                margin=dict(l=20, r=20, t=60, b=20),
                legend_title_text="",
            )

            chart_1.plotly_chart(
                fig_sources,
                use_container_width=True,
            )

            if (
                "peak_demand_mw" in monthly.columns
                and monthly["peak_demand_mw"].notna().any()
            ):
                fig_peak = px.line(
                    monthly,
                    x="month",
                    y="peak_demand_mw",
                    color="city",
                    markers=True,
                    title="Monthly maximum peak demand",
                    labels={
                        "month": "Month",
                        "peak_demand_mw": "Peak demand (MW)",
                        "city": "City",
                    },
                )

                fig_peak.update_layout(
                    title_x=0.03,
                    margin=dict(l=20, r=20, t=60, b=20),
                )

                chart_2.plotly_chart(
                    fig_peak,
                    use_container_width=True,
                )

        st.divider()
        st.subheader("Generated insights")

        insights = manager.generate_insights(filtered)

        if insights:
            for insight in insights:
                st.markdown(f"- {insight}")
        else:
            st.info(
                "No additional insights are available for this selection."
            )


# ============================================================
# 6. REPORTS
# ============================================================

with tab_report:
    st.subheader("Energy report")
    st.caption(
        "Generate a summary and download the filtered data."
    )

    search_term = search or ""

    filters_used = {
        "Cities": (
            ", ".join(selected_cities)
            if selected_cities
            else "none selected"
        ),
        "Date range": (
            f"{date_range[0]} to {date_range[1]}"
            if date_range
            else "not applied"
        ),
        "Search term": search_term or "none",
    }

    report_data = manager.filter_data(
        selected_cities,
        date_range,
        search_term,
    )

    report = manager.build_report(
        report_data,
        filters_used,
        total_rows=len(all_data),
    )

    st.text_area(
        "Report preview",
        report,
        height=320,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    download_report, download_csv = st.columns(2)

    with download_report:
        st.download_button(
            "⬇️ Download text report",
            data=report,
            file_name=f"energy_report_{timestamp}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with download_csv:
        st.download_button(
            "⬇️ Download filtered CSV",
            data=report_data.to_csv(index=False).encode("utf-8"),
            file_name=f"energy_filtered_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "SMART CITY DASHBOARD · ENERGY MODULE · "
    "Illustrative modeled data for four Kerala cities"
)
