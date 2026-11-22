import sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from plasticwatch_phase0b.registry import load_registry
from plasticwatch_phase0b.acquisition import safe_extract_zip
from plasticwatch_phase0b.inventory import inventory_tree

def test_registry_has_unique_ids():
    data = load_registry()
    ids = [x["id"] for x in data["datasets"]]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 10

def test_safe_zip_extract(tmp_path):
    z = tmp_path / "ok.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("folder/file.txt", "hello")
    out = tmp_path / "out"
    paths = safe_extract_zip(z, out)
    assert (out / "folder" / "file.txt").read_text() == "hello"
    assert len(paths) == 1

def test_zip_path_traversal_rejected(tmp_path):
    z = tmp_path / "bad.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("../escape.txt", "bad")
    try:
        safe_extract_zip(z, tmp_path / "out")
    except ValueError:
        pass
    else:
        raise AssertionError("Path traversal archive should be rejected")
