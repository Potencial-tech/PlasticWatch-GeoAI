#!/usr/bin/env python3
"""Conservative CSV intake audit for PlasticWatch GeoAI Phase 0C."""
from pathlib import Path
import argparse, csv, hashlib, json, re
from datetime import datetime, timezone
import pandas as pd

STATE_TERMS = {
    "Andhra Pradesh": ["andhra pradesh", "andhra"],
    "Telangana": ["telangana"]
}
LAT_NAMES = {"lat", "latitude", "y", "station_latitude"}
LON_NAMES = {"lon", "long", "longitude", "x", "station_longitude"}
DATE_HINTS = ("date", "time", "year", "month")
ID_HINTS = ("station", "site", "location", "sample", "id", "code")

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def norm(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")

def inspect(path, root):
    row = {"path": str(path.relative_to(root)), "bytes": path.stat().st_size,
           "sha256": sha256(path), "format": path.suffix.lower()}
    try:
        df = pd.read_csv(path, low_memory=False, nrows=250000)
        cols = list(df.columns)
        normal = {c: norm(c) for c in cols}
        lat_cols = [c for c in cols if normal[c] in LAT_NAMES]
        lon_cols = [c for c in cols if normal[c] in LON_NAMES]
        date_cols = [c for c in cols if any(h in normal[c] for h in DATE_HINTS)]
        id_cols = [c for c in cols if any(h in normal[c] for h in ID_HINTS)]
        state_hits = {}
        for state, terms in STATE_TERMS.items():
            hits = []
            for c in cols:
                if df[c].dtype == "object":
                    values = df[c].dropna().astype(str).str.lower()
                    if any(values.str.contains(re.escape(t), regex=True).any() for t in terms):
                        hits.append(str(c))
            state_hits[state] = hits
        coordinate_check = {"status": "not_assessed"}
        if lat_cols and lon_cols:
            lat = pd.to_numeric(df[lat_cols[0]], errors="coerce")
            lon = pd.to_numeric(df[lon_cols[0]], errors="coerce")
            coordinate_check = {
                "latitude_column": str(lat_cols[0]), "longitude_column": str(lon_cols[0]),
                "valid_pairs": int((lat.between(-90, 90) & lon.between(-180, 180)).sum()),
                "null_or_unparseable_pairs": int((lat.isna() | lon.isna()).sum()),
                "outside_coordinate_range": int((~lat.between(-90, 90) | ~lon.between(-180, 180)).sum()),
                "note": "Range checks only; this does not establish AP/Telangana membership."
            }
        row.update({
            "rows_inspected_max_250k": int(len(df)),
            "columns": [str(c) for c in cols],
            "missing_fraction": {str(c): round(float(df[c].isna().mean()), 5) for c in cols},
            "duplicate_rows_in_sample": int(df.duplicated().sum()),
            "likely_station_or_site_columns": [str(c) for c in id_cols],
            "likely_date_columns": [str(c) for c in date_cols],
            "state_name_column_candidates": state_hits,
            "coordinate_check": coordinate_check,
            "status": "inspected"
        })
    except Exception as exc:
        row.update({"status": "error", "error": str(exc)})
    return row

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/raw")
    ap.add_argument("--output", default="reports/phase0c")
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    inp = Path(args.input)
    if not inp.is_absolute(): inp = root / inp
    out = Path(args.output)
    if not out.is_absolute(): out = root / out
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in inp.rglob("*") if p.is_file() and p.suffix.lower() in {".csv", ".tsv"})
    results = [inspect(p, inp) for p in files]
    report = {
        "project": "PlasticWatch GeoAI", "phase": "0C",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(inp), "csv_tsv_file_count": len(files),
        "files": results,
        "scientific_warnings": [
            "CPCB/CWC water-quality data are contextual variables, not plastic labels.",
            "Coordinate range checks do not verify state-boundary membership.",
            "Unobserved sites are not zero-plastic observations.",
            "Do not combine macroplastic imagery and microplastic field measurements as one target.",
            "Do not silently impute, delete outliers, change units or correct coordinates."
        ]
    }
    (out / "phase0c_validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Phase 0C validation report", "", f"Generated UTC: {report['generated_utc']}",
             f"CSV/TSV files inspected: {len(files)}", ""]
    for item in results:
        lines += [f"## {item['path']}", f"- Status: {item['status']}",
                  f"- Bytes: {item['bytes']}", f"- SHA-256: `{item['sha256']}`"]
        if item.get("status") == "inspected":
            lines += [f"- Rows inspected: {item['rows_inspected_max_250k']}",
                      f"- Duplicate rows in inspected sample: {item['duplicate_rows_in_sample']}",
                      f"- Likely date columns: {item['likely_date_columns']}",
                      f"- Likely station/site columns: {item['likely_station_or_site_columns']}",
                      f"- Coordinate check: `{json.dumps(item['coordinate_check'])}`"]
        else:
            lines += [f"- Error: {item.get('error')}"]
        lines.append("")
    lines += ["## Scientific warnings", ""] + [f"- {w}" for w in report["scientific_warnings"]]
    (out / "phase0c_validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Inspected {len(files)} CSV/TSV files. Report: {out}")
    if any(x["status"] == "error" for x in results):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
