"""AirQualityManager - Vaishnav Sunil Nair (owner of data/air_quality.csv)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from utils.common import CSVManager

COLUMNS = ["record_id", "date", "city", "aqi", "pm25", "pm10", "no2", "so2", "co", "aqi_category"]
CITIES = ["Kochi", "Trivandrum", "Kozhikode", "Thrissur"]
CATEGORIES = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]  # CPCB scale
NUMERIC_COLS = ["aqi", "pm25", "pm10", "no2", "so2", "co"]

# Sensible input ranges: column -> (min, max, label)
RANGES = {
    "aqi": (0, 500, "AQI"),
    "pm25": (0, 1000, "PM2.5"),
    "pm10": (0, 1500, "PM10"),
    "no2": (0, 1000, "NO2"),
    "so2": (0, 1000, "SO2"),
    "co": (0, 50, "CO"),
}


class AirQualityManager(CSVManager):
    """CRUD + analysis for air_quality.csv."""

    def __init__(self, filepath):
        super().__init__(filepath, COLUMNS, id_column="record_id")

    # ------------------------------------------------------------ categories
    @staticmethod
    def aqi_category(aqi) -> str | None:
        """CPCB AQI category for a value (None if the value is missing)."""
        if aqi is None or pd.isna(aqi):
            return None
        if aqi <= 50:
            return "Good"
        if aqi <= 100:
            return "Satisfactory"
        if aqi <= 200:
            return "Moderate"
        if aqi <= 300:
            return "Poor"
        if aqi <= 400:
            return "Very Poor"
        return "Severe"

    # ------------------------------------------------- hooks (override base)
    def _coerce(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fix column types. Bad values become NaN/NaT so they are flagged, not crashed on."""
        df = df.copy()
        df["record_id"] = pd.to_numeric(df["record_id"], errors="coerce").round().astype("Int64")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for col in NUMERIC_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["city"] = df["city"].map(lambda c: None if pd.isna(c) else str(c).strip().title())
        # aqi_category is DERIVED from aqi (never typed in by the user)
        df["aqi_category"] = df["aqi"].map(self.aqi_category)
        return df

    def _prepare(self, record: dict[str, Any], is_new: bool = True) -> tuple[dict[str, Any], list[str]]:
        """Validate one record. Returns (clean_record, list_of_error_messages)."""
        errors: list[str] = []
        clean: dict[str, Any] = {}

        try:
            rid = int(record.get("record_id"))
            if rid < 1:
                raise ValueError
            clean["record_id"] = rid
        except (TypeError, ValueError):
            errors.append("Record ID must be a positive whole number.")

        date = pd.to_datetime(record.get("date"), errors="coerce")
        if pd.isna(date):
            errors.append("Date is required and must be a valid date (YYYY-MM-DD).")
        clean["date"] = date

        city = record.get("city")
        city = None if city is None or pd.isna(city) else str(city).strip().title()
        if city not in CITIES:
            errors.append(f"City must be one of: {', '.join(CITIES)}.")
        clean["city"] = city

        for col, (lo, hi, label) in RANGES.items():
            raw = record.get(col)
            try:
                value = float(raw)
                if np.isnan(value):
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"{label} is required and must be a number.")
                clean[col] = np.nan
                continue
            if not lo <= value <= hi:
                errors.append(f"{label} must be between {lo} and {hi}.")
            clean[col] = round(value) if col == "aqi" else value

        clean["aqi_category"] = self.aqi_category(clean.get("aqi"))
        return {c: clean.get(c) for c in COLUMNS}, errors

    # --------------------------------------------------------------- filters
    def filter_data(self, cities: list[str] | None = None, date_range=None,
                    query: str | None = None) -> pd.DataFrame:
        """Filter by city, (start, end) date range and free-text search."""
        df = self.data
        if cities:
            df = df[df["city"].isin(cities)]
        if date_range and len(date_range) == 2:
            start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
            df = df[(df["date"] >= start) & (df["date"] <= end)]
        if query:
            text = df.astype(str)
            mask = pd.Series(False, index=df.index)
            for col in text.columns:
                mask |= text[col].str.contains(query, case=False, regex=False, na=False)
            df = df[mask]
        return df

    # -------------------------------------------------------- missing values
    @staticmethod
    def flagged_rows(df: pd.DataFrame) -> pd.DataFrame:
        """Rows with at least one missing value (NaN/NaT) - flagged, not deleted."""
        return df[df.isna().any(axis=1)]

    @staticmethod
    def nan_counts(df: pd.DataFrame) -> pd.Series:
        counts = df.isna().sum()
        return counts[counts > 0]

    # ------------------------------------------------------------ statistics
    @staticmethod
    def avg_aqi_by_city(df: pd.DataFrame) -> pd.Series:
        """Stat 1 (group-by): mean AQI per city, NaN excluded, highest first."""
        return df.dropna(subset=["aqi"]).groupby("city")["aqi"].mean().round(1).sort_values(ascending=False)

    @staticmethod
    def max_pm25(df: pd.DataFrame) -> dict[str, Any] | None:
        """Stat 2: highest PM2.5 reading with its city and date."""
        valid = df.dropna(subset=["pm25"])
        if valid.empty:
            return None
        row = valid.loc[valid["pm25"].idxmax()]
        return {"value": float(row["pm25"]), "city": row["city"],
                "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "unknown"}

    @staticmethod
    def category_counts(df: pd.DataFrame) -> pd.Series:
        """Stat 3: number of readings in each AQI category (CPCB order)."""
        return df["aqi_category"].value_counts().reindex(CATEGORIES, fill_value=0)

    @staticmethod
    def aqi_summary(df: pd.DataFrame) -> dict[str, float]:
        """Stat 4 (NumPy): mean, median, std, 95th percentile and max of AQI."""
        values = df["aqi"].dropna().to_numpy(dtype=float)
        if values.size == 0:
            return {}
        return {"mean": float(np.mean(values)), "median": float(np.median(values)),
                "std": float(np.std(values)), "p95": float(np.percentile(values, 95)),
                "max": float(np.max(values))}

    @staticmethod
    def monthly_aqi(df: pd.DataFrame) -> pd.DataFrame:
        """Mean AQI per month per city (for the trend line chart)."""
        valid = df.dropna(subset=["aqi", "date"]).copy()
        if valid.empty:
            return pd.DataFrame(columns=["month", "city", "aqi"])
        valid["month"] = valid["date"].dt.to_period("M").dt.to_timestamp()
        out = valid.groupby(["month", "city"], as_index=False)["aqi"].mean()
        out["aqi"] = out["aqi"].round(1)
        return out

    # --------------------------------------------------------------- insights
    def generate_insights(self, df: pd.DataFrame) -> list[str]:
        """Text insights computed from the data (never hand-written numbers)."""
        insights: list[str] = []
        by_city = self.avg_aqi_by_city(df)
        if by_city.empty:
            return ["No AQI readings in the selected period."]
        insights.append(f"{by_city.index[0]} recorded the highest average AQI "
                        f"({by_city.iloc[0]}) in the selected period.")
        if len(by_city) > 1:
            insights.append(f"{by_city.index[-1]} had the cleanest air on average "
                            f"(AQI {by_city.iloc[-1]}).")
        peak = self.max_pm25(df)
        if peak:
            insights.append(f"Highest PM2.5 reading: {peak['value']} ug/m3 in {peak['city']} on {peak['date']}.")
        monthly = self.monthly_aqi(df)
        if not monthly.empty:
            by_month = monthly.groupby("month")["aqi"].mean()
            insights.append(f"Pollution was worst in {by_month.idxmax():%B %Y} "
                            f"(avg AQI {by_month.max():.1f}) and lowest in "
                            f"{by_month.idxmin():%B %Y} (avg AQI {by_month.min():.1f}).")
        counts = self.category_counts(df)
        total = int(counts.sum())
        if total:
            top = counts.idxmax()
            insights.append(f"{counts[top] / total * 100:.0f}% of readings fall in the '{top}' category.")
            unhealthy = int(counts[["Poor", "Very Poor", "Severe"]].sum())
            insights.append(f"{unhealthy} reading(s) were Poor or worse (AQI above 200).")
        return insights

    # ----------------------------------------------------------------- report
    def build_report(self, df: pd.DataFrame, filters: dict[str, str], total_rows: int) -> str:
        """Plain-text summary report: timestamp, row counts, filters, key statistics."""
        lines = [
            "SMART CITY DASHBOARD - AIR QUALITY REPORT",
            "=" * 44,
            f"Generated at   : {datetime.now():%Y-%m-%d %H:%M:%S}",
            f"Total rows     : {total_rows}",
            f"Filtered rows  : {len(df)}",
            "Filters applied:",
        ]
        lines += [f"  - {name}: {value}" for name, value in filters.items()]
        lines.append(f"Missing-value rows (flagged, excluded from statistics): {len(self.flagged_rows(df))}")
        lines += ["", "Average AQI by city:"]
        by_city = self.avg_aqi_by_city(df)
        lines += [f"  {city}: {val}" for city, val in by_city.items()] or ["  (no data)"]
        peak = self.max_pm25(df)
        lines += ["", "Highest PM2.5: " + (f"{peak['value']} ug/m3, {peak['city']}, {peak['date']}" if peak else "n/a")]
        lines += ["", "Readings per AQI category:"]
        lines += [f"  {cat}: {n}" for cat, n in self.category_counts(df).items()]
        summary = self.aqi_summary(df)
        if summary:
            lines += ["", "AQI summary (NumPy): " + ", ".join(f"{k}={v:.1f}" for k, v in summary.items())]
        lines += ["", "Insights:"] + [f"  * {text}" for text in self.generate_insights(df)]
        return "\n".join(lines)