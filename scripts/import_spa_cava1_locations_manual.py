#!/usr/bin/env python3
"""
Importa localizaciones manuales de SPA (-1) Cava 1 para:
  data/bodega_webapp.json -> establecimientos.spa.localizacion

Modo seguro:
- cruza por similitud nombre/bodega/añada;
- aplica solo matches de alta confianza;
- no toca pvp;
- no toca unidades (solo localizacion);
- preserva localizaciones existentes (merge sin duplicados).
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
DB_PATH = ROOT / "data" / "bodega_webapp.json"
SOURCE_CSV_PATH = ROOT / "reports" / "spa_cava1_manual_source.csv"
REPORT_JSON_PATH = ROOT / "reports" / "spa_cava1_import_report.json"
REPORT_UNMATCHED_CSV_PATH = ROOT / "reports" / "spa_cava1_import_unmatched.csv"

SCORE_MIN = 0.78
MARGIN_MIN = 0.06
HARD_MIN = 0.90


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
        "and",
        "grand",
        "cru",
        "cuvee",
        "champagne",
        "brut",
        "extra",
        "nature",
        "premier",
        "reserve",
        "reserva",
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


def location_sort_key(value: str) -> tuple[int, int, int, str]:
    parts = [p.strip().upper() for p in str(value or "").split("·") if p.strip()]
    cava = int(parts[0]) if parts and parts[0].isdigit() else 999
    if len(parts) > 1 and parts[1] == "BASE":
        return (cava, 999, 999, value)
    balda = ord(parts[1][0]) - 64 if len(parts) > 1 and parts[1] else 999
    pos = {"A": 1, "D": 2}.get(parts[2], 9) if len(parts) > 2 else 9
    return (cava, balda, pos, value)


@dataclass
class SourceRow:
    wine_text: str
    year: int | None
    qty: int
    location: str
    norm_text: str
    tokens: set[str]


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
class MatchResult:
    score: float
    margin: float
    second_score: float
    entry: CatalogEntry


MANUAL_ROWS = [
    ("La Baixada Alvaro Palacios", 2022, 1, "1·A·D"),
    ("Salanques Mas Doix", 2022, 1, "1·A·D"),
    ("Les Terrasses Velles Vinyes Alvaro Palacios", 2022, 1, "1·A·D"),
    ("Casa Castillo", 2023, 1, "1·B·D"),
    ("La Tendida Casa Castillo", 2023, 1, "1·B·D"),
    ("Pintia", 2017, 1, "1·D·D"),
    ("Pintia", 2020, 1, "1·D·D"),
    ("La Rioja Alta Gran Reserva 904", 2016, 1, "1·D·D"),
    ("Hispania Dominio del Aguila", 2021, 1, "1·E·D"),
    ("Picarana Dominio del Aguila", 2022, 1, "1·E·D"),
    ("Dominio del Aguila Reserva", 2020, 1, "1·E·A"),
    ("Dominio del Aguila Camino del Soto", 2022, 1, "1·E·A"),
    ("Mauro VS", 2022, 1, "1·E·A"),
    ("Suzanne Bodegas Bhilar", 2020, 1, "1·F·D"),
    ("La Emperatriz Finca La Emperatriz", 2019, 1, "1·F·D"),
    ("La Rioja Alta Gran Reserva 904", 2016, 1, "1·F·D"),
    ("Bideona", 2020, 1, "1·F·D"),
    ("Macan Clasico", 2021, 1, "1·F·A"),
    ("Macan", 2020, 1, "1·F·A"),
    ("La Emperatriz Finca La Emperatriz", 2020, 1, "1·F·A"),
    ("Bideona", 2020, 1, "1·F·A"),
    ("Suzanne Bodegas Bhilar", 2020, 1, "1·F·A"),
    ("Corimbo I Reserva", 2018, 1, "1·G·D"),
    ("Corimbo I Reserva", 2022, 1, "1·G·D"),
    ("Bosque de Matasnos Reserva", 2022, 1, "1·G·D"),
    ("Hacienda del Marques Reserva", 2020, 1, "1·G·D"),
    ("Abadia Retuerta Seleccion Especial", 2020, 1, "1·G·D"),
    ("Unico Vega Sicilia", 2015, 1, "1·G·A"),
    ("Valbuena 5", 2020, 1, "1·G·A"),
    ("La Rioja Alta Gran Reserva 904", 2015, 1, "1·G·A"),
    ("Abadia Retuerta Seleccion Especial", 2021, 1, "1·G·A"),
    ("Hacienda del Marques Reserva", 2020, 1, "1·G·A"),
    ("Bosque de Matasnos Reserva", 2019, 1, "1·G·A"),
    ("Vina Ardanza Reserva", 2019, 1, "1·H·D"),
    ("La Emperatriz Finca La Emperatriz", 2019, 1, "1·H·D"),
    ("Marques de Murrieta Reserva", 2021, 1, "1·H·D"),
    ("Bodegas Lan Reserva", 2021, 1, "1·H·D"),
    ("Corimbo", 2022, 1, "1·H·D"),
    ("Corimbo I Reserva", 2018, 1, "1·H·A"),
    ("Corimbo I Reserva", 2022, 1, "1·H·A"),
    ("Bosque de Matasnos Reserva", 2022, 1, "1·H·A"),
    ("Roda Reserva", 2021, 1, "1·H·A"),
    ("Vina Ardanza Reserva", 2019, 1, "1·I·D"),
    ("La Emperatriz Finca La Emperatriz", 2019, 1, "1·I·D"),
    ("Marques de Murrieta Reserva", 2021, 1, "1·I·D"),
    ("Bodegas Lan Reserva", 2021, 1, "1·I·D"),
    ("Corimbo", 2022, 1, "1·I·D"),
    ("Pintia", 2017, 1, "1·I·A"),
    ("Malleolus Emilio Moro", 2021, 1, "1·I·A"),
    ("Malleolus de Valderramiro", 2021, 1, "1·I·A"),
    ("Malleolus de Sanchomartin", 2021, 1, "1·I·A"),
    ("Lacima Dominio do Bibei", 2020, 1, "1·BASE"),
    ("Sangarida Pico Tuerto", 2022, 1, "1·BASE"),
    ("Bosque de Matasnos", 2022, 1, "1·BASE"),
    ("Ata Rangi Pinot Noir", 2021, 1, "1·BASE"),
    ("San Roman", 2022, 1, "1·BASE"),
    ("Shannon Vineyards Mount Bullet", 2020, 1, "1·BASE"),
]


CURATED_POD_BY_SOURCE = {
    "la baixada alvaro palacios::2022": "POD015976",
    "salanques mas doix::2022": "POD018766",
    "les terrasses velles vinyes alvaro palacios::2022": "POD012960",
    "casa castillo::2023": "POD018084",
    "la tendida casa castillo::2023": "POD019624",
    "pintia::2017": "POD013547",
    "pintia::2020": "POD016962",
    "la rioja alta gran reserva 904::2016": "POD018770",
    "la rioja alta gran reserva 904::2015": "POD018770",
    "hispania dominio del aguila::2021": "POD015343",
    "dominio del aguila reserva::2020": "POD_TEMP_1040",
    "dominio del aguila camino del soto::2022": "POD015918",
    "mauro vs::2022": "POD016105",
    "la emperatriz finca la emperatriz::2019": "POD019735",
    "la emperatriz finca la emperatriz::2020": "POD019735",
    "bideona::2020": "POD013749",
    "macan clasico::2021": "POD016957",
    "macan::2020": "POD014428",
    "corimbo i reserva::2018": "POD017118",
    "corimbo i reserva::2022": "POD018632",
    "bosque de matasnos reserva::2019": "POD013769",
    "bosque de matasnos reserva::2022": "POD016574",
    "abadia retuerta seleccion especial::2020": "POD012811",
    "abadia retuerta seleccion especial::2021": "POD018922",
    "unico vega sicilia::2015": "POD016966",
    "valbuena 5::2020": "POD016964",
    "vina ardanza reserva::2019": "POD017679",
    "marques de murrieta reserva::2021": "POD017713",
    "corimbo::2022": "POD018632",
    "roda reserva::2021": "POD015674",
    "malleolus de valderramiro::2021": "POD015579",
    "malleolus de sanchomartin::2021": "POD019082",
    "lacima dominio do bibei::2020": "POD016340",
    "sangarida pico tuerto::2022": "POD016562",
    "bosque de matasnos::2022": "POD016574",
    "ata rangi pinot noir::2021": "POD018202",
    "san roman::2022": "POD016113",
    "shannon vineyards mount bullet::2020": "POD018201",
}


def build_source_rows() -> list[SourceRow]:
    rows: list[SourceRow] = []
    for wine_text, year, qty, location in MANUAL_ROWS:
        text = normalize_spaces(wine_text)
        rows.append(
            SourceRow(
                wine_text=text,
                year=year,
                qty=int(qty),
                location=location,
                norm_text=normalize_text(text),
                tokens=tokenize(text),
            )
        )
    return rows


def score_candidate(source: SourceRow, candidate: CatalogEntry) -> float:
    seq_desc = seq_ratio(source.norm_text, candidate.norm_desc)
    seq_search = seq_ratio(source.norm_text, candidate.norm_search)
    jac_desc = jaccard(source.tokens, candidate.tokens_desc)
    jac_search = jaccard(source.tokens, candidate.tokens_search)

    seq_best = max(seq_desc, seq_search)
    jac_best = max(jac_desc, jac_search)
    if seq_best < 0.45 and jac_best < 0.08:
        return -1.0

    score = 0.64 * seq_best + 0.30 * jac_best
    if source.year is not None and candidate.ano is not None:
        delta = abs(source.year - candidate.ano)
        if delta == 0:
            score += 0.12
        elif delta == 1:
            score += 0.03
        elif delta == 2:
            score -= 0.06
        else:
            return -1.0

    if source.tokens and source.tokens.issubset(candidate.tokens_search):
        score += 0.04
    if len(source.tokens & candidate.tokens_search) >= 3:
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

    if not ((best_score >= SCORE_MIN and margin >= MARGIN_MIN) or best_score >= HARD_MIN):
        return None
    return MatchResult(score=best_score, margin=margin, second_score=second_score, entry=best_entry)


def write_source_csv(rows: list[SourceRow]) -> None:
    with SOURCE_CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["wine_text", "year", "qty", "location"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "wine_text": row.wine_text,
                    "year": row.year or "",
                    "qty": row.qty,
                    "location": row.location,
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Grava alterações no catálogo")
    args = parser.parse_args()

    catalog = json.load(DB_PATH.open("r", encoding="utf-8"))
    if not isinstance(catalog, list):
        raise RuntimeError("Formato inesperado de data/bodega_webapp.json: esperado lista de vinhos")

    source_rows = build_source_rows()
    write_source_csv(source_rows)

    candidates: list[CatalogEntry] = []
    for i, wine in enumerate(catalog):
        descripcion = normalize_spaces(wine.get("descripcion", ""))
        bodega = normalize_spaces(wine.get("bodega", ""))
        ano_raw = wine.get("ano")
        try:
            ano = int(ano_raw) if ano_raw is not None else None
        except Exception:
            ano = None
        search = normalize_spaces(f"{bodega} {descripcion} {ano or ''}")
        candidates.append(
            CatalogEntry(
                index=i,
                pod=normalize_spaces(wine.get("pod", "")),
                ano=ano,
                descripcion=descripcion,
                bodega=bodega,
                norm_desc=normalize_text(descripcion),
                norm_search=normalize_text(search),
                tokens_desc=tokenize(descripcion),
                tokens_search=tokenize(search),
            )
        )
    catalog_by_pod = {normalize_spaces(w.get("pod", "")): w for w in catalog}

    grouped_by_pod: dict[str, dict[str, Any]] = defaultdict(lambda: {"qty_total": 0, "locations": set(), "rows": []})
    unmatched_rows: list[dict[str, Any]] = []

    for src in source_rows:
        source_key = normalize_text(src.wine_text)
        source_key_year = f"{source_key}::{src.year}" if src.year is not None else None
        curated_pod = None
        if source_key_year:
            curated_pod = CURATED_POD_BY_SOURCE.get(source_key_year)
        if not curated_pod:
            curated_pod = CURATED_POD_BY_SOURCE.get(source_key)
        if curated_pod and curated_pod in catalog_by_pod:
            wine = catalog_by_pod[curated_pod]
            grp = grouped_by_pod[curated_pod]
            grp["qty_total"] += src.qty
            grp["locations"].add(src.location)
            grp["rows"].append(
                {
                    "wine_text": src.wine_text,
                    "year": src.year,
                    "qty": src.qty,
                    "location": src.location,
                    "score": 1.0,
                    "margin": 1.0,
                    "match_mode": "curated",
                }
            )
            continue

        match = pick_best_match(src, candidates)
        if not match:
            # log best attempt for troubleshooting
            scored = [(score_candidate(src, c), c) for c in candidates]
            scored = [(s, c) for s, c in scored if s >= 0]
            scored.sort(key=lambda x: x[0], reverse=True)
            best = scored[0] if scored else None
            second = scored[1] if len(scored) > 1 else None
            unmatched_rows.append(
                {
                    "wine_text": src.wine_text,
                    "year": src.year,
                    "qty": src.qty,
                    "location": src.location,
                    "best_score": round(best[0], 4) if best else None,
                    "best_margin": round((best[0] - second[0]), 4) if best and second else None,
                    "best_pod": best[1].pod if best else None,
                    "best_desc": best[1].descripcion if best else None,
                    "best_bodega": best[1].bodega if best else None,
                    "best_year": best[1].ano if best else None,
                }
            )
            continue

        pod = match.entry.pod
        grp = grouped_by_pod[pod]
        grp["qty_total"] += src.qty
        grp["locations"].add(src.location)
        grp["rows"].append(
            {
                "wine_text": src.wine_text,
                "year": src.year,
                "qty": src.qty,
                "location": src.location,
                "score": round(match.score, 4),
                "margin": round(match.margin, 4),
                "match_mode": "fuzzy",
            }
        )
    updated_entries: list[dict[str, Any]] = []
    for pod, payload in grouped_by_pod.items():
        wine = catalog_by_pod.get(pod)
        if not wine:
            continue
        ensure_establecimientos(wine)
        est = wine["establecimientos"]["spa"]

        old_loc_set = split_locations(est.get("localizacion"))
        new_loc_set = set(payload["locations"])
        merged_loc_set = old_loc_set | new_loc_set
        merged_loc = " / ".join(sorted(merged_loc_set, key=location_sort_key)) if merged_loc_set else None

        est["localizacion"] = merged_loc

        updated_entries.append(
            {
                "pod": pod,
                "descripcion": wine.get("descripcion"),
                "bodega": wine.get("bodega"),
                "rows_count": len(payload["rows"]),
                "qty_manual_total": payload["qty_total"],
                "location_before_count": len(old_loc_set),
                "location_after_count": len(merged_loc_set),
                "location_after": merged_loc,
            }
        )

    if args.apply:
        DB_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    unmatched_headers = [
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
        "manual_rows_total": len(source_rows),
        "manual_qty_total": sum(r.qty for r in source_rows),
        "matched_rows": sum(len(v["rows"]) for v in grouped_by_pod.values()),
        "matched_unique_pods": len(grouped_by_pod),
        "unmatched_rows": len(unmatched_rows),
        "updated_entries_count": len(updated_entries),
        "updated_entries": sorted(updated_entries, key=lambda x: x["rows_count"], reverse=True),
        "unmatched": unmatched_rows,
        "paths": {
            "db": str(DB_PATH),
            "source_csv": str(SOURCE_CSV_PATH),
            "report_json": str(REPORT_JSON_PATH),
            "report_unmatched_csv": str(REPORT_UNMATCHED_CSV_PATH),
        },
        "thresholds": {
            "SCORE_MIN": SCORE_MIN,
            "MARGIN_MIN": MARGIN_MIN,
            "HARD_MIN": HARD_MIN,
        },
        "location_convention": "1·<BALDA>·A (atrás) | 1·<BALDA>·D (frente) | 1·BASE",
        "unmatched_reasons": dict(Counter("low_confidence_or_ambiguous" for _ in unmatched_rows)),
    }
    REPORT_JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"mode={report['mode']}")
    print(f"manual_rows_total={report['manual_rows_total']}")
    print(f"manual_qty_total={report['manual_qty_total']}")
    print(f"matched_rows={report['matched_rows']}")
    print(f"matched_unique_pods={report['matched_unique_pods']}")
    print(f"unmatched_rows={report['unmatched_rows']}")
    print(f"updated_entries_count={report['updated_entries_count']}")
    print(f"report_json={REPORT_JSON_PATH}")
    print(f"report_unmatched_csv={REPORT_UNMATCHED_CSV_PATH}")


if __name__ == "__main__":
    main()
