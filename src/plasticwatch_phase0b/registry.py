from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]

def load_registry(path=None):
    path = Path(path) if path else ROOT / "config" / "datasets.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("datasets"), list):
        raise ValueError("Registry must contain a datasets list")
    ids = set()
    required = {"id", "title", "provider", "landing_url", "modality", "target", "licence_status", "access"}
    for item in payload["datasets"]:
        missing = required - set(item)
        if missing:
            raise ValueError(f"{item.get('id', '<unknown>')}: missing {sorted(missing)}")
        if item["id"] in ids:
            raise ValueError(f"Duplicate dataset id: {item['id']}")
        ids.add(item["id"])
        if not str(item["landing_url"]).startswith(("https://", "http://")):
            raise ValueError(f"{item['id']}: landing_url must be HTTP(S)")
        if item.get("download_url") and not str(item["download_url"]).startswith(("https://", "http://")):
            raise ValueError(f"{item['id']}: download_url must be HTTP(S)")
    return payload
