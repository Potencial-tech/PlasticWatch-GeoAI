from pathlib import Path
from datetime import datetime, timezone
import json, yaml
from .registry import load_registry
from .inventory import inventory_tree

ROOT = Path(__file__).resolve().parents[2]

def load_acquisition_log():
    path = ROOT / "metadata" / "acquisitions.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try: out.append(json.loads(line))
        except json.JSONDecodeError: continue
    return out

def audit(out_dir=None):
    registry = load_registry()
    inventory = inventory_tree()
    log = load_acquisition_log()
    latest = {}
    for row in log:
        latest[row.get("dataset_id")] = row
    dataset_rows = []
    for item in registry["datasets"]:
        acquisition = latest.get(item["id"], {})
        dataset_rows.append({
            "id": item["id"], "title": item["title"],
            "provider": item["provider"], "priority": item.get("priority"),
            "target": item["target"], "modality": item["modality"],
            "geography": item.get("geography", []),
            "licence_status": item["licence_status"],
            "access": item["access"],
            "landing_url": item["landing_url"],
            "download_url_configured": bool(item.get("download_url")),
            "acquisition_status": acquisition.get("status", "not_attempted"),
            "acquired_path": acquisition.get("path"),
            "notes": item.get("notes", "")
        })
    result = {
        "project": "PlasticWatch GeoAI",
        "phase": "0B",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "registry_version": registry.get("registry_version"),
        "dataset_count": len(dataset_rows),
        "datasets": dataset_rows,
        "inventory": inventory,
        "acquisition_log_entries": len(log),
        "scientific_warnings": [
            "Water-quality measurements are contextual variables, not plastic labels.",
            "Microplastic field measurements and floating macroplastic imagery are different targets.",
            "A landing page does not establish that a dataset file was acquired.",
            "Unknown or unverified licences require review before redistribution or commercial use.",
            "Unobserved locations must not be encoded as zero-plastic observations.",
            "Near-duplicate images and frames can cause spatial/temporal leakage across splits."
        ]
    }
    if out_dir:
        out = Path(out_dir)
        if not out.is_absolute(): out = ROOT / out
        out.mkdir(parents=True, exist_ok=True)
        (out / "phase0b_audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        (out / "phase0b_audit.md").write_text(render_markdown(result), encoding="utf-8")
    return result

def render_markdown(result):
    lines = [
        "# PlasticWatch GeoAI — Phase 0B Audit",
        f"\nGenerated (UTC): {result['generated_utc']}",
        f"\nRegistry version: {result['registry_version']}",
        f"\nRegistered datasets: {result['dataset_count']}",
        "\n## Dataset register",
        "\n| ID | Provider | Target | Licence | Acquisition |",
        "|---|---|---|---|---|"
    ]
    for d in result["datasets"]:
        lines.append(f"| {d['id']} | {d['provider']} | {d['target']} | {d['licence_status']} | {d['acquisition_status']} |")
    s = result["inventory"]["summary"]
    lines += ["\n## Local file inventory",
              f"\n- Files: {s.get('file_count', 0)}",
              f"- Images: {s.get('image_count', 0)}",
              f"- Invalid images: {s.get('invalid_images', 0)}",
              f"- Duplicate file groups: {s.get('duplicate_groups', 0)}",
              f"- Formats: `{s.get('formats', {})}`",
              "\n## Scientific and governance warnings"]
    lines += [f"\n- {w}" for w in result["scientific_warnings"]]
    lines += ["\n## Files inspected", ""]
    for f in result["inventory"].get("files", []):
        lines.append(f"- `{f['path']}` — {f.get('format')} — {f.get('bytes')} bytes")
        if f.get("error"): lines.append(f"  - Error: {f['error']}")
    return "\n".join(lines) + "\n"
