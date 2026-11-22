from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json, re, xml.etree.ElementTree as ET
import pandas as pd
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[2]
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
TEXT_EXT = {".txt"}
TABLE_EXT = {".csv", ".tsv"}
JSON_EXT = {".json"}

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def inspect_csv(path):
    result = {"path": str(path.relative_to(ROOT)), "format": path.suffix.lower()}
    try:
        df = pd.read_csv(path, sep="\t" if path.suffix.lower()==".tsv" else ",",
                         nrows=100000, low_memory=False)
        result.update({
            "rows_inspected": int(len(df)), "columns": list(map(str, df.columns)),
            "missing_fraction": {str(k): round(float(v), 5) for k,v in df.isna().mean().items()},
            "dtypes": {str(k): str(v) for k,v in df.dtypes.items()},
            "duplicate_rows_inspected": int(df.duplicated().sum())
        })
        for col in df.columns:
            if df[col].dtype == "object":
                result.setdefault("sample_values", {})[str(col)] = [
                    str(x)[:100] for x in df[col].dropna().astype(str).unique()[:5]
                ]
    except Exception as exc:
        result["error"] = str(exc)
    return result

def inspect_coco(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        images = data.get("images", [])
        anns = data.get("annotations", [])
        cats = data.get("categories", [])
        counts = Counter(str(a.get("category_id")) for a in anns)
        cat_names = {str(c.get("id")): c.get("name") for c in cats}
        return {"path": str(path.relative_to(ROOT)), "format": "json",
                "json_type": "coco_candidate",
                "images_declared": len(images), "annotations": len(anns),
                "categories": [{"id": c.get("id"), "name": c.get("name")} for c in cats],
                "annotation_counts_by_category": {
                    cat_names.get(k, k): v for k,v in counts.items()
                },
                "images_missing_file_name": sum(not x.get("file_name") for x in images)}
    except Exception as exc:
        return {"path": str(path.relative_to(ROOT)), "format": "json", "error": str(exc)}

def inspect_yolo(path):
    rows, malformed, classes = 0, 0, Counter()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        try:
            if len(parts) < 5:
                raise ValueError()
            cls = int(float(parts[0]))
            nums = [float(x) for x in parts[1:]]
            if not all(0 <= x <= 1 for x in nums[:4]):
                raise ValueError()
            rows += 1
            classes[str(cls)] += 1
        except Exception:
            malformed += 1
    return {"path": str(path.relative_to(ROOT)), "format": "yolo_txt",
            "valid_label_rows": rows, "malformed_rows": malformed,
            "counts_by_class_id": dict(classes)}

def inspect_xml(path):
    try:
        root = ET.parse(path).getroot()
        boxes = root.findall(".//object")
        labels = Counter((o.findtext("name") or "UNKNOWN") for o in boxes)
        return {"path": str(path.relative_to(ROOT)), "format": "xml",
                "xml_type": "pascal_voc_candidate",
                "image_filename": root.findtext("filename"),
                "objects": len(boxes), "counts_by_label": dict(labels)}
    except Exception as exc:
        return {"path": str(path.relative_to(ROOT)), "format": "xml", "error": str(exc)}

def inventory_tree(base=None):
    base = Path(base) if base else ROOT / "data"
    records, duplicates = [], defaultdict(list)
    if not base.exists():
        return {"root": str(base), "files": [], "summary": {}}
    for p in sorted(x for x in base.rglob("*") if x.is_file()):
        if p.name.endswith(".part"):
            continue
        rec = {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
               "sha256": file_sha256(p)}
        ext = p.suffix.lower()
        if ext in IMAGE_EXT:
            try:
                with Image.open(p) as im:
                    rec.update({"format": "image", "image_format": im.format,
                                "width": im.width, "height": im.height,
                                "mode": im.mode, "image_valid": True})
            except (UnidentifiedImageError, OSError) as exc:
                rec.update({"format": "image", "image_valid": False, "error": str(exc)})
        elif ext in TABLE_EXT:
            rec.update(inspect_csv(p))
        elif ext in JSON_EXT:
            rec.update(inspect_coco(p))
        elif ext == ".xml":
            rec.update(inspect_xml(p))
        elif ext in TEXT_EXT:
            rec.update(inspect_yolo(p))
        else:
            rec["format"] = ext.lstrip(".") or "unknown"
        duplicates[rec["sha256"]].append(rec["path"])
        records.append(rec)
    duplicate_groups = [v for v in duplicates.values() if len(v) > 1]
    formats = Counter(r.get("format", "unknown") for r in records)
    images = [r for r in records if r.get("format") == "image"]
    return {
        "root": str(base), "files": records,
        "duplicate_groups": duplicate_groups,
        "summary": {"file_count": len(records), "formats": dict(formats),
                    "image_count": len(images),
                    "invalid_images": sum(r.get("image_valid") is False for r in images),
                    "duplicate_groups": len(duplicate_groups)}
    }
