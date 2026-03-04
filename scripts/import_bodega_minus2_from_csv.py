#!/usr/bin/env python3
"""
Importa stock/localizacao de BODEGA -2 a partir de data/lista_unica_vinos.csv
ignorando linhas de "tasca fina 18 de febrero.pdf".

Atualiza:
  data/bodega_webapp.json -> establecimientos.bodega.{unidades, localizacion}

Também gera relatório em reports/.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "lista_unica_vinos.csv"
DB_PATH = ROOT / "data" / "bodega_webapp.json"
REPORT_PATH = ROOT / "reports" / "bodega_minus2_import_report.json"
REPORT_TXT_PATH = ROOT / "reports" / "bodega_minus2_import_report.txt"

TASCA_FILE = "tasca fina 18 de febrero.pdf"

PRODUCER_GATE_MIN = 0.42
AUTO_MATCH_SCORE = 0.72
AUTO_MATCH_MARGIN = 0.03
AUTO_MATCH_HARD = 0.80


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = strip_accents(text)
    text = text.replace("·", " ").replace("–", "-").replace("—", "-")
    text = re.sub(r"[’']", "", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(value: Any) -> set[str]:
    stop = {
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "y",
        "i",
        "d",
        "di",
        "da",
        "do",
        "du",
        "des",
        "le",
        "les",
        "the",
        "et",
    }
    tokens = normalize_text(value).split()
    return {t for t in tokens if len(t) > 1 and t not in stop}


def seq_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def parse_year(raw_year: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", str(raw_year or ""))
    if not match:
        return None
    return int(match.group(0))


def parse_qty(raw_qty: str) -> int | None:
    match = re.search(r"\d+", str(raw_qty or ""))
    if not match:
        return None
    return int(match.group(0))


def parse_cava_from_group(group: str) -> str | None:
    match = re.search(r"cava\s*(\d+)", str(group or ""), re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


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
    side_map = {"IZQUIERDA": "IZQ", "DERECHA": "DER", "CENTRO": "CEN"}
    side = side_map.get(side_raw, side_raw)

    if side:
        return f"BALDA {balda} · {side}"
    return f"BALDA {balda}"


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


@dataclass
class CatalogEntry:
    index: int
    pod: str
    ano: int | None
    bodega: str
    descripcion: str
    norm_bodega: str
    norm_desc: str
    tokens_bodega: set[str]
    tokens_desc: set[str]


@dataclass
class MatchResult:
    score: float
    margin: float
    entry: CatalogEntry


def score_candidate(
    producer_norm: str,
    producer_tokens: set[str],
    item_norm: str,
    item_tokens: set[str],
    year: int | None,
    candidate: CatalogEntry,
) -> float:
    producer_score = max(
        seq_ratio(producer_norm, candidate.norm_bodega),
        jaccard(producer_tokens, candidate.tokens_bodega),
    )
    if producer_score < PRODUCER_GATE_MIN:
        return -1.0

    if year is not None and candidate.ano is not None and abs(candidate.ano - year) > 2:
        return -1.0

    item_score = max(
        seq_ratio(item_norm, candidate.norm_desc),
        jaccard(item_tokens, candidate.tokens_desc),
    )

    score = 0.42 * producer_score + 0.45 * item_score

    if year is not None and candidate.ano is not None:
        if candidate.ano == year:
            score += 0.10
        elif abs(candidate.ano - year) == 1:
            score += 0.03
        else:
            score -= 0.04

    if item_tokens and item_tokens.issubset(candidate.tokens_desc):
        score += 0.05
    if producer_tokens and producer_tokens.issubset(candidate.tokens_bodega):
        score += 0.05

    return score


def pick_best_match(
    row: dict[str, str],
    candidates: list[CatalogEntry],
) -> MatchResult | None:
    producer = row.get("producer", "")
    item = row.get("item", "")
    year = parse_year(row.get("ano", ""))

    producer_norm = normalize_text(producer)
    producer_tokens = tokenize(producer)
    item_norm = normalize_text(item)
    item_tokens = tokenize(item)

    scored: list[tuple[float, CatalogEntry]] = []
    for entry in candidates:
        score = score_candidate(
            producer_norm, producer_tokens, item_norm, item_tokens, year, entry
        )
        if score >= 0:
            scored.append((score, entry))

    if not scored:
        return None

    scored.sort(key=lambda pair: pair[0], reverse=True)
    best_score, best_entry = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    margin = best_score - second_score

    auto = (best_score >= AUTO_MATCH_SCORE and margin >= AUTO_MATCH_MARGIN) or (
        best_score >= AUTO_MATCH_HARD
    )
    if not auto:
        return None

    return MatchResult(score=best_score, margin=margin, entry=best_entry)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica atualizacoes no data/bodega_webapp.json",
    )
    args = parser.parse_args()

    with CSV_PATH.open("r", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    rows = [row for row in rows if (row.get("source_file") or "").strip() != TASCA_FILE]

    with DB_PATH.open("r", encoding="utf-8") as file:
        catalog = json.load(file)

    entries: list[CatalogEntry] = []
    for index, wine in enumerate(catalog):
        entries.append(
            CatalogEntry(
                index=index,
                pod=str(wine.get("pod", "")).strip(),
                ano=wine.get("ano") if isinstance(wine.get("ano"), int) else None,
                bodega=str(wine.get("bodega", "")).strip(),
                descripcion=str(wine.get("descripcion", "")).strip(),
                norm_bodega=normalize_text(wine.get("bodega", "")),
                norm_desc=normalize_text(wine.get("descripcion", "")),
                tokens_bodega=tokenize(wine.get("bodega", "")),
                tokens_desc=tokenize(wine.get("descripcion", "")),
            )
        )

    pod_aggregate: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"rows": [], "qty_total": 0, "locations": set(), "scores": []}
    )
    unmatched_rows: list[dict[str, Any]] = []

    for row in rows:
        match = pick_best_match(row, entries)
        if not match:
            unmatched_rows.append(
                {
                    "source_file": row.get("source_file"),
                    "producer": row.get("producer"),
                    "item": row.get("item"),
                    "ano": row.get("ano"),
                    "qty": row.get("qty"),
                    "posicion": row.get("posicion"),
                    "location_group": row.get("location_group"),
                }
            )
            continue

        qty = parse_qty(row.get("qty", "")) or 0
        location = build_location(row.get("location_group", ""), row.get("posicion", ""))
        pod = match.entry.pod

        payload = pod_aggregate[pod]
        payload["rows"].append(row)
        payload["qty_total"] += qty
        if location:
            payload["locations"].add(location)
        payload["scores"].append(match.score)

    applied_preview: list[dict[str, Any]] = []
    for pod, payload in pod_aggregate.items():
        locations = sorted(payload["locations"], key=location_sort_key)
        localizacion = " / ".join(locations) if locations else None
        avg_score = (
            round(sum(payload["scores"]) / len(payload["scores"]), 4)
            if payload["scores"]
            else None
        )

        applied_preview.append(
            {
                "pod": pod,
                "rows_count": len(payload["rows"]),
                "qty_total": payload["qty_total"],
                "localizacion": localizacion,
                "avg_score": avg_score,
            }
        )

    applied_preview.sort(key=lambda row: row["pod"])

    updates_applied = 0
    if args.apply:
        by_pod = {str(w.get("pod", "")).strip(): w for w in catalog}
        for row in applied_preview:
            wine = by_pod.get(row["pod"])
            if not wine:
                continue
            if not isinstance(wine.get("establecimientos"), dict):
                wine["establecimientos"] = {}
            if not isinstance(wine["establecimientos"].get("bodega"), dict):
                wine["establecimientos"]["bodega"] = {
                    "pvp": None,
                    "unidades": None,
                    "localizacion": None,
                }

            wine["establecimientos"]["bodega"]["unidades"] = row["qty_total"]
            wine["establecimientos"]["bodega"]["localizacion"] = row["localizacion"]
            updates_applied += 1

        with DB_PATH.open("w", encoding="utf-8") as file:
            json.dump(catalog, file, ensure_ascii=False, indent=2)
            file.write("\n")

    timestamp = datetime.now(timezone.utc).isoformat()
    report = {
        "timestamp_utc": timestamp,
        "mode": "apply" if args.apply else "dry_run",
        "csv_rows_total_non_tasca": len(rows),
        "csv_source_files_non_tasca": sorted(
            list({(row.get("source_file") or "").strip() for row in rows})
        ),
        "matched_rows": sum(item["rows_count"] for item in applied_preview),
        "matched_unique_pods": len(applied_preview),
        "unmatched_rows": len(unmatched_rows),
        "updates_applied": updates_applied,
        "top_unmatched_producers": Counter(
            (row.get("producer") or "").strip() for row in unmatched_rows
        ).most_common(25),
        "preview_first_100": applied_preview[:100],
        "unmatched_first_200": unmatched_rows[:200],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")

    summary_lines = [
        "BODEGA -2 import summary",
        f"- mode: {report['mode']}",
        f"- rows non tasca: {report['csv_rows_total_non_tasca']}",
        f"- matched rows: {report['matched_rows']}",
        f"- matched unique pods: {report['matched_unique_pods']}",
        f"- unmatched rows: {report['unmatched_rows']}",
        f"- updates applied: {report['updates_applied']}",
        "",
        f"Report JSON: {REPORT_PATH}",
    ]
    with REPORT_TXT_PATH.open("w", encoding="utf-8") as file:
        file.write("\n".join(summary_lines) + "\n")

    print("\n".join(summary_lines))


if __name__ == "__main__":
    main()
