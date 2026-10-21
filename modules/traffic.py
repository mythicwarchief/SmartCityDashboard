
"""Traffic data management and analytics for Smart City Dashboard."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from utils.common import CSVManager

COLUMNS = [
    "record_id", "date", "hour", "city", "road",
    "vehicle_count", "avg_speed_kmph", "congestion_level", "day_type",
    "data_type", "source", "source_url", "district",
    "registration_year", "registered_vehicles",
]

CITIES = ["Kochi", "Trivandrum", "Kozhikode", "Thrissur"]
CONGESTION_LEVELS = ["Low", "Moderate", "High", "Severe"]
DAY_TYPES = ["Weekday", "Weekend"]


class TrafficManager(CSVManager):
    """CRUD, validation, filtering and analytics for traffic records."""

    def __init__(self, filepath):
        super().__init__(filepath, COLUMNS, id_column="record_id")

    def _coerce(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df["record_id"] = pd.to_numeric(
            df["record_id"], errors="coerce"
        ).round().astype("Int64")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["hour"] = pd.to_numeric(
            df["hour"], errors="coerce"
        ).astype("Int64")

        for col in ["vehicle_count", "avg_speed_kmph"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["registered_vehicles"] = pd.to_numeric(
            df["registered_vehicles"], errors="coerce"
        ).astype("Int64")

        text_columns = [
            "city", "road", "congestion_level", "day_type", "data_type",
            "source", "source_url", "district", "registration_year",
        ]
        for col in text_columns:
            df[col] = df[col].map(
                lambda x: None if pd.isna(x) else str(x).strip()
            )

        for col in ["city", "congestion_level", "day_type"]:
            df[col] = df[col].map(
                lambda x: x.title() if x else x
            )

        return df

    def _prepare(
        self, record: dict[str, Any], is_new: bool = True
    ) -> tuple[dict[str, Any], list[str]]:
        errors = []
        clean = {}

        # ID
        try:
            raw_id = record.get("record_id")
            rid = int(raw_id)
            if float(raw_id) != rid or rid < 1:
                raise ValueError
            clean["record_id"] = rid
        except (TypeError, ValueError, OverflowError):
            errors.append("Record ID must be a positive whole number.")
            clean["record_id"] = None

        # Date
        date = pd.to_datetime(record.get("date"), errors="coerce")
        if pd.isna(date):
            errors.append("Date must be valid.")
        clean["date"] = date

        # Hour
        try:
            raw_hour = record.get("hour")
            hour = int(raw_hour)
            if float(raw_hour) != hour or not 0 <= hour <= 23:
                raise ValueError
            clean["hour"] = hour
        except (TypeError, ValueError, OverflowError):
            errors.append("Hour must be a whole number from 0 to 23.")
            clean["hour"] = None

        # City
        city = str(record.get("city", "")).strip().title()
        if city not in CITIES:
            errors.append(f"City must be one of: {', '.join(CITIES)}.")
        clean["city"] = city

        # Road
        road = str(record.get("road", "")).strip()
        if not road:
            errors.append("Road name is required.")
        clean["road"] = road

        # Vehicle count
        try:
            raw_count = record.get("vehicle_count")
            count = int(raw_count)
            if float(raw_count) != count or count < 0:
                raise ValueError
            clean["vehicle_count"] = count
        except (TypeError, ValueError, OverflowError):
            errors.append("Vehicle count must be a non-negative whole number.")
            clean["vehicle_count"] = np.nan

        # Speed
        try:
            speed = float(record.get("avg_speed_kmph"))
            if not np.isfinite(speed) or not 0 <= speed <= 200:
                raise ValueError
            clean["avg_speed_kmph"] = round(speed, 2)
        except (TypeError, ValueError, OverflowError):
            errors.append("Speed must be between 0 and 200 km/h.")
            clean["avg_speed_kmph"] = np.nan

        # Congestion
        congestion = str(record.get("congestion_level", "")).strip().title()
        if congestion not in CONGESTION_LEVELS:
            errors.append(
                f"Congestion must be one of: {', '.join(CONGESTION_LEVELS)}."
            )
        clean["congestion_level"] = congestion

        # Day type
        day_type = str(record.get("day_type", "")).strip().title()
        if day_type not in DAY_TYPES:
            errors.append("Day type must be Weekday or Weekend.")
        clean["day_type"] = day_type

        # Data provenance
        district_map = {
            "Kochi": "Ernakulam",
            "Trivandrum": "Thiruvananthapuram",
            "Kozhikode": "Kozhikode",
            "Thrissur": "Thrissur",
        }
        clean["data_type"] = "SIMULATED_HOURLY"
        clean["source"] = "User-entered example; not measured traffic"
        clean["source_url"] = ""
        clean["district"] = district_map.get(city, "")
        clean["registration_year"] = "2024-25"

        try:
            registered = int(record.get("registered_vehicles", 0) or 0)
            if registered < 0:
                raise ValueError
            clean["registered_vehicles"] = registered
        except (TypeError, ValueError, OverflowError):
            clean["registered_vehicles"] = 0

        return {col: clean.get(col) for col in COLUMNS}, errors

    def filter_data(
        self, cities=None, date_range=None, hours=None,
        congestion_levels=None, query=None, data_types=None
    ):
        df = self.data

        if cities:
            df = df[df["city"].isin(cities)]
        if date_range and len(date_range) == 2:
            start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
            df = df[df["date"].between(start, end, inclusive="both")]
        if hours:
            df = df[df["hour"].isin(hours)]
        if congestion_levels:
            df = df[df["congestion_level"].isin(congestion_levels)]
        if data_types:
            df = df[df["data_type"].isin(data_types)]
        if query:
            mask = pd.Series(False, index=df.index)
            for col in df.columns:
                mask |= df[col].astype(str).str.contains(
                    query, case=False, regex=False, na=False
                )
            df = df[mask]

        return df

    @staticmethod
    def flagged_rows(df: pd.DataFrame) -> pd.DataFrame:
        return df[df.isna().any(axis=1)]

    @staticmethod
    def nan_counts(df: pd.DataFrame) -> pd.Series:
        counts = df.isna().sum()
        return counts[counts > 0]

    @staticmethod
    def traffic_summary(df: pd.DataFrame) -> dict[str, float]:
        if df.empty:
            return {}

        valid = df.dropna(subset=["vehicle_count", "avg_speed_kmph"])
        if valid.empty:
            return {}

        return {
            "total_vehicles": float(valid["vehicle_count"].sum()),
            "average_speed": float(valid["avg_speed_kmph"].mean()),
            "average_vehicles": float(valid["vehicle_count"].mean()),
            "high_congestion_percent": float(
                df["congestion_level"].isin(["High", "Severe"]).mean() * 100
            ),
        }

    @staticmethod
    def hourly_traffic(df: pd.DataFrame) -> pd.DataFrame:
        valid = df.dropna(subset=["hour", "vehicle_count"])
        if valid.empty:
            return pd.DataFrame(
                columns=["hour", "vehicle_count", "avg_speed_kmph"]
            )

        return valid.groupby("hour", as_index=False).agg(
            vehicle_count=("vehicle_count", "mean"),
            avg_speed_kmph=("avg_speed_kmph", "mean"),
        ).sort_values("hour")

    @staticmethod
    def traffic_by_city(df: pd.DataFrame) -> pd.DataFrame:
        valid = df.dropna(subset=["vehicle_count"])
        if valid.empty:
            return pd.DataFrame(
                columns=["city", "vehicle_count", "avg_speed_kmph"]
            )

        return valid.groupby("city", as_index=False).agg(
            vehicle_count=("vehicle_count", "sum"),
            avg_speed_kmph=("avg_speed_kmph", "mean"),
        ).sort_values("vehicle_count", ascending=False)

    @staticmethod
    def registration_by_city(df: pd.DataFrame) -> pd.DataFrame:
        cols = [
            "city", "district", "registration_year", "registered_vehicles"
        ]
        if df.empty:
            return pd.DataFrame(columns=cols)

        return (
            df[cols]
            .dropna(subset=["registered_vehicles"])
            .drop_duplicates(subset=["city", "registration_year"])
            .sort_values("registered_vehicles", ascending=False)
        )

    def generate_insights(self, df: pd.DataFrame) -> list[str]:
        if df.empty:
            return ["No traffic records match the selected filters."]

        insights = []
        hourly = self.hourly_traffic(df)

        if not hourly.empty:
            peak = hourly.loc[hourly["vehicle_count"].idxmax()]
            insights.append(
                f"Highest average hourly vehicle count occurs around "
                f"{int(peak['hour']):02d}:00."
            )

        by_city = self.traffic_by_city(df)
        if not by_city.empty:
            busiest = by_city.iloc[0]
            insights.append(
                f"{busiest['city']} has the highest total simulated vehicle "
                f"count ({busiest['vehicle_count']:,.0f}) in this selection."
            )

        speeds = df["avg_speed_kmph"].dropna()
        if not speeds.empty:
            insights.append(
                f"Mean simulated traffic speed is {speeds.mean():.1f} km/h."
            )

        high = df["congestion_level"].isin(["High", "Severe"]).mean() * 100
        insights.append(
            f"{high:.1f}% of selected records are labelled High or Severe congestion."
        )

        registration = self.registration_by_city(df)
        if not registration.empty:
            row = registration.iloc[0]
            insights.append(
                f"Official registration context: {row['district']} had "
                f"{int(row['registered_vehicles']):,} registered vehicles in "
                f"{row['registration_year']}. This is district-wide data, "
                "not a road traffic count."
            )

        return insights

    def build_report(self, df, filters, total_rows) -> str:
        lines = [
            "SMART CITY DASHBOARD - TRAFFIC REPORT",
            "=" * 40,
            "Hourly counts/speeds: simulated examples, not measured traffic.",
            "Registrations: district-level context, not road traffic counts.",
            f"Generated at: {datetime.now():%Y-%m-%d %H:%M:%S}",
            f"Total rows: {total_rows}",
            f"Filtered rows: {len(df)}",
            "",
            "Filters applied:",
        ]
        lines.extend(f"  - {key}: {value}" for key, value in filters.items())
        lines.extend(["", "Insights:"])
        lines.extend(f"  - {item}" for item in self.generate_insights(df))
        return "\n".join(lines)
