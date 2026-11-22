# PlasticWatch GeoAI — Phase 0C (Andhra Pradesh & Telangana)

This add-on prepares a traceable acquisition and validation workflow for AP and Telangana. It does **not** claim that any dataset has already been downloaded, and it does not create plastic labels from water-quality records.

## Scope and evidence classes

1. Direct macroplastic observations / floating-litter images — potential plastic targets after annotation review.
2. Microplastic field measurements — separate target and sampling compartment; never merge with macroplastic image labels.
3. CPCB/CWC water-quality observations — environmental context only, not plastic labels.
4. GIS / satellite / catchment layers — spatial covariates, not direct plastic observations.

## Official starting sources

- [NWDP/NWIC portal](https://nwdp.nwic.gov.in/)
- [CPCB physical parameters](https://nwdp.nwic.gov.in/en/dataset/surface-water-quality-manual-physical-parameters-cpcb)
- [CPCB biological parameters](https://nwdp.nwic.gov.in/en/dataset/surface-water-quality-manual-biological-parameters-cpcb)
- [CPCB chemical parameters](https://nwdp.nwic.gov.in/dataset/surface-water-quality-manual-chemical-parameters-cpcb)
- [CWC physical parameters](https://nwdp.nwic.gov.in/en/dataset/surface-water-quality-manual-physical-parameters-central-water-commission-cwc)
- [CWC chemical parameters — AP page](https://nwdp.nwic.gov.in/dataset/surface-water-quality-manual-chemical-parameters-andhra-pradesh-central-water-commission-cwc)
- [CWC biological parameters](https://nwdp.nwic.gov.in/en/dataset/surface-water-quality-manual-biological-parameters-cwc)
- [OGD surface-water quality catalogue](https://data.gov.in/catalog/surface-water-quality)

The portal catalogue exposes state-specific resources and different periods. Select and download AP and Telangana resources separately. A catalogue entry is not proof that a file has been downloaded or that it contains the expected stations/fields.

## Install and run

Copy this add-on into the root of your existing repository, preserving the current files.

```powershell
python -m pip install -r requirements.txt
python scripts/phase0c_validate.py --input data/raw --output reports/phase0c
```

The validator scans CSV files under the input directory, records file hashes, inspects columns, missingness, duplicate rows, likely date and coordinate columns, coordinate range anomalies and basic AP/Telangana state-name matches. It does not auto-correct values or assert administrative membership from coordinates.

Optional explicit state names and column overrides can be supplied in a JSON sidecar later; do not rename original source columns in raw files.

## Raw-data directory convention

```text
data/raw/
  NWDP/
    Andhra_Pradesh/<dataset_id>/<original_filename>.csv
    Telangana/<dataset_id>/<original_filename>.csv
  CPCB/
  CWC/
```

Never overwrite raw source files. Keep provider landing page, exact resource title, download date, terms/licence and checksum in the manifest.

## Acquisition manifest

Start from `metadata/phase0c_acquisition_manifest.csv`. One row per downloaded resource. Use `not_downloaded` until the file is actually present locally. Leave unknown fields blank rather than guessing.

## Validation gates

- Provenance: official source, exact resource name, retrieval date, terms/licence, checksum.
- Integrity: file opens, encoding/delimiter, size, malformed rows.
- Schema: station identifier, date, coordinates, parameter names and original units.
- Spatial: raw coordinates retained; flag out-of-range/suspect points; verify AP/Telangana membership against a documented boundary layer in a later GIS QA step.
- Temporal: preserve original date string and report coverage/gaps.
- Scientific role: water quality is context; macroplastic and microplastic are distinct targets.
- Image QA: class taxonomy, duplicate/near-duplicate frames, survey/site grouping and licence review.

## Important restrictions

- Do not treat missing observations as zero.
- Do not turn CPCB/CWC exceedances, turbidity, coliforms, population, roads or drainage into plastic labels.
- Do not infer a confirmed plastic hotspot from contextual covariates. Without direct local labels, describe outputs as susceptibility or survey-priority areas.
- Do not merge the Dal Lake image datasets with AP/Telangana observations as if they were local ground truth.
- Do not commit large raw datasets, restricted files, credentials or API keys to Git.

## Exit criteria

Phase 0C is complete only when each accepted source has a verified file, traceable terms, checksum, schema report, spatial/temporal QA and an explicit scientific-role classification. Report local plastic ground-truth gaps honestly.
