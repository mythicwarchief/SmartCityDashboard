"""Shared CSVManager base class (utils/common.py).

DRAFT of the class the team designs together. Vaishnav's AirQualityManager extends it.
Agree the final version with Shreyas, Adithyadev and Kiran - they extend the same class.

Concepts shown (good for the viva):
    * Encapsulation  - the DataFrame lives in a protected attribute `_data`,
                       exposed read-only through the `data` @property.
    * Inheritance    - each dataset manager subclasses CSVManager and overrides the
                       hooks `_prepare()` (validation) and `_coerce()` (typing).
    * Safe writes    - temp file in the same folder + os.replace().
    * try/except/else/finally on every CSV read and write.
    * Methods RETURN values (success flag + message, or a DataFrame) - they never print.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd


class CSVManager:
    """Generic CRUD manager for one CSV file with a unique id column."""

    def __init__(self, filepath, columns: list[str], id_column: str = "record_id"):
        self._filepath = Path(filepath)
        self._columns = list(columns)
        self._id_column = id_column
        self._data = pd.DataFrame(columns=self._columns)  # protected attribute
        self.load_status = "not_loaded"  # ok | empty | missing | error
        self.load_message = ""

    # ---------------------------------------------------------- encapsulation
    @property
    def data(self) -> pd.DataFrame:
        """Read-only copy of the current data (callers cannot modify _data directly)."""
        return self._data.copy()

    @property
    def filepath(self) -> Path:
        return self._filepath

    @property
    def columns(self) -> list[str]:
        return list(self._columns)

    # ------------------------------------------------------------------ hooks
    def _coerce(self, df: pd.DataFrame) -> pd.DataFrame:
        """Subclass hook: convert column types / derive columns. Default: unchanged."""
        return df

    def _prepare(self, record: dict[str, Any], is_new: bool = True) -> tuple[dict[str, Any], list[str]]:
        """Subclass hook: validate and clean one record. Returns (clean_record, errors)."""
        errors = [f"'{c}' is required." for c in self._columns
                  if record.get(c) is None or record.get(c) == ""]
        return {c: record.get(c) for c in self._columns}, errors

    # ------------------------------------------------------------------- load
    def load(self) -> tuple[bool, str]:
        """Read the CSV fresh from disk. Returns (ok, message) and sets load_status."""
        ok, msg, status = False, "", "error"
        try:
            df = pd.read_csv(self._filepath)
        except FileNotFoundError:
            status = "missing"
            msg = f"The data file '{self._filepath.name}' was not found."
            self._data = pd.DataFrame(columns=self._columns)
        except pd.errors.EmptyDataError:
            status, ok = "empty", True
            msg = f"'{self._filepath.name}' is empty. Add a record to get started."
            self._data = self._coerce(pd.DataFrame(columns=self._columns))
        except pd.errors.ParserError:
            msg = f"'{self._filepath.name}' is corrupted and could not be read as CSV."
        except (PermissionError, UnicodeDecodeError, OSError) as exc:
            msg = f"Could not read '{self._filepath.name}': {exc}"
        except Exception as exc:  # last-resort guard so the page never shows a traceback
            msg = f"Unexpected problem while reading the file: {exc}"
        else:
            missing_cols = [c for c in self._columns if c not in df.columns]
            if missing_cols:
                msg = f"The file is missing required column(s): {', '.join(missing_cols)}."
            else:
                self._data = self._coerce(df[self._columns].copy())
                ok = True
                if self._data.empty:
                    status, msg = "empty", "The file has headers but no records yet."
                else:
                    status, msg = "ok", f"Loaded {len(self._data)} records."
        finally:
            self.load_status = status
            self.load_message = msg
        return ok, msg

    # ------------------------------------------------------------- safe write
    def _atomic_write(self, df: pd.DataFrame) -> tuple[bool, str]:
        """Write df to a temp file in the same folder, then swap it in with os.replace()."""
        tmp_path = None
        ok, msg = False, ""
        try:
            self._filepath.parent.mkdir(parents=True, exist_ok=True)
            out = df.copy()
            for col in out.columns:
                if pd.api.types.is_datetime64_any_dtype(out[col]):
                    out[col] = out[col].dt.strftime("%Y-%m-%d")
            fd, tmp_path = tempfile.mkstemp(dir=self._filepath.parent, suffix=".tmp")
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
                out.to_csv(fh, index=False)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, self._filepath)  # atomic swap: no half-written CSV
            tmp_path = None
        except OSError as exc:
            msg = f"Could not save the file: {exc}"
        except Exception as exc:
            msg = f"Unexpected problem while saving: {exc}"
        else:
            ok, msg = True, "Saved."
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        return ok, msg

    def _commit(self, new_df: pd.DataFrame) -> tuple[bool, str]:
        """Persist new_df; only replace in-memory data if the write succeeded."""
        ok, msg = self._atomic_write(new_df)
        if ok:
            self._data = new_df
            self.load_status = "ok" if len(new_df) else "empty"
        return ok, msg

    def create_empty_file(self) -> tuple[bool, str]:
        """Create the CSV with only the header row (used when the file is missing)."""
        ok, msg = self._commit(self._coerce(pd.DataFrame(columns=self._columns)))
        return ok, ("Created an empty file with the correct headers." if ok else msg)

    # ------------------------------------------------------------------- CRUD
    def _index_of(self, record_id) -> Any:
        """Row label of record_id, or None if it does not exist / is not a valid id."""
        try:
            rid = int(record_id)
        except (TypeError, ValueError):
            return None
        mask = (self._data[self._id_column] == rid).fillna(False).astype(bool)
        hits = self._data.index[mask]
        return hits[0] if len(hits) else None

    def get_record(self, record_id) -> dict[str, Any] | None:
        idx = self._index_of(record_id)
        return None if idx is None else self._data.loc[idx].to_dict()

    def next_id(self) -> int:
        ids = pd.to_numeric(self._data[self._id_column], errors="coerce").dropna()
        return int(ids.max()) + 1 if len(ids) else 1

    def create(self, record: dict[str, Any]) -> tuple[bool, str]:
        """Validate -> reject duplicate id -> append -> save."""
        clean, errors = self._prepare(record, is_new=True)
        if errors:
            return False, " ".join(errors)
        if self._index_of(clean[self._id_column]) is not None:
            return False, f"Duplicate entry: a record with ID {clean[self._id_column]} already exists."
        new_df = pd.concat([self._data, pd.DataFrame([clean])], ignore_index=True)
        ok, msg = self._commit(self._coerce(new_df))
        return (True, f"Record {clean[self._id_column]} added.") if ok else (False, msg)

    def read(self, query: str | None = None, sort_by: str | None = None,
             ascending: bool = True) -> pd.DataFrame:
        """Return records, optionally text-searched (any column) and sorted."""
        df = self.data
        if query:
            text = df.astype(str)
            mask = pd.Series(False, index=df.index)
            for col in text.columns:
                mask |= text[col].str.contains(query, case=False, regex=False, na=False)
            df = df[mask]
        if sort_by in df.columns:
            df = df.sort_values(sort_by, ascending=ascending, na_position="last")
        return df

    def update(self, record_id, changes: dict[str, Any]) -> tuple[bool, str]:
        """Select by id -> merge changes -> re-validate -> save."""
        idx = self._index_of(record_id)
        if idx is None:
            return False, f"Record not found: there is no record with ID {record_id}."
        merged = self._data.loc[idx].to_dict()
        merged.update(changes)
        merged[self._id_column] = self._data.loc[idx, self._id_column]  # id is immutable
        clean, errors = self._prepare(merged, is_new=False)
        if errors:
            return False, " ".join(errors)
        new_df = self._data.copy()
        for col, value in clean.items():
            new_df.at[idx, col] = value
        ok, msg = self._commit(self._coerce(new_df))
        return (True, f"Record {record_id} updated.") if ok else (False, msg)

    def delete(self, record_id) -> tuple[bool, str]:
        """Remove a record by id and rewrite the CSV without that row."""
        idx = self._index_of(record_id)
        if idx is None:
            return False, f"Record not found: there is no record with ID {record_id}."
        new_df = self._data.drop(index=idx).reset_index(drop=True)
        ok, msg = self._commit(new_df)
        return (True, f"Record {record_id} deleted.") if ok else (False, msg)