#!/usr/bin/env python3
"""
Aplica o CSV curado da BODEGA -2 com estratégia segura de POD:
- Usa POD existente apenas quando não há conflito e score >= limiar.
- Cria POD_TEMP único quando há conflito ou baixa confiança.
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
CSV_PATH = ROOT / "data" / "vinhos_para_analise_bodega_minus2_curado_v2.csv"
CATALOG_PATH = ROOT / "data" / "bodega_webapp.json"
REPORT_PATH = ROOT / "reports" / "bodega_minus2_safe_pods_apply_report.json"

CONFIDENCE_MIN_SCORE = 0.65


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def parse_qty(value: str) -> int:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group(0)) if m else 0


def parse_year(value: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", str(value or ""))
    return int(m.group(0)) if m else None


def split_locations(value: str) -> list[str]:
    return [normalize_spaces(v) for v in str(value or "").split(" / ") if normalize_spaces(v)]


def location_sort_key(value: str) -> tuple[int, int, str]:
    cava_match = re.search(r"CAVA\s+(\d+)", value, re.IGNORECASE)
    balda_match = re.search(r"BALDA\s+(\d+)", value, re.IGNORECASE)
    cava_n = int(cava_match.group(1)) if cava_match else 999
    balda_n = int(balda_match.group(1)) if balda_match else 999
    return (cava_n, balda_n, value)


def tipo_struct(tipo_sugerido: str) -> dict[str, str]:
    t = str(tipo_sugerido or "").lower()
    if "blanco" in t:
        return {"codigo": "BL", "nombre": "Blanco"}
    return {"codigo": "TO", "nombre": "Tinto"}


def parse_grapes(text: str) -> list[str]:
    raw = normalize_spaces(text)
    if not raw:
        return []
    raw = re.sub(r"\((.*?)\)", "", raw).strip()
    raw = raw.replace(" ou ", "/").replace(" o ", "/")
    parts = [normalize_spaces(p) for p in re.split(r"[/,;]", raw)]
    out = []
    seen = set()
    for part in parts:
        if not part:
            continue
        key = part.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(part)
    return out


def grapes_struct(grapes: list[str]) -> list[dict[str, Any]]:
    return [{"nome": g, "pct": None, "confianza": "estimada"} for g in grapes]


def detect_format(item: str) -> dict[str, Any]:
    txt = str(item or "").lower()
    if "1.5l" in txt or "magnum" in txt:
        return {"cl": 150, "ml": 1500, "etiqueta": "Magnum (150cl)"}
    return {"cl": 75, "ml": 750, "etiqueta": "Botella (75cl)"}


def build_temp_description(item: str, ano: int | None, tipo_nombre: str) -> str:
    base = normalize_spaces(item)
    if ano:
        yy = str(ano)[-2:]
        return f"[TEMP] {base} {yy}-"
    if tipo_nombre.lower().startswith("bl"):
        return f"[TEMP] {base} BL-"
    return f"[TEMP] {base} TO-"


def next_temp_pod(existing_pods: set[str], counter: int) -> str:
    while True:
        pod = f"POD_TEMP_BM2_{counter:04d}"
        if pod not in existing_pods:
            return pod
        counter += 1


def row_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        normalize_spaces(row.get("source_file", "")).lower(),
        normalize_spaces(row.get("producer", "")).lower(),
        normalize_spaces(row.get("item", "")).lower(),
        normalize_spaces(row.get("ano_raw", "")).lower(),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    rows = list(csv.DictReader(CSV_PATH.open("r", encoding="utf-8")))

    # resolve Summum
    for row in rows:
        if (
            not normalize_spaces(row.get("best_pod", ""))
            and normalize_spaces(row.get("producer", "")).lower() == "summum"
            and normalize_spaces(row.get("item", "")).lower() == "chardonnay"
            and normalize_spaces(row.get("ano_raw", "")) == "2022"
        ):
            row["best_pod"] = "POD017493"

    # detect conflicts: same best_pod tied to multiple different wine keys
    pod_to_keys: dict[str, set[tuple[str, str, str, str]]] = defaultdict(set)
    for row in rows:
        pod = normalize_spaces(row.get("best_pod", ""))
        if not pod:
            continue
        pod_to_keys[pod].add(row_key(row))
    conflicting_pods = {pod for pod, keys in pod_to_keys.items() if len(keys) > 1}

    catalog = json.load(CATALOG_PATH.open("r", encoding="utf-8"))
    existing_pods = {normalize_spaces(w.get("pod", "")) for w in catalog}
    catalog_by_pod = {normalize_spaces(w.get("pod", "")): w for w in catalog}

    temp_counter = 1
    assigned_temp_by_key: dict[tuple[str, str, str, str], str] = {}

    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "rows": [],
            "qty_total": 0,
            "locations": set(),
            "pais": None,
            "region": None,
            "tipo": None,
            "uva": None,
            "producer": None,
            "item": None,
            "ano": None,
            "source_file": None,
            "kind": None,  # existing_pod | temp_pod
            "origin_best_pod": None,
        }
    )

    decision_log = []

    for row in rows:
        k = row_key(row)
        best_pod = normalize_spaces(row.get("best_pod", ""))
        best_score = float(row.get("best_score") or 0)

        use_existing = bool(best_pod) and best_pod not in conflicting_pods and best_score >= CONFIDENCE_MIN_SCORE
        if use_existing:
            final_pod = best_pod
            kind = "existing_pod"
            reason = "score_ok_no_conflict"
        else:
            if k not in assigned_temp_by_key:
                final_pod = next_temp_pod(existing_pods, temp_counter)
                existing_pods.add(final_pod)
                assigned_temp_by_key[k] = final_pod
                temp_counter += 1
            final_pod = assigned_temp_by_key[k]
            kind = "temp_pod"
            if not best_pod:
                reason = "missing_best_pod"
            elif best_pod in conflicting_pods:
                reason = "best_pod_conflict"
            else:
                reason = "low_score"

        grp = grouped[final_pod]
        grp["rows"].append(row)
        grp["qty_total"] += parse_qty(row.get("qty_total", ""))
        grp["locations"].update(split_locations(row.get("locations", "")))
        grp["pais"] = row.get("pais_sugerido") or grp["pais"]
        grp["region"] = row.get("region_sugerida") or grp["region"]
        grp["tipo"] = row.get("tipo_sugerido") or grp["tipo"]
        grp["uva"] = row.get("uva_sugerida") or grp["uva"]
        grp["producer"] = row.get("producer") or grp["producer"]
        grp["item"] = row.get("item") or grp["item"]
        grp["ano"] = parse_year(row.get("ano_raw", "")) or grp["ano"]
        grp["source_file"] = row.get("source_file") or grp["source_file"]
        grp["kind"] = kind
        grp["origin_best_pod"] = best_pod or grp["origin_best_pod"]

        decision_log.append(
            {
                "source_file": row.get("source_file"),
                "producer": row.get("producer"),
                "item": row.get("item"),
                "ano_raw": row.get("ano_raw"),
                "best_pod": best_pod or None,
                "best_score": best_score,
                "final_pod": final_pod,
                "final_kind": kind,
                "reason": reason,
            }
        )

    created_entries = []
    updated_entries = []

    for pod, grp in grouped.items():
        if pod in catalog_by_pod:
            wine = catalog_by_pod[pod]
        else:
            tipo = tipo_struct(grp["tipo"] or "")
            ano = grp["ano"]
            new_wine = {
                "pod": pod,
                "descripcion": build_temp_description(grp["item"] or "", ano, tipo["nombre"]),
                "pais": normalize_spaces(grp["pais"] or ""),
                "region": normalize_spaces(grp["region"] or ""),
                "bodega": normalize_spaces(grp["producer"] or ""),
                "ano": ano,
                "tipo": tipo,
                "formato": detect_format(grp["item"] or ""),
                "uvas": grapes_struct(parse_grapes(grp["uva"] or "")),
                "uvas_confianza": "estimada",
                "registro_temporario": True,
                "origem_temporaria": "bodega_minus2_revisao_manual",
                "bodega_general": {"unidades": None, "localizacion": None},
                "establecimientos": {
                    "spa": {"pvp": None, "unidades": None, "localizacion": None},
                    "tasca_fina": {"pvp": None, "unidades": None, "localizacion": None},
                    "victoria": {"pvp": None, "unidades": None, "localizacion": None},
                    "galeria": {"pvp": None, "unidades": None, "localizacion": None},
                    "bodega": {"pvp": None, "unidades": None, "localizacion": None},
                },
            }
            catalog.append(new_wine)
            catalog_by_pod[pod] = new_wine
            wine = new_wine
            created_entries.append({"pod": pod, "producer": grp["producer"], "item": grp["item"], "ano": grp["ano"]})

        if pod.startswith("POD_TEMP_BM2_"):
            wine["registro_temporario"] = True
            wine["origem_temporaria"] = "bodega_minus2_revisao_manual"

        if not isinstance(wine.get("establecimientos"), dict):
            wine["establecimientos"] = {}
        if not isinstance(wine["establecimientos"].get("bodega"), dict):
            wine["establecimientos"]["bodega"] = {"pvp": None, "unidades": None, "localizacion": None}

        est = wine["establecimientos"]["bodega"]
        old_units = est.get("unidades")
        old_loc = est.get("localizacion")

        est["unidades"] = int(grp["qty_total"])
        est["localizacion"] = " / ".join(sorted(list(grp["locations"]), key=location_sort_key)) if grp["locations"] else None

        # metadata for expanded card
        wine["pais"] = normalize_spaces(grp["pais"] or wine.get("pais", ""))
        wine["region"] = normalize_spaces(grp["region"] or wine.get("region", ""))
        wine["tipo"] = tipo_struct(grp["tipo"] or wine.get("tipo", {}).get("nombre", ""))
        grapes = parse_grapes(grp["uva"] or "")
        if grapes:
            wine["uvas"] = grapes_struct(grapes)
            wine["uvas_confianza"] = "estimada"

        updated_entries.append(
            {
                "pod": pod,
                "kind": grp["kind"],
                "rows_count": len(grp["rows"]),
                "units_before": old_units,
                "units_after": est.get("unidades"),
                "location_before": old_loc,
                "location_after": est.get("localizacion"),
            }
        )

    if args.apply:
        with CATALOG_PATH.open("w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
            f.write("\n")

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "dry_run",
        "rows_in_csv": len(rows),
        "confidence_min_score": CONFIDENCE_MIN_SCORE,
        "conflicting_pods": sorted(list(conflicting_pods)),
        "unique_final_pods": len(grouped),
        "existing_pod_groups": sum(1 for g in grouped.values() if g["kind"] == "existing_pod"),
        "temp_pod_groups": sum(1 for g in grouped.values() if g["kind"] == "temp_pod"),
        "created_entries": created_entries,
        "updated_entries_count": len(updated_entries),
        "decision_log_first_300": decision_log[:300],
        "updated_entries_first_220": updated_entries[:220],
    }

    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"mode={report['mode']}")
    print(f"rows_in_csv={report['rows_in_csv']}")
    print(f"conflicting_pods={len(conflicting_pods)}")
    print(f"unique_final_pods={report['unique_final_pods']}")
    print(f"existing_pod_groups={report['existing_pod_groups']}")
    print(f"temp_pod_groups={report['temp_pod_groups']}")
    print(f"created_entries={len(created_entries)}")
    print(f"updated_entries_count={report['updated_entries_count']}")
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
