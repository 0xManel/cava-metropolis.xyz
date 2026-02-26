#!/usr/bin/env python3
"""
Importa localizações da planta 1 (Victoria) a partir de
reports/ubicacion_vinos_planta1_unico.csv para:
  data/bodega_webapp.json -> establecimientos.victoria.{localizacion, unidades}

Modo seguro:
- aplica somente matches de alta confiança;
- ignora linhas ambíguas de OCR;
- preserva dados já existentes (faz merge de localizações).
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
CSV_PATH = ROOT / "reports" / "ubicacion_vinos_planta1_unico.csv"
DB_PATH = ROOT / "data" / "bodega_webapp.json"
REPORT_JSON_PATH = ROOT / "reports" / "victoria_import_report.json"
REPORT_UNMATCHED_CSV_PATH = ROOT / "reports" / "victoria_import_unmatched.csv"

SCORE_MIN = 0.75
MARGIN_MIN = 0.05
HARD_MIN = 0.88
RELAXED_SCORE_MIN = 0.72
RELAXED_MARGIN_MIN = 0.03
RELAXED_COVERAGE_MIN = 0.70
RELAXED_SCORE_ALT = 0.705
RELAXED_MARGIN_ALT = 0.08
RELAXED_COVERAGE_ALT = 0.75


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_spaces(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


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
        "grand",
        "cru",
        "classe",
        "class",
        "reserva",
        "vintage",
        "domaine",
        "dominio",
        "chateau",
    }
    return {t for t in normalize_text(value).split() if len(t) > 1 and t not in stop}


def seq_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def parse_year(text: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", str(text or ""))
    return int(match.group(0)) if match else None


def parse_qty(value: str) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else None


def parse_x_qty(value: str) -> int | None:
    match = re.search(r"\bX\s*(\d{1,3})\b", str(value or "").upper())
    return int(match.group(1)) if match else None


def parse_victoria_cava(raw_cava: str) -> str | None:
    text = normalize_spaces(raw_cava).upper()
    if not text:
        return None
    if "EXHIBIC" in text:
        return "X"
    match = re.search(r"\bCAVA\s*([A-Z0-9]{1,3})\b", text)
    if match:
        return match.group(1)
    return None


def parse_victoria_balda(raw_balda: str) -> str | None:
    text = normalize_spaces(raw_balda).upper().replace(":", "")
    match = re.search(r"\bBALDA\s*(\d{1,2})\b", text)
    if match:
        return str(int(match.group(1)))
    return None


def parse_victoria_door(raw: str) -> str | None:
    text = normalize_spaces(raw).upper()
    if not text:
        return None
    if "IZQ" in text or "IZQUI" in text:
        return "IZQ"
    if "DER" in text or "DERE" in text:
        return "DER"
    if "CEN" in text or "CENT" in text:
        return "CEN"
    return None


def parse_victoria_line(raw: str) -> str | None:
    text = normalize_spaces(raw).upper().replace("Í", "I")
    if not text:
        return None
    ord_map = {"PRIMERA": 1, "SEGUNDA": 2, "TERCERA": 3, "CUARTA": 4, "QUINTA": 5}
    for k, v in ord_map.items():
        if k in text:
            return f"L{v}"
    line_match = re.search(r"\bLINEA\s*(\d{1,2})\b", text)
    if line_match:
        return f"L{line_match.group(1)}"
    num_match = re.search(r"\b(\d{1,2})\b", text)
    if num_match:
        return f"L{num_match.group(1)}"
    return None


def build_victoria_location(row: dict[str, str]) -> str | None:
    cava = parse_victoria_cava(row.get("cava", ""))
    balda = parse_victoria_balda(row.get("balda", ""))
    if not cava or not balda:
        return None

    door = parse_victoria_door(" ".join([row.get("area", ""), row.get("cava", ""), row.get("balda", "")]))
    line = parse_victoria_line(" ".join([row.get("sublinea", ""), row.get("linea", "")]))

    parts = [cava, balda]
    if door:
        parts.append(door)
    if line:
        parts.append(line)
    return "·".join(parts)


def clean_wine_text(raw_text: str) -> str:
    text = normalize_spaces(raw_text)
    text = re.sub(r"^\s*BALDA\s*\d+\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+x\s*\d+\s*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" -,:;")
    return text


def extract_wine_text(row: dict[str, str]) -> str:
    full = normalize_spaces(row.get("item_vino_sin_cantidad_completo", ""))
    base = normalize_spaces(row.get("vino_sin_cantidad", ""))
    fallback = normalize_spaces(row.get("entrada_sin_checkbox", ""))
    raw = full or base or fallback
    return clean_wine_text(raw)


def looks_ambiguous(row: dict[str, str], wine_text: str) -> bool:
    if not wine_text or len(wine_text) < 6:
        return True
    if re.fullmatch(r"BALDA\s*\d+", wine_text, flags=re.IGNORECASE):
        return True
    total_parts = parse_qty(row.get("item_total_parts", "")) or 1
    if total_parts <= 1:
        return False
    years = {m.group(0) for m in re.finditer(r"(19|20)\d{2}", wine_text)}
    return len(years) > 1


def get_row_qty(row: dict[str, str]) -> int:
    direct = parse_qty(row.get("cantidad", ""))
    if direct is not None and direct > 0:
        return direct

    raw = parse_x_qty(row.get("cantidad_raw", ""))
    if raw is not None and raw > 0:
        return raw

    from_entry = parse_x_qty(row.get("entrada_sin_checkbox", ""))
    if from_entry is not None and from_entry > 0:
        return from_entry

    from_item = parse_x_qty(row.get("item_entrada_completa", ""))
    if from_item is not None and from_item > 0:
        return from_item

    return 1


def location_sort_key(value: str) -> tuple[int, int, int, int, str]:
    parts = [p.strip().upper() for p in str(value or "").split("·") if p.strip()]
    cava = parts[0] if parts else ""
    balda = parse_qty(parts[1] if len(parts) > 1 else "") or 999
    door = parts[2] if len(parts) > 2 else ""
    line = parse_qty(parts[3] if len(parts) > 3 else "") or 999
    cava_order = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "X": 7}.get(cava, 99)
    door_order = {"IZQ": 1, "CEN": 2, "DER": 3}.get(door, 9)
    return (cava_order, balda, door_order, line, value)


@dataclass
class CatalogEntry:
    index: int
    pod: str
    ano: int | None
    descripcion: str
    bodega: str
    norm_desc: str
    norm_search: str
    tokens_desc: set[str]
    tokens_search: set[str]


@dataclass
class SourceRow:
    orden: str
    item_id: str
    wine_text: str
    year: int | None
    qty: int
    location: str
    norm_text: str
    tokens: set[str]
    source: dict[str, str]


@dataclass
class MatchResult:
    score: float
    margin: float
    entry: CatalogEntry
    second_score: float


def score_candidate(source: SourceRow, candidate: CatalogEntry) -> float:
    seq_desc = seq_ratio(source.norm_text, candidate.norm_desc)
    seq_search = seq_ratio(source.norm_text, candidate.norm_search)
    jac_desc = jaccard(source.tokens, candidate.tokens_desc)
    jac_search = jaccard(source.tokens, candidate.tokens_search)

    seq_best = max(seq_desc, seq_search)
    jac_best = max(jac_desc, jac_search)

    if seq_best < 0.45 and jac_best < 0.08:
        return -1.0

    score = 0.62 * seq_best + 0.30 * jac_best
    if source.year is not None and candidate.ano is not None:
        delta = abs(source.year - candidate.ano)
        if delta == 0:
            score += 0.12
        elif delta == 1:
            score += 0.04
        elif delta == 2:
            score -= 0.05
        else:
            return -1.0
    elif source.year is not None and candidate.ano is None:
        score -= 0.02

    source_tokens = source.tokens
    if source_tokens and source_tokens.issubset(candidate.tokens_search):
        score += 0.05
    if len(source_tokens & candidate.tokens_search) >= 3:
        score += 0.02
    return score


def pick_best_match(source: SourceRow, candidates: list[CatalogEntry]) -> MatchResult | None:
    scored: list[tuple[float, CatalogEntry]] = []
    for candidate in candidates:
        score = score_candidate(source, candidate)
        if score >= 0:
            scored.append((score, candidate))
    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_entry = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    margin = best_score - second_score

    auto = (best_score >= SCORE_MIN and margin >= MARGIN_MIN) or (best_score >= HARD_MIN)
    if not auto:
        return None
    return MatchResult(score=best_score, margin=margin, entry=best_entry, second_score=second_score)


def pick_best_candidate_any(source: SourceRow, candidates: list[CatalogEntry]) -> MatchResult | None:
    scored: list[tuple[float, CatalogEntry]] = []
    for candidate in candidates:
        score = score_candidate(source, candidate)
        if score >= 0:
            scored.append((score, candidate))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_entry = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    return MatchResult(
        score=best_score,
        margin=best_score - second_score,
        entry=best_entry,
        second_score=second_score,
    )


def candidate_pool_for_year(source_year: int | None, candidates_by_year: dict[int, list[CatalogEntry]], fallback: list[CatalogEntry]) -> list[CatalogEntry]:
    if source_year is None:
        return fallback
    pool: list[CatalogEntry] = []
    for y in (source_year - 1, source_year, source_year + 1):
        pool.extend(candidates_by_year.get(y, []))
    if not pool:
        return fallback
    return pool


def relaxed_match_is_safe(source: SourceRow, best_any: MatchResult | None) -> bool:
    if best_any is None:
        return False
    coverage_base = source.tokens
    coverage_target = best_any.entry.tokens_search
    coverage = (len(coverage_base & coverage_target) / len(coverage_base)) if coverage_base else 0.0

    primary_ok = (
        best_any.score >= RELAXED_SCORE_MIN
        and best_any.margin >= RELAXED_MARGIN_MIN
        and coverage >= RELAXED_COVERAGE_MIN
    )
    alternate_ok = (
        best_any.score >= RELAXED_SCORE_ALT
        and best_any.margin >= RELAXED_MARGIN_ALT
        and coverage >= RELAXED_COVERAGE_ALT
    )

    return primary_ok or alternate_ok


def split_locations(value: Any) -> set[str]:
    return {normalize_spaces(x) for x in str(value or "").split(" / ") if normalize_spaces(x)}


def ensure_establecimientos(wine: dict[str, Any]) -> None:
    if not isinstance(wine.get("establecimientos"), dict):
        wine["establecimientos"] = {}
    for key in ("spa", "tasca_fina", "victoria", "galeria", "bodega"):
        if not isinstance(wine["establecimientos"].get(key), dict):
            wine["establecimientos"][key] = {"pvp": None, "unidades": None, "localizacion": None}
        else:
            wine["establecimientos"][key].setdefault("pvp", None)
            wine["establecimientos"][key].setdefault("unidades", None)
            wine["establecimientos"][key].setdefault("localizacion", None)


def coerce_positive_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    parsed = parse_qty(str(value))
    if parsed is None or parsed <= 0:
        return None
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Grava alterações no catálogo")
    args = parser.parse_args()

    source_csv_rows = list(csv.DictReader(CSV_PATH.open("r", encoding="utf-8")))
    catalog = json.load(DB_PATH.open("r", encoding="utf-8"))

    candidates: list[CatalogEntry] = []
    candidates_by_year: dict[int, list[CatalogEntry]] = defaultdict(list)
    for i, wine in enumerate(catalog):
        descripcion = normalize_spaces(wine.get("descripcion", ""))
        bodega = normalize_spaces(wine.get("bodega", ""))
        ano = wine.get("ano")
        try:
            ano_int = int(ano) if ano is not None else None
        except Exception:
            ano_int = None
        search = normalize_spaces(f"{bodega} {descripcion} {ano_int or ''}")
        candidate = CatalogEntry(
            index=i,
            pod=normalize_spaces(wine.get("pod", "")),
            ano=ano_int,
            descripcion=descripcion,
            bodega=bodega,
            norm_desc=normalize_text(descripcion),
            norm_search=normalize_text(search),
            tokens_desc=tokenize(descripcion),
            tokens_search=tokenize(search),
        )
        candidates.append(candidate)
        if ano_int is not None:
            candidates_by_year[ano_int].append(candidate)

    usable_rows: list[SourceRow] = []
    skipped_rows: list[dict[str, Any]] = []

    for row in source_csv_rows:
        if normalize_spaces(row.get("tipo", "")).upper() != "ITEM":
            continue
        wine_text = extract_wine_text(row)
        if not wine_text:
            skipped_rows.append({"orden": row.get("orden"), "reason": "empty_wine_text", "raw": row})
            continue
        if looks_ambiguous(row, wine_text):
            skipped_rows.append({"orden": row.get("orden"), "reason": "ambiguous_or_noise", "wine_text": wine_text, "raw": row})
            continue
        location = build_victoria_location(row)
        if not location:
            skipped_rows.append({"orden": row.get("orden"), "reason": "missing_location", "wine_text": wine_text, "raw": row})
            continue

        usable_rows.append(
            SourceRow(
                orden=normalize_spaces(row.get("orden", "")),
                item_id=normalize_spaces(row.get("item_id", "")),
                wine_text=wine_text,
                year=parse_year(wine_text),
                qty=get_row_qty(row),
                location=location,
                norm_text=normalize_text(wine_text),
                tokens=tokenize(wine_text),
                source=row,
            )
        )

    grouped_by_pod: dict[str, dict[str, Any]] = defaultdict(lambda: {"qty_total": 0, "locations": set(), "rows": []})
    unmatched_rows: list[dict[str, Any]] = []
    decision_log: list[dict[str, Any]] = []

    for src in usable_rows:
        pool = candidate_pool_for_year(src.year, candidates_by_year, candidates)
        match = pick_best_match(src, pool)
        if not match:
            best_any = pick_best_candidate_any(src, pool)
            if relaxed_match_is_safe(src, best_any):
                match = best_any
        if not match:
            unmatched_rows.append(
                {
                    "orden": src.orden,
                    "item_id": src.item_id,
                    "wine_text": src.wine_text,
                    "year": src.year,
                    "qty": src.qty,
                    "location": src.location,
                    "best_score": round(best_any.score, 4) if best_any else None,
                    "best_margin": round(best_any.margin, 4) if best_any else None,
                    "best_pod": best_any.entry.pod if best_any else None,
                    "best_desc": best_any.entry.descripcion if best_any else None,
                    "best_bodega": best_any.entry.bodega if best_any else None,
                    "best_year": best_any.entry.ano if best_any else None,
                }
            )
            decision_log.append(
                {
                    "orden": src.orden,
                    "item_id": src.item_id,
                    "wine_text": src.wine_text,
                    "matched": False,
                    "reason": "low_confidence_or_ambiguous",
                    "best_score": round(best_any.score, 4) if best_any else None,
                    "best_margin": round(best_any.margin, 4) if best_any else None,
                    "best_pod": best_any.entry.pod if best_any else None,
                }
            )
            continue

        pod = match.entry.pod
        grp = grouped_by_pod[pod]
        grp["qty_total"] += src.qty
        grp["locations"].add(src.location)
        grp["rows"].append(
            {
                "orden": src.orden,
                "item_id": src.item_id,
                "wine_text": src.wine_text,
                "year": src.year,
                "qty": src.qty,
                "location": src.location,
                "score": round(match.score, 4),
            }
        )
        decision_log.append(
            {
                "orden": src.orden,
                "item_id": src.item_id,
                "wine_text": src.wine_text,
                "matched": True,
                "pod": pod,
                "score": round(match.score, 4),
                "margin": round(match.margin, 4),
                "second_score": round(match.second_score, 4),
            }
        )

    catalog_by_pod = {normalize_spaces(w.get("pod", "")): w for w in catalog}
    updated_entries = []
    for pod, payload in grouped_by_pod.items():
        wine = catalog_by_pod.get(pod)
        if not wine:
            continue
        ensure_establecimientos(wine)
        est = wine["establecimientos"]["victoria"]

        old_loc_set = split_locations(est.get("localizacion"))
        new_loc_set = set(payload["locations"])
        merged_loc_set = old_loc_set | new_loc_set
        merged_loc = " / ".join(sorted(merged_loc_set, key=location_sort_key)) if merged_loc_set else None

        old_units = coerce_positive_int(est.get("unidades"))
        if old_units is None:
            new_units = payload["qty_total"] if payload["qty_total"] > 0 else None
            units_mode = "set_from_csv"
        else:
            new_units = old_units
            units_mode = "kept_existing"

        est["localizacion"] = merged_loc
        est["unidades"] = new_units

        updated_entries.append(
            {
                "pod": pod,
                "descripcion": wine.get("descripcion"),
                "rows_count": len(payload["rows"]),
                "qty_csv_total": payload["qty_total"],
                "units_mode": units_mode,
                "units_before": old_units,
                "units_after": new_units,
                "location_before_count": len(old_loc_set),
                "location_after_count": len(merged_loc_set),
                "location_after": merged_loc,
            }
        )

    if args.apply:
        DB_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    unmatched_headers = [
        "orden",
        "item_id",
        "wine_text",
        "year",
        "qty",
        "location",
        "best_score",
        "best_margin",
        "best_pod",
        "best_desc",
        "best_bodega",
        "best_year",
    ]
    with REPORT_UNMATCHED_CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=unmatched_headers)
        writer.writeheader()
        for row in unmatched_rows:
            writer.writerow({k: row.get(k) for k in unmatched_headers})

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "dry_run",
        "csv_total_rows": len(source_csv_rows),
        "csv_item_rows": sum(1 for r in source_csv_rows if normalize_spaces(r.get("tipo", "")).upper() == "ITEM"),
        "usable_rows_after_filters": len(usable_rows),
        "skipped_rows": len(skipped_rows),
        "skip_reasons": dict(Counter(row["reason"] for row in skipped_rows)),
        "matched_rows": sum(len(v["rows"]) for v in grouped_by_pod.values()),
        "matched_unique_pods": len(grouped_by_pod),
        "unmatched_rows": len(unmatched_rows),
        "updated_entries_count": len(updated_entries),
        "updated_entries": sorted(updated_entries, key=lambda x: x["rows_count"], reverse=True)[:300],
        "unmatched_first_300": unmatched_rows[:300],
        "decision_log_first_600": decision_log[:600],
        "paths": {
            "csv_source": str(CSV_PATH),
            "db": str(DB_PATH),
            "report_json": str(REPORT_JSON_PATH),
            "report_unmatched_csv": str(REPORT_UNMATCHED_CSV_PATH),
        },
    }
    REPORT_JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"mode={report['mode']}")
    print(f"csv_item_rows={report['csv_item_rows']}")
    print(f"usable_rows_after_filters={report['usable_rows_after_filters']}")
    print(f"matched_rows={report['matched_rows']}")
    print(f"matched_unique_pods={report['matched_unique_pods']}")
    print(f"unmatched_rows={report['unmatched_rows']}")
    print(f"updated_entries_count={report['updated_entries_count']}")
    print(f"report_json={REPORT_JSON_PATH}")
    print(f"report_unmatched_csv={REPORT_UNMATCHED_CSV_PATH}")


if __name__ == "__main__":
    main()
