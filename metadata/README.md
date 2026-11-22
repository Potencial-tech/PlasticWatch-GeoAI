# Metadata

`acquisitions.jsonl` is an append-only record written by the acquisition command. Each record includes the dataset ID, status, source URL, retrieval timestamp and (for successful downloads) file path, byte count and SHA-256.

`inventory.json` and reports are generated outputs. They should be reviewed before committing. Do not put credentials or restricted source files here.
