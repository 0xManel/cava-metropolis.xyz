#!/usr/bin/env python3
"""
Aplica CSV curado da BODEGA -2 no catálogo.

Atualiza por POD:
- establecimientos.bodega.unidades
- establecimientos.bodega.localizacion
- pais, region, tipo, uvas (metadados para card expandido)
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
CURATED_CSV = ROOT / "data" / "vinhos_para_analise_bodega_minus2_curado_v2.csv"
CATALOG_JSON = ROOT / "data" / "bodega_webapp.json"
REPORT_JSON = ROOT / "reports" / "bodega_minus2_curated_apply_report.json"


def parse_qty(value: str) -> int:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group(0)) if m else 0


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def location_sort_key(value: str) -> tuple[int, int, str]:
    cava_match = re.search(r"CAVA\s+(\d+)", value, re.IGNORECASE)
    balda_match = re.search(r"BALDA\s+(\d+)", value, re.IGNORECASE)
    cava_n = int(cava_match.group(1)) if cava_match else 999
    balda_n = int(balda_match.group(1)) if balda_match else 999
    return (cava_n, balda_n, value)


def split_locations(value: str) -> list[str]:
    if not value:
        return []
    return [normalize_spaces(part) for part in str(value).split(" / ") if normalize_spaces(part)]


def parse_grapes(uva_sugerida: str) -> list[str]:
    text = normalize_spaces(uva_sugerida)
    if not text:
        return []
    text = re.sub(r"\((.*?)\)", "", text).strip()
    text = text.replace(" ou ", "/").replace(" o ", "/")
    parts = re.split(r"[/,;]", text)
    grapes = []
    for part in parts:
        g = normalize_spaces(part)
        if not g:
            continue
        grapes.append(g)
    # dedupe preserving order
    seen = set()
    out = []
    for g in grapes:
        k = g.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(g)
    return out


def tipo_to_struct(tipo_sugerido: str, old_tipo: Any) -> dict[str, str]:
    t = str(tipo_sugerido or "").strip().lower()
    if "blanco" in t:
        return {"codigo": "BL", "nombre": "Blanco"}
    if "tinto" in t:
        return {"codigo": "TO", "nombre": "Tinto"}
    if isinstance(old_tipo, dict) and old_tipo.get("codigo") and old_tipo.get("nombre"):
        return {"codigo": str(old_tipo["codigo"]), "nombre": str(old_tipo["nombre"])}
    return {"codigo": "TO", "nombre": "Tinto"}


def grapes_to_struct(grapes: list[str]) -> list[dict[str, Any]]:
    return [{"nome": g, "pct": None, "confianza": "estimada"} for g in grapes]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Grava alterações no catálogo")
    args = parser.parse_args()

    rows = list(csv.DictReader(CURATED_CSV.open("r", encoding="utf-8")))

    # Resolve o último caso sem POD (Summum 2022).
    for row in rows:
        if (
            not str(row.get("best_pod") or "").strip()
            and normalize_spaces(row.get("producer", "")).lower() == "summum"
            and normalize_spaces(row.get("item", "")).lower() == "chardonnay"
            and normalize_spaces(row.get("ano_raw", "")) == "2022"
        ):
            row["best_pod"] = "POD017493"

    by_pod: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "qty_total": 0,
            "locations": set(),
            "rows": [],
            "pais": None,
            "region": None,
            "tipo": None,
            "uva": None,
        }
    )
    rows_without_pod = []

    for row in rows:
        pod = normalize_spaces(row.get("best_pod", ""))
        if not pod:
            rows_without_pod.append(
                {
                    "source_file": row.get("source_file"),
                    "producer": row.get("producer"),
                    "item": row.get("item"),
                    "ano_raw": row.get("ano_raw"),
                }
            )
            continue

        grp = by_pod[pod]
        grp["qty_total"] += parse_qty(row.get("qty_total", ""))
        for loc in split_locations(row.get("locations", "")):
            grp["locations"].add(loc)
        grp["rows"].append(row)
        grp["pais"] = row.get("pais_sugerido") or grp["pais"]
        grp["region"] = row.get("region_sugerida") or grp["region"]
        grp["tipo"] = row.get("tipo_sugerido") or grp["tipo"]
        grp["uva"] = row.get("uva_sugerida") or grp["uva"]

    catalog = json.load(CATALOG_JSON.open("r", encoding="utf-8"))
    catalog_by_pod = {normalize_spaces(w.get("pod", "")): w for w in catalog}

    updated = []
    missing_pods_in_catalog = []
    conflicts = []

    for pod, grp in by_pod.items():
        wine = catalog_by_pod.get(pod)
        if not wine:
            missing_pods_in_catalog.append(pod)
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
        old_loc = est.get("localizacion")
        old_pais = wine.get("pais")
        old_region = wine.get("region")
        old_tipo = wine.get("tipo")
        old_uvas = wine.get("uvas")

        new_units = int(grp["qty_total"])
        new_locations_list = sorted(list(grp["locations"]), key=location_sort_key)
        new_loc = " / ".join(new_locations_list) if new_locations_list else None
        new_pais = normalize_spaces(grp["pais"] or old_pais)
        new_region = normalize_spaces(grp["region"] or old_region)
        new_tipo = tipo_to_struct(grp["tipo"], old_tipo)
        new_grapes = parse_grapes(grp["uva"] or "")
        if not new_grapes and isinstance(old_uvas, list):
            # mantém se não veio curadoria de uva
            pass
        else:
            wine["uvas"] = grapes_to_struct(new_grapes)
            wine["uvas_confianza"] = "estimada"

        est["unidades"] = new_units
        est["localizacion"] = new_loc
        wine["pais"] = new_pais
        wine["region"] = new_region
        wine["tipo"] = new_tipo

        # Detecta conflitos de metadado dentro do mesmo POD.
        tipo_vals = sorted({normalize_spaces(r.get("tipo_sugerido", "")) for r in grp["rows"] if normalize_spaces(r.get("tipo_sugerido", ""))})
        uva_vals = sorted({normalize_spaces(r.get("uva_sugerida", "")) for r in grp["rows"] if normalize_spaces(r.get("uva_sugerida", ""))})
        if len(tipo_vals) > 1 or len(uva_vals) > 1:
            conflicts.append(
                {
                    "pod": pod,
                    "tipo_values": tipo_vals,
                    "uva_values": uva_vals,
                }
            )

        updated.append(
            {
                "pod": pod,
                "descripcion": wine.get("descripcion"),
                "rows_count": len(grp["rows"]),
                "units_before": old_units,
                "units_after": new_units,
                "location_before": old_loc,
                "location_after": new_loc,
                "pais_before": old_pais,
                "pais_after": new_pais,
                "region_before": old_region,
                "region_after": new_region,
                "tipo_before": old_tipo,
                "tipo_after": new_tipo,
                "uvas_before": old_uvas,
                "uvas_after": wine.get("uvas"),
            }
        )

    if args.apply:
        with CATALOG_JSON.open("w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
            f.write("\n")

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "dry_run",
        "rows_in_csv": len(rows),
        "rows_without_pod": rows_without_pod,
        "unique_pods_from_csv": len(by_pod),
        "updated_pods": len(updated),
        "missing_pods_in_catalog": missing_pods_in_catalog,
        "metadata_conflicts": conflicts,
        "sample_updates_first_120": updated[:120],
    }

    with REPORT_JSON.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"mode={report['mode']}")
    print(f"rows_in_csv={report['rows_in_csv']}")
    print(f"rows_without_pod={len(rows_without_pod)}")
    print(f"unique_pods_from_csv={report['unique_pods_from_csv']}")
    print(f"updated_pods={report['updated_pods']}")
    print(f"missing_pods_in_catalog={len(missing_pods_in_catalog)}")
    print(f"metadata_conflicts={len(conflicts)}")
    print(f"report={REPORT_JSON}")


if __name__ == "__main__":
    main()
