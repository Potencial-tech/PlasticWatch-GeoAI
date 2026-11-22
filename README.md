# PlasticWatch GeoAI — Phase 0B Dataset Acquisition & Audit

A reproducible Python package for registering, acquiring, inventorying and auditing plastic-litter imagery and supporting environmental datasets.

**Important:** Phase 0B is a data-ingestion and quality-audit workflow. It does not train a plastic detector, infer pollution from water-quality variables, or claim that a dataset has been downloaded merely because a catalogue URL is listed.

## Scope

- Dataset registry with source URL, DOI, geography, modality, labels, licence status and acquisition status.
- Safe HTTP acquisition with retries, streaming, checksums and provenance records.
- Optional archive extraction with path-traversal protection.
- Inventory of CSV/TSV, JSON/COCO, XML/Pascal VOC, YOLO text labels, ZIP and common image formats.
- Image dimensions, corrupt-image checks, SHA-256 duplicate detection and annotation statistics.
- CSV schema/missingness/type summaries and optional region-keyword screening.
- JSON and Markdown audit reports.
- Tests using synthetic fixtures only; no synthetic records are added to research datasets.

## Quick start

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python scripts/phase0b.py validate-registry
python scripts/phase0b.py inventory
python scripts/phase0b.py audit
```

Run a metadata-only audit first. It does not access external websites:

```bash
python scripts/phase0b.py audit --out reports/phase0b_audit
```

Acquire only explicitly enabled, direct-download sources:

```bash
python scripts/phase0b.py acquire --only aqua_plastic_waste
python scripts/phase0b.py acquire --only risid
```

The Mendeley, Figshare and Hugging Face entries are registered as landing pages unless a direct file URL is verified and configured. The tool will not guess their download endpoints. Add a verified `download_url` to `config/datasets.yaml` after checking the provider's terms and licence.

For government sources, obtain the official CSV/ZIP download URL from the relevant portal and place it in the corresponding `download_url` field. Portal landing pages are not treated as file downloads.

```bash
python scripts/phase0b.py audit --out reports/phase0b_audit
```

## Directory layout

```text
config/
  datasets.yaml
  region_keywords.yaml
data/
  raw/                 # acquired original files; never edit
  extracted/           # safely extracted archives
  interim/
  processed/
metadata/
  acquisitions.jsonl   # append-only acquisition log
  inventory.json
reports/
  phase0b_audit/
scripts/
  phase0b.py
src/plasticwatch_phase0b/
  registry.py
  acquisition.py
  inventory.py
  audit.py
  reporting.py
tests/
```

## Data governance rules

1. Never overwrite raw source files by default.
2. Preserve source URL, retrieval timestamp, byte count and SHA-256.
3. A landing page is not a dataset file.
4. A licence marked `verify` or `unknown` must be checked before redistribution or commercial use.
5. Do not merge macroplastic imagery, microplastic concentration measurements and general water-quality records into one target variable.
6. Unobserved sites are not zero-plastic sites. Absence requires an explicit surveyed non-detection.
7. CPCB/CWC water-quality indicators are contextual environmental variables, not plastic labels.
8. Keep original station names, units and timestamps; do not impute or remove outliers during acquisition.
9. Treat duplicate images and repeated frames as potential leakage between train and test splits.
10. Report incomplete, inaccessible and failed sources honestly.

## Registered starting sources

The registry includes:
- AquaPlasticWaste 2026 — Dal Lake drone imagery (Mendeley landing page).
- FloPWD — Dal Lake drone imagery (Mendeley landing page).
- IWHR floating debris — Figshare DOI landing page.
- RiSID — Zenodo record.
- FloatWaste — Hugging Face and Zenodo landing pages.
- FloW — GitHub project / access instructions.
- River plastic hotspot detection reference implementation.
- CPCB NWMP, CWC and National Water Data Portal catalogue pages.
- CPCB river water-quality data repository mirror (for comparison only).
- Global Plastic Watch API access information (registration required; not assumed accessible).

The registry is a discovery register, not a guarantee that every source is downloadable or suitable for a specific study.

## CLI

```bash
python scripts/phase0b.py validate-registry
python scripts/phase0b.py acquire
python scripts/phase0b.py inventory
python scripts/phase0b.py audit
python scripts/phase0b.py audit --out reports/run_2026_11_22
```

`acquire` only downloads entries with a verified direct `download_url`. It skips landing-page URLs. Use `--only dataset_id` to limit acquisition. It does not bypass logins, API keys, rate limits or provider access controls.

## Environment variables

- `DATA_GOV_IN_API_KEY`: optional key if a future data.gov.in resource is configured with its official API endpoint.
- `PLASTICWATCH_USER_AGENT`: optional descriptive User-Agent string.

Do not commit credentials, API keys or downloaded restricted datasets.

## Reproducibility

The audit records tool version, registry version, timestamps, file hashes, detected formats and quality flags. Keep generated reports and the registry under version control; keep large/raw data outside Git or use an approved data repository / Git LFS after reviewing dataset terms.

## Current limitations

- Dataset landing pages are catalogued but not scraped for undocumented download endpoints.
- Some providers require account access, application or click-through terms.
- The package inventories common formats; it does not fully validate every provider-specific annotation convention.
- Geospatial station coordinate validation and spatial joins are a later Phase 0C/Phase 1 task.
- Model-ready train/validation/test splits are deliberately not generated in Phase 0B.
