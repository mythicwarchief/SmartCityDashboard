"""Energy CSV management and analysis for Kiran S Nair's dashboard module.

The starter CSV is an illustrative, deterministic model rather than metered
utility data. Replace it with a cited source before presenting values as real.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from utils.common import CSVManager

COLUMNS = [
    "record_id", "date", "city", "consumption_mwh", "renewable_mwh",
    "non_renewable_mwh", "peak_demand_mw",
]
CITIES = ["Kochi", "Trivandrum", "Kozhikode", "Thrissur"]
NUMERIC_COLUMNS = ["consumption_mwh", "renewable_mwh", "non_renewable_mwh", "peak_demand_mw"]
VALUE_LABELS = {
    "consumption_mwh": "Consumption (MWh)",
    "renewable_mwh": "Renewable energy (MWh)",
    "non_renewable_mwh": "Non-renewable energy (MWh)",
    "peak_demand_mw": "Peak demand (MW)",
}


class EnergyManager(CSVManager):
    """CRUD, validation and analysis for the Energy dataset."""

    def __init__(self, filepath):
        super().__init__(filepath, COLUMNS, id_column="record_id")

    def _coerce(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert CSV values safely; invalid numeric/date values become missing."""
        df = df.copy()
        df["record_id"] = pd.to_numeric(df["record_id"], errors="coerce").round().astype("Int64")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for column in NUMERIC_COLUMNS:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df["city"] = df["city"].map(lambda value: None if pd.isna(value) else str(value).strip().title())
        return df

    def _prepare(self, record: dict[str, Any], is_new: bool = True) -> tuple[dict[str, Any], list[str]]:
        """Validate an Energy record, including its energy-balance relationship."""
        errors: list[str] = []
        clean: dict[str, Any] = {}

        try:
            raw_id = record.get("record_id")
            record_id = int(raw_id)
            if float(raw_id) != record_id or record_id < 1:
                raise ValueError
            clean["record_id"] = record_id
        except (TypeError, ValueError, OverflowError):
            errors.append("Record ID must be a positive whole number.")

        parsed_date = pd.to_datetime(record.get("date"), errors="coerce")
        if pd.isna(parsed_date):
            errors.append("Date is required and must be valid.")
        clean["date"] = parsed_date

        city_value = record.get("city")
        city = None if city_value is None or pd.isna(city_value) else str(city_value).strip().title()
        if city not in CITIES:
            errors.append(f"City must be one of: {', '.join(CITIES)}.")
        clean["city"] = city

        for column, label in VALUE_LABELS.items():
            try:
                value = float(record.get(column))
                if not np.isfinite(value) or value < 0:
                    raise ValueError
                clean[column] = round(value, 3)
            except (TypeError, ValueError, OverflowError):
                errors.append(f"{label} must be a non-negative number.")
                clean[column] = np.nan

        if all(np.isfinite(clean.get(column, np.nan)) for column in NUMERIC_COLUMNS):
            consumption = clean["consumption_mwh"]
            renewable = clean["renewable_mwh"]
            non_renewable = clean["non_renewable_mwh"]
            if renewable > consumption:
                errors.append("Renewable energy cannot exceed total consumption.")
            if non_renewable > consumption:
                errors.append("Non-renewable energy cannot exceed total consumption.")
            if not np.isclose(consumption, renewable + non_renewable, atol=0.01):
                errors.append("Renewable and non-renewable energy must add up to total consumption.")

        return {column: clean.get(column) for column in COLUMNS}, errors

    def filter_data(self, cities: list[str] | None = None, date_range=None,
                    query: str | None = None) -> pd.DataFrame:
        """Filter by city, inclusive date range and optional free-text search."""
        df = self.data
        if cities is not None:
            df = df[df["city"].isin(cities)]
        if date_range and len(date_range) == 2:
            start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
            df = df[df["date"].between(start, end, inclusive="both")]
        if query:
            text = df.astype(str)
            mask = pd.Series(False, index=df.index)
            for column in text.columns:
                mask |= text[column].str.contains(query, case=False, regex=False, na=False)
            df = df[mask]
        return df

    @staticmethod
    def flagged_rows(df: pd.DataFrame) -> pd.DataFrame:
        """Return rows with missing values so they can be reviewed, not imputed."""
        return df[df.isna().any(axis=1)]

    @staticmethod
    def nan_counts(df: pd.DataFrame) -> pd.Series:
        counts = df.isna().sum()
        return counts[counts > 0]

    @staticmethod
    def energy_summary(df: pd.DataFrame) -> dict[str, float]:
        """Summarize complete consumption/source rows; missing values are excluded."""
        values = df.dropna(subset=["consumption_mwh", "renewable_mwh", "non_renewable_mwh"])
        if values.empty:
            return {}
        consumption = float(values["consumption_mwh"].sum())
        renewable = float(values["renewable_mwh"].sum())
        non_renewable = float(values["non_renewable_mwh"].sum())
        return {
            "consumption_mwh": consumption,
            "renewable_mwh": renewable,
            "non_renewable_mwh": non_renewable,
            "renewable_percent": renewable / consumption * 100 if consumption else 0.0,
            "mean_peak_demand_mw": float(df["peak_demand_mw"].mean()),
            "max_peak_demand_mw": float(df["peak_demand_mw"].max()),
        }

    @staticmethod
    def consumption_by_city(df: pd.DataFrame) -> pd.DataFrame:
        """Total consumption and renewable share grouped by city."""
        valid = df.dropna(subset=["consumption_mwh", "renewable_mwh", "non_renewable_mwh"])
        if valid.empty:
            return pd.DataFrame(columns=["city", "consumption_mwh", "renewable_mwh",
                                         "non_renewable_mwh", "renewable_percent"])
        grouped = valid.groupby("city", as_index=False)[
            ["consumption_mwh", "renewable_mwh", "non_renewable_mwh"]
        ].sum()
        grouped["renewable_percent"] = np.where(
            grouped["consumption_mwh"] > 0,
            grouped["renewable_mwh"] / grouped["consumption_mwh"] * 100,
            0.0,
        )
        return grouped.sort_values("consumption_mwh", ascending=False).reset_index(drop=True)

    @staticmethod
    def monthly_energy(df: pd.DataFrame) -> pd.DataFrame:
        """Monthly totals by city for energy source and peak-demand charts."""
        valid = df.dropna(subset=["date", "consumption_mwh", "renewable_mwh",
                                  "non_renewable_mwh"]).copy()
        if valid.empty:
            return pd.DataFrame(columns=["month", "city", "consumption_mwh", "renewable_mwh",
                                         "non_renewable_mwh", "peak_demand_mw"])
        valid["month"] = valid["date"].dt.to_period("M").dt.to_timestamp()
        return valid.groupby(["month", "city"], as_index=False).agg(
            consumption_mwh=("consumption_mwh", "sum"),
            renewable_mwh=("renewable_mwh", "sum"),
            non_renewable_mwh=("non_renewable_mwh", "sum"),
            peak_demand_mw=("peak_demand_mw", "max"),
        )

    @staticmethod
    def peak_demand_record(df: pd.DataFrame) -> dict[str, Any] | None:
        valid = df.dropna(subset=["peak_demand_mw"])
        if valid.empty:
            return None
        row = valid.loc[valid["peak_demand_mw"].idxmax()]
        day = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "unknown"
        return {"value": float(row["peak_demand_mw"]), "city": row["city"], "date": day}

    def generate_insights(self, df: pd.DataFrame) -> list[str]:
        """Build short insights only from the currently filtered records."""
        grouped = self.consumption_by_city(df)
        if grouped.empty:
            return ["No complete Energy readings are available for the selected filters."]

        insights = [
            f"{grouped.iloc[0]['city']} had the highest total consumption "
            f"({grouped.iloc[0]['consumption_mwh']:,.1f} MWh) in the selected period."
        ]
        if len(grouped) > 1:
            lowest = grouped.iloc[-1]
            insights.append(f"{lowest['city']} had the lowest total consumption "
                            f"({lowest['consumption_mwh']:,.1f} MWh).")

        summary = self.energy_summary(df)
        insights.append(f"Renewable sources supplied {summary['renewable_percent']:.1f}% of recorded consumption.")
        peak = self.peak_demand_record(df)
        if peak:
            insights.append(f"Highest peak demand was {peak['value']:.2f} MW in {peak['city']} on {peak['date']}.")

        monthly = self.monthly_energy(df)
        if not monthly.empty:
            total_by_month = monthly.groupby("month")["consumption_mwh"].sum()
            insights.append(f"Consumption was highest in {total_by_month.idxmax():%B %Y} and lowest in "
                            f"{total_by_month.idxmin():%B %Y}.")
        return insights

    def build_report(self, df: pd.DataFrame, filters: dict[str, str], total_rows: int) -> str:
        """Return a plain-text summary with current filters and computed metrics."""
        lines = [
            "SMART CITY DASHBOARD - ENERGY REPORT",
            "=" * 38,
            "Data note      : Starter readings are illustrative modeled data, not utility measurements.",
            f"Generated at   : {datetime.now():%Y-%m-%d %H:%M:%S}",
            f"Total rows     : {total_rows}",
            f"Filtered rows  : {len(df)}",
            "Filters applied:",
        ]
        lines.extend(f"  - {name}: {value}" for name, value in filters.items())
        lines.append(f"Rows with missing values (flagged, excluded from affected metrics): {len(self.flagged_rows(df))}")

        summary = self.energy_summary(df)
        lines.append("")
        if summary:
            lines.extend([
                f"Total consumption : {summary['consumption_mwh']:,.2f} MWh",
                f"Renewable energy : {summary['renewable_mwh']:,.2f} MWh",
                f"Non-renewable    : {summary['non_renewable_mwh']:,.2f} MWh",
                f"Renewable share  : {summary['renewable_percent']:.2f}%",
                f"Mean peak demand : {summary['mean_peak_demand_mw']:.2f} MW",
                f"Maximum peak     : {summary['max_peak_demand_mw']:.2f} MW",
            ])
        else:
            lines.append("No complete Energy readings are available.")
        lines.extend(["", "Consumption by city:"])
        grouped = self.consumption_by_city(df)
        lines.extend(
            f"  {row.city}: {row.consumption_mwh:,.2f} MWh, {row.renewable_percent:.1f}% renewable"
            for row in grouped.itertuples()
        )
        if grouped.empty:
            lines.append("  (no data)")
        lines.extend(["", "Insights:"])
        lines.extend(f"  * {text}" for text in self.generate_insights(df))
        return "\n".join(lines)
