from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, re, shutil, zipfile
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
EXTRACTED = ROOT / "data" / "extracted"
LOG = ROOT / "metadata" / "acquisitions.jsonl"

def sha256_file(path, chunk_size=1024*1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()

def _session():
    s = requests.Session()
    retry = Retry(total=4, connect=4, read=4, backoff_factor=1.0,
                  status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = os.getenv(
        "PLASTICWATCH_USER_AGENT", "PlasticWatch-GeoAI-Phase0B/0.1 (research dataset audit)"
    )
    return s

def _safe_name(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "download"

def _append_log(record):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def safe_extract_zip(zip_path, destination):
    destination = Path(destination).resolve()
    extracted = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            target = (destination / info.filename).resolve()
            if target != destination and destination not in target.parents:
                raise ValueError(f"Unsafe archive path rejected: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
            extracted.append(str(target))
    return extracted

def acquire_dataset(item, timeout=60, extract=True):
    url = item.get("download_url")
    now = datetime.now(timezone.utc).isoformat()
    if not url:
        record = {"dataset_id": item["id"], "status": "skipped_no_verified_direct_download_url",
                  "landing_url": item["landing_url"], "timestamp_utc": now}
        _append_log(record)
        return record

    RAW.mkdir(parents=True, exist_ok=True)
    name = _safe_name(item["id"])
    suffix = Path(url.split("?")[0]).suffix or ".download"
    target = RAW / f"{name}{suffix}"
    if target.exists():
        record = {"dataset_id": item["id"], "status": "skipped_existing_file",
                  "path": str(target.relative_to(ROOT)), "sha256": sha256_file(target),
                  "timestamp_utc": now}
        _append_log(record)
        return record

    temp = target.with_suffix(target.suffix + ".part")
    try:
        with _session().get(url, stream=True, timeout=timeout, allow_redirects=True) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            with temp.open("wb") as f:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
        if temp.stat().st_size == 0:
            raise ValueError("Downloaded file is empty")
        temp.replace(target)
        digest = sha256_file(target)
        extracted_files = []
        if extract and zipfile.is_zipfile(target):
            out = EXTRACTED / name
            out.mkdir(parents=True, exist_ok=True)
            extracted_files = safe_extract_zip(target, out)
        record = {
            "dataset_id": item["id"], "status": "downloaded",
            "source_url": url, "final_url": response.url,
            "path": str(target.relative_to(ROOT)), "bytes": target.stat().st_size,
            "sha256": digest, "content_type": content_type,
            "extracted_files": [str(Path(p).relative_to(ROOT)) for p in extracted_files],
            "timestamp_utc": now
        }
    except Exception as exc:
        if temp.exists():
            temp.unlink()
        record = {"dataset_id": item["id"], "status": "failed",
                  "source_url": url, "error": str(exc), "timestamp_utc": now}
    _append_log(record)
    return record
