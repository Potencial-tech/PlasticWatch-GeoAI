# Phase 0C manual smoke test

1. Put one small official CSV copy under `data/raw/NWDP/Andhra_Pradesh/<dataset_id>/`.
2. Run `python scripts/phase0c_validate.py --input data/raw --output reports/phase0c`.
3. Confirm the JSON and Markdown reports are created.
4. Confirm SHA-256 and byte size are recorded.
5. Confirm coordinate range checks do not claim state membership.
6. Confirm contextual water-quality warnings remain in the report.
7. Record source title, licence/terms and download date in the acquisition manifest.

Do not add fabricated rows to test a research dataset. For software unit tests, create clearly labelled temporary synthetic fixtures outside `data/raw`.
