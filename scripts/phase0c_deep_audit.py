#!/usr/bin/env python3
"""Detailed, non-destructive audit of PlasticWatch GeoAI CSV/TSV water-quality files."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re
import pandas as pd

META_HINTS = {
    "slno", "station", "agency", "state lgd code", "state",
    "district lgd code", "district", "tehsil", "block", "village",
    "river", "basin", "tributary", "subtributary", "subsubtributary",
    "local river", "latitude", "longitude", "data acquisition time"
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def clean_name(value):
    return re.sub(r"\s+", " ", str(value).strip()).lower()

def audit_file(path, root):
    item = {
        "file": str(path.relative_to(root)),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    try:
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        df = pd.read_csv(path, sep=sep, low_memory=False)
        cols = list(df.columns)
        norm = {c: clean_name(c) for c in cols}

        station_col = next((c for c in cols if norm[c] == "station"), None)
        state_col = next((c for c in cols if norm[c] == "state"), None)
        district_col = next((c for c in cols if norm[c] == "district"), None)
        river_col = next((c for c in cols if norm[c] in {"river", "local river"}), None)
        basin_col = next((c for c in cols if norm[c] == "basin"), None)
        lat_col = next((c for c in cols if norm[c] == "latitude"), None)
        lon_col = next((c for c in cols if norm[c] == "longitude"), None)
        date_col = next((c for c in cols if norm[c] == "data acquisition time"), None)

        date_series = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True) if date_col else pd.Series(dtype="datetime64[ns]")
        parameter_cols = [c for c in cols if norm[c] not in META_HINTS]
        missing = {str(c): round(float(df[c].isna().mean()), 5) for c in parameter_cols}

        coords = None
        if lat_col and lon_col:
            lat = pd.to_numeric(df[lat_col], errors="coerce")
            lon = pd.to_numeric(df[lon_col], errors="coerce")
            pairs = pd.DataFrame({"lat": lat, "lon": lon}).dropna()
            coords = {
                "unique_coordinate_pairs": int(pairs.drop_duplicates().shape[0]),
                "null_or_unparseable_pairs": int((lat.isna() | lon.isna()).sum()),
                "out_of_range_pairs": int((~lat.between(-90, 90) | ~lon.between(-180, 180)).sum()),
            }

        state_counts = {}
        if state_col:
            state_counts = {str(k): int(v) for k, v in df[state_col].fillna("[NULL]").value_counts().items()}

        station_count = int(df[station_col].dropna().astype(str).str.strip().nunique()) if station_col else None
        station_date_dupes = None
        if station_col and date_col:
            station_date_dupes = int(df.duplicated(subset=[station_col, date_col]).sum())

        item.update({
            "status": "audited",
            "row_count": int(len(df)),
            "column_count": int(len(cols)),
            "columns": [str(c) for c in cols],
            "state_value_counts": state_counts,
            "unique_station_names": station_count,
            "unique_districts": int(df[district_col].dropna().astype(str).nunique()) if district_col else None,
            "unique_rivers": int(df[river_col].dropna().astype(str).nunique()) if river_col else None,
            "unique_basins": int(df[basin_col].dropna().astype(str).nunique()) if basin_col else None,
            "date_column": str(date_col) if date_col else None,
            "valid_parsed_dates": int(date_series.notna().sum()) if date_col else 0,
            "unparsed_or_missing_dates": int(date_series.isna().sum()) if date_col else len(df),
            "date_min": str(date_series.min().date()) if date_col and date_series.notna().any() else None,
            "date_max": str(date_series.max().date()) if date_col and date_series.notna().any() else None,
            "duplicate_full_rows": int(df.duplicated().sum()),
            "duplicate_station_date_rows": station_date_dupes,
            "coordinates": coords,
            "parameter_columns": [str(c) for c in parameter_cols],
            "parameter_missing_fraction": missing,
            "potential_parameter_columns_with_all_null": [str(c) for c in parameter_cols if df[c].isna().all()],
        })
    except Exception as exc:
        item.update({"status": "error", "error": str(exc)})
    return item

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw")
    parser.add_argument("--output", default="reports/phase0c_deep")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    root = Path(args.input)
    out = Path(args.output)
    if not root.is_absolute():
        root = repo / root
    if not out.is_absolute():
        out = repo / out
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".csv", ".tsv"})
    audits = [audit_file(p, root) for p in files]
    report = {
        "project": "PlasticWatch GeoAI",
        "phase": "0C detailed data audit",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "total_rows_across_files_not_deduplicated": sum(x.get("row_count", 0) for x in audits),
        "files": audits,
        "interpretation_warning": "Counts are file-level. Rows across files may overlap. Unique station labels are not necessarily unique physical sites. Parameter missingness is calculated per file. No state-boundary validation or plastic labels are inferred."
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "phase0c_deep_audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = ["# Phase 0C detailed data audit", "",
               f"- Files: {len(files)}",
               f"- Total rows across files (not deduplicated): {report['total_rows_across_files_not_deduplicated']}",
               f"- Generated UTC: {report['generated_utc']}", ""]
    for a in audits:
        summary += [f"## {a['file']}", f"- Status: {a['status']}"]
        if a["status"] == "audited":
            summary += [
                f"- Rows: {a['row_count']}",
                f"- Unique station names: {a['unique_station_names']}",
                f"- Unique districts / rivers / basins: {a['unique_districts']} / {a['unique_rivers']} / {a['unique_basins']}",
                f"- Date range: {a['date_min']} to {a['date_max']}",
                f"- Parsed / missing dates: {a['valid_parsed_dates']} / {a['unparsed_or_missing_dates']}",
                f"- Duplicate full rows: {a['duplicate_full_rows']}",
                f"- Duplicate station-date rows: {a['duplicate_station_date_rows']}",
                f"- Coordinate summary: `{json.dumps(a['coordinates'])}`",
                f"- State values: `{json.dumps(a['state_value_counts'], ensure_ascii=False)}`",
                "- Parameter missing fractions:"
            ]
            summary += [f"  - {k}: {v:.1%}" for k, v in a["parameter_missing_fraction"].items()]
        else:
            summary.append(f"- Error: {a.get('error')}")
        summary.append("")
    summary += ["## Interpretation", "", report["interpretation_warning"]]
    (out / "phase0c_deep_audit.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"Audited {len(files)} CSV/TSV files; report: {out}")
    if any(a["status"] == "error" for a in audits):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
