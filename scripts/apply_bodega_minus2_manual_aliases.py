#!/usr/bin/env python3
"""
Aplica aliases manuais da BODEGA -2 sobre o catálogo.

Somente linhas não-tasca são consideradas.
Atualiza establecimientos.bodega.{unidades, localizacion} com merge:
- unidades: soma com valor existente
- localizacion: união sem duplicatas
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "lista_unica_vinos.csv"
DB_PATH = ROOT / "data" / "bodega_webapp.json"
ALIAS_PATH = ROOT / "config" / "bodega_minus2_manual_aliases.json"
REPORT_PATH = ROOT / "reports" / "bodega_minus2_manual_aliases_report.json"
TASCA_FILE = "tasca fina 18 de febrero.pdf"


def parse_qty(raw_qty: str) -> int:
    match = re.search(r"\d+", str(raw_qty or ""))
    return int(match.group(0)) if match else 0


def parse_cava_from_group(group: str) -> str | None:
    match = re.search(r"cava\s*(\d+)", str(group or ""), re.IGNORECASE)
    return match.group(1) if match else None


def normalize_balda_position(raw_position: str) -> str | None:
    text = str(raw_position or "").strip()
    if not text:
        return None
    clean = re.sub(r"\s+", " ", text.replace("·", " · ")).strip()
    match = re.match(
        r"^balda\s*(\d+)(?:\s*·\s*(izquierda|derecha|centro|[a-e]))?$",
        clean,
        re.IGNORECASE,
    )
    if not match:
        return clean.upper()
    balda = match.group(1)
    side_raw = (match.group(2) or "").upper()
    side = {"IZQUIERDA": "IZQ", "DERECHA": "DER", "CENTRO": "CEN"}.get(side_raw, side_raw)
    return f"BALDA {balda} · {side}" if side else f"BALDA {balda}"


def build_location(location_group: str, raw_position: str) -> str | None:
    pos = normalize_balda_position(raw_position)
    cava = parse_cava_from_group(location_group)
    if cava and pos:
        return f"CAVA {cava} · {pos}"
    if pos:
        return pos
    if cava:
        return f"CAVA {cava}"
    return None


def location_sort_key(value: str) -> tuple[int, int, str]:
    cava_match = re.search(r"CAVA\s+(\d+)", value, re.IGNORECASE)
    balda_match = re.search(r"BALDA\s+(\d+)", value, re.IGNORECASE)
    cava_n = int(cava_match.group(1)) if cava_match else 999
    balda_n = int(balda_match.group(1)) if balda_match else 999
    return (cava_n, balda_n, value)


def key_of(source_file: str, producer: str, item: str, ano_raw: str) -> tuple[str, str, str, str]:
    return (
        str(source_file or "").strip(),
        str(producer or "").strip(),
        str(item or "").strip(),
        str(ano_raw or "").strip(),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Aplica alterações no catálogo")
    args = parser.parse_args()

    rows = list(csv.DictReader(CSV_PATH.open("r", encoding="utf-8")))
    rows = [r for r in rows if (r.get("source_file") or "").strip() != TASCA_FILE]

    aliases_doc = json.load(ALIAS_PATH.open("r", encoding="utf-8"))
    aliases = aliases_doc.get("aliases", [])

    by_alias_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for alias in aliases:
        alias_key = key_of(
            alias.get("source_file"),
            alias.get("producer"),
            alias.get("item"),
            alias.get("ano_raw"),
        )
        by_alias_key[alias_key] = {
            "target_pod": alias.get("target_pod"),
            "reason": alias.get("reason"),
            "rows_count": 0,
            "qty_total": 0,
            "locations": set(),
        }

    missing_alias_keys = []
    for alias_key, payload in by_alias_key.items():
        source_file, producer, item, ano_raw = alias_key
        matched_rows = [
            r
            for r in rows
            if key_of(r.get("source_file"), r.get("producer"), r.get("item"), r.get("ano")) == alias_key
        ]
        if not matched_rows:
            missing_alias_keys.append(alias_key)
            continue
        payload["rows_count"] = len(matched_rows)
        payload["qty_total"] = sum(parse_qty(r.get("qty", "")) for r in matched_rows)
        payload["locations"] = {
            loc
            for loc in (
                build_location(r.get("location_group", ""), r.get("posicion", ""))
                for r in matched_rows
            )
            if loc
        }

    catalog = json.load(DB_PATH.open("r", encoding="utf-8"))
    by_pod = {str(w.get("pod", "")).strip(): w for w in catalog}

    updates = []
    for alias_key, payload in by_alias_key.items():
        pod = str(payload["target_pod"] or "").strip()
        wine = by_pod.get(pod)
        if not pod or not wine:
            continue

        if not isinstance(wine.get("establecimientos"), dict):
            wine["establecimientos"] = {}
        if not isinstance(wine["establecimientos"].get("bodega"), dict):
            wine["establecimientos"]["bodega"] = {
                "pvp": None,
                "unidades": None,
                "localizacion": None,
            }

        est = wine["establecimientos"]["bodega"]
        old_units = est.get("unidades")
        old_units_num = old_units if isinstance(old_units, int) else 0
        add_units = int(payload["qty_total"])
        new_units = old_units_num + add_units

        old_locations = set()
        if est.get("localizacion"):
            old_locations = {
                s.strip()
                for s in str(est["localizacion"]).split(" / ")
                if s.strip()
            }
        merged_locations = sorted(old_locations | payload["locations"], key=location_sort_key)
        new_location = " / ".join(merged_locations) if merged_locations else None

        updates.append(
            {
                "source_file": alias_key[0],
                "producer": alias_key[1],
                "item": alias_key[2],
                "ano_raw": alias_key[3],
                "target_pod": pod,
                "reason": payload["reason"],
                "rows_count": payload["rows_count"],
                "qty_add": add_units,
                "units_before": old_units,
                "units_after": new_units,
                "locations_add": sorted(payload["locations"], key=location_sort_key),
                "location_before": est.get("localizacion"),
                "location_after": new_location,
            }
        )

        est["unidades"] = new_units
        est["localizacion"] = new_location

    if args.apply:
        with DB_PATH.open("w", encoding="utf-8") as file:
            json.dump(catalog, file, ensure_ascii=False, indent=2)
            file.write("\n")

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "dry_run",
        "aliases_defined": len(aliases),
        "aliases_with_rows_found": sum(1 for a in by_alias_key.values() if a["rows_count"] > 0),
        "missing_alias_keys": [
            {
                "source_file": key[0],
                "producer": key[1],
                "item": key[2],
                "ano_raw": key[3],
            }
            for key in missing_alias_keys
        ],
        "updates": updates,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"mode={report['mode']}")
    print(f"aliases_defined={report['aliases_defined']}")
    print(f"aliases_with_rows_found={report['aliases_with_rows_found']}")
    print(f"updates={len(updates)}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
