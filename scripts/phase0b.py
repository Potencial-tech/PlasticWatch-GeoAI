#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from plasticwatch_phase0b.registry import load_registry
from plasticwatch_phase0b.acquisition import acquire_dataset
from plasticwatch_phase0b.inventory import inventory_tree
from plasticwatch_phase0b.audit import audit

def main():
    parser = argparse.ArgumentParser(description="PlasticWatch GeoAI Phase 0B tools")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-registry")
    acq = sub.add_parser("acquire")
    acq.add_argument("--only", action="append", default=[])
    acq.add_argument("--no-extract", action="store_true")
    inv = sub.add_parser("inventory")
    inv.add_argument("--root", default=None)
    au = sub.add_parser("audit")
    au.add_argument("--out", default="reports/phase0b_audit")
    args = parser.parse_args()

    if args.command == "validate-registry":
        reg = load_registry()
        print(f"Registry valid: {len(reg['datasets'])} unique dataset entries")
    elif args.command == "acquire":
        reg = load_registry()
        selected = [x for x in reg["datasets"] if not args.only or x["id"] in args.only]
        if args.only:
            missing = set(args.only) - {x["id"] for x in selected}
            if missing: parser.error(f"Unknown dataset ids: {sorted(missing)}")
        for item in selected:
            print(json.dumps(acquire_dataset(item, extract=not args.no_extract), ensure_ascii=False))
    elif args.command == "inventory":
        print(json.dumps(inventory_tree(args.root), indent=2, ensure_ascii=False))
    elif args.command == "audit":
        result = audit(args.out)
        print(f"Audit written to {args.out}")
        print(f"Datasets: {result['dataset_count']}; local files: {result['inventory']['summary'].get('file_count',0)}")

if __name__ == "__main__":
    main()
