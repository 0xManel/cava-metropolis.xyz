#!/usr/bin/env python3
"""
Analisa vinhos pendentes da BODEGA -2 (fora de tasca fina) e gera
um relatório para facilitar cadastro completo no card expandido.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "lista_unica_vinos.csv"
DB_PATH = ROOT / "data" / "bodega_webapp.json"
OUT_JSON = ROOT / "reports" / "bodega_minus2_pending_wines_analysis.json"
OUT_CSV = ROOT / "reports" / "bodega_minus2_pending_wines_analysis.csv"
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


def parse_qty(raw_qty: str) -> int:
    match = re.search(r"\d+", str(raw_qty or ""))
    if not match:
        return 0
    return int(match.group(0))


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


def infer_from_source(source_file: str) -> dict[str, str]:
    s = normalize_text(source_file)
    if "italia" in s and "francia italia" not in s:
        return {"pais": "Italia", "tipo": "Tinto/Blanco", "contexto": "italia"}
    if "borgona blancos" in s:
        return {"pais": "França", "tipo": "Blanco", "contexto": "borgona_blancos"}
    if "borgona tintos" in s:
        return {"pais": "França", "tipo": "Tinto", "contexto": "borgona_tintos"}
    if "resto francia italia blancos" in s:
        return {"pais": "França/Italia", "tipo": "Blanco", "contexto": "fr_it_blancos"}
    if "resto francia" in s:
        return {"pais": "França", "tipo": "Tinto/Blanco", "contexto": "resto_francia"}
    if "usa y sudafrica" in s:
        return {"pais": "EUA/África do Sul", "tipo": "Tinto", "contexto": "usa_sa_to"}
    return {"pais": "—", "tipo": "—", "contexto": "desconocido"}


def infer_region_grape(item: str) -> tuple[str, str, str, str]:
    n = normalize_text(item)

    rules = [
        ("barolo", ("Piamonte", "Nebbiolo", "Continental com outono longo.", "Marga calcárea.")),
        ("barbaresco", ("Piamonte", "Nebbiolo", "Continental com outono longo.", "Marga calcárea.")),
        ("langhe nebbiolo", ("Piamonte", "Nebbiolo", "Continental com neblina sazonal.", "Marga e calcário.")),
        ("etna rosso", ("Sicilia", "Nerello Mascalese", "Mediterrâneo com altitude vulcânica.", "Vulcânico basáltico.")),
        ("etna bianco", ("Sicilia", "Carricante", "Mediterrâneo com altitude vulcânica.", "Vulcânico basáltico.")),
        ("brunello di montalcino", ("Toscana", "Sangiovese", "Mediterrâneo continental.", "Galestro e albarese.")),
        ("rosso di montalcino", ("Toscana", "Sangiovese", "Mediterrâneo continental.", "Galestro e albarese.")),
        ("bolgheri", ("Toscana", "Blend bordalês", "Mediterrâneo moderado pelo mar.", "Argila, calcário e cascalho.")),
        ("valpolicella", ("Véneto", "Corvina (blend)", "Continental-mediterrâneo.", "Calcário e argila.")),
        ("chateauneuf du pape blanc", ("Ródano Sul", "Blend blanc", "Mediterrâneo quente.", "Galets e calcário.")),
        ("chateauneuf du pape", ("Ródano Sul", "Grenache (blend)", "Mediterrâneo quente.", "Galets e argila.")),
        ("hermitage blanc", ("Ródano Norte", "Marsanne/Roussanne", "Continental-mediterrâneo.", "Granito e aluviais.")),
        ("condrieu", ("Ródano Norte", "Viognier", "Continental-mediterrâneo.", "Granito.")),
        ("pouilly fuisse", ("Borgoña", "Chardonnay", "Continental.", "Calcário e marga.")),
        ("meursault", ("Borgoña", "Chardonnay", "Continental.", "Calcário e marga.")),
        ("puligny montrachet", ("Borgoña", "Chardonnay", "Continental.", "Calcário e marga.")),
        ("montrachet", ("Borgoña", "Chardonnay", "Continental.", "Calcário e marga.")),
        ("corton charlemagne", ("Borgoña", "Chardonnay", "Continental.", "Calcário e marga.")),
        ("musigny blanc", ("Borgoña", "Chardonnay", "Continental.", "Calcário e marga.")),
        ("musigny", ("Borgoña", "Pinot Noir", "Continental.", "Calcário e marga.")),
        ("gevrey", ("Borgoña", "Pinot Noir", "Continental.", "Calcário e marga.")),
        ("vosne", ("Borgoña", "Pinot Noir", "Continental.", "Calcário e marga.")),
        ("bourgogne", ("Borgoña", "Pinot Noir/Chardonnay", "Continental.", "Calcário e marga.")),
        ("chablis", ("Borgoña", "Chardonnay", "Continental fresco.", "Calcário kimmeridgiano.")),
        ("pithos bianco", ("Sicilia", "Grecanico (blend)", "Mediterrâneo quente.", "Calcário e vulcânico.")),
        ("sauvignon", ("—", "Sauvignon Blanc", "Preferência por clima fresco.", "Sílex/calcário/granito.")),
    ]

    for keyword, payload in rules:
        if keyword in n:
            return payload

    return ("—", "—", "—", "—")


def year_delta(year_a: int | None, year_b: int | None) -> int:
    if year_a is None or year_b is None:
        return 99
    return abs(year_a - year_b)


@dataclass
class CatalogEntry:
    pod: str
    ano: int | None
    pais: str
    region: str
    tipo: str
    formato: str
    uvas: list[str]
    bodega: str
    descripcion: str
    norm_bodega: str
    norm_desc: str
    tokens_bodega: set[str]
    tokens_desc: set[str]


def score_candidate(
    producer_norm: str,
    producer_tokens: set[str],
    item_norm: str,
    item_tokens: set[str],
    year: int | None,
    candidate: CatalogEntry,
) -> tuple[float, float]:
    producer_score = max(
        seq_ratio(producer_norm, candidate.norm_bodega),
        jaccard(producer_tokens, candidate.tokens_bodega),
    )
    if producer_score < PRODUCER_GATE_MIN:
        return (-1.0, producer_score)

    if year is not None and candidate.ano is not None and abs(candidate.ano - year) > 2:
        return (-1.0, producer_score)

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

    return (score, producer_score)


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open("r", encoding="utf-8")))
    rows = [row for row in rows if (row.get("source_file") or "").strip() != TASCA_FILE]

    catalog_raw = json.load(DB_PATH.open("r", encoding="utf-8"))
    catalog: list[CatalogEntry] = []
    for wine in catalog_raw:
        uvas = []
        for grape in wine.get("uvas") or []:
            if isinstance(grape, dict):
                name = str(grape.get("nome", "")).strip()
            else:
                name = str(grape).strip()
            if name:
                uvas.append(name)
        tipo = ""
        if isinstance(wine.get("tipo"), dict):
            tipo = str(wine["tipo"].get("nombre", "")).strip()
        formato = ""
        if isinstance(wine.get("formato"), dict):
            formato = str(wine["formato"].get("etiqueta", "")).strip()

        catalog.append(
            CatalogEntry(
                pod=str(wine.get("pod", "")).strip(),
                ano=wine.get("ano") if isinstance(wine.get("ano"), int) else None,
                pais=str(wine.get("pais", "")).strip(),
                region=str(wine.get("region", "")).strip(),
                tipo=tipo,
                formato=formato,
                uvas=uvas,
                bodega=str(wine.get("bodega", "")).strip(),
                descripcion=str(wine.get("descripcion", "")).strip(),
                norm_bodega=normalize_text(wine.get("bodega", "")),
                norm_desc=normalize_text(wine.get("descripcion", "")),
                tokens_bodega=tokenize(wine.get("bodega", "")),
                tokens_desc=tokenize(wine.get("descripcion", "")),
            )
        )

    # 1) Reproduce auto matches to know pendentes.
    pending = []
    for row in rows:
        producer_norm = normalize_text(row.get("producer"))
        producer_tokens = tokenize(row.get("producer"))
        item_norm = normalize_text(row.get("item"))
        item_tokens = tokenize(row.get("item"))
        year = parse_year(row.get("ano", ""))

        scored = []
        for entry in catalog:
            score, _producer_score = score_candidate(
                producer_norm,
                producer_tokens,
                item_norm,
                item_tokens,
                year,
                entry,
            )
            if score >= 0:
                scored.append((score, entry))
        if not scored:
            pending.append(row)
            continue

        scored.sort(key=lambda pair: pair[0], reverse=True)
        best_score = scored[0][0]
        second_score = scored[1][0] if len(scored) > 1 else 0.0
        margin = best_score - second_score
        auto = (best_score >= AUTO_MATCH_SCORE and margin >= AUTO_MATCH_MARGIN) or (
            best_score >= AUTO_MATCH_HARD
        )
        if not auto:
            pending.append(row)

    # 2) Aggregate pending unique wines.
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in pending:
        key = (
            normalize_text(row.get("source_file")),
            normalize_text(row.get("producer")),
            normalize_text(row.get("item")),
            str(row.get("ano") or "").strip(),
        )
        if key not in grouped:
            grouped[key] = {
                "source_file": (row.get("source_file") or "").strip(),
                "producer": (row.get("producer") or "").strip(),
                "item": (row.get("item") or "").strip(),
                "ano_raw": (row.get("ano") or "").strip(),
                "ano": parse_year(row.get("ano", "")),
                "qty_total": 0,
                "locations": set(),
                "rows_count": 0,
            }

        grouped[key]["qty_total"] += parse_qty(row.get("qty", ""))
        loc = build_location(row.get("location_group", ""), row.get("posicion", ""))
        if loc:
            grouped[key]["locations"].add(loc)
        grouped[key]["rows_count"] += 1

    analysis = []
    for wine in grouped.values():
        producer_norm = normalize_text(wine["producer"])
        producer_tokens = tokenize(wine["producer"])
        item_norm = normalize_text(wine["item"])
        item_tokens = tokenize(wine["item"])
        year = wine["ano"]

        scored = []
        for entry in catalog:
            score, producer_score = score_candidate(
                producer_norm,
                producer_tokens,
                item_norm,
                item_tokens,
                year,
                entry,
            )
            if score >= 0:
                scored.append((score, producer_score, entry))
        scored.sort(key=lambda row: row[0], reverse=True)
        best = scored[0] if scored else None
        second = scored[1] if len(scored) > 1 else None

        best_score = best[0] if best else 0.0
        best_producer_score = best[1] if best else 0.0
        best_entry = best[2] if best else None
        second_score = second[0] if second else 0.0
        margin = best_score - second_score

        item_similarity = 0.0
        item_subset = False
        if best_entry:
            item_similarity = max(
                seq_ratio(item_norm, best_entry.norm_desc),
                jaccard(item_tokens, best_entry.tokens_desc),
            )
            item_subset = bool(item_tokens) and item_tokens.issubset(best_entry.tokens_desc)
        year_diff = year_delta(year, best_entry.ano if best_entry else None)

        if best_entry and (
            (best_score >= 0.78 and best_producer_score >= 0.55)
            or (best_producer_score >= 0.48 and item_similarity >= 0.72 and year_diff <= 1)
            or (best_producer_score >= 0.45 and item_subset and year_diff <= 1)
        ):
            status = "provavel_alias_existente"
        elif best_entry and (
            best_score >= 0.62
            or (best_producer_score >= 0.42 and item_similarity >= 0.58)
            or (best_producer_score >= 0.40 and item_subset)
        ):
            status = "revisao_manual_obrigatoria"
        else:
            status = "provavel_vinho_novo"

        source_hint = infer_from_source(wine["source_file"])
        inferred_region, inferred_grape, inferred_clima, inferred_suelo = infer_region_grape(
            wine["item"]
        )

        if best_entry and status != "provavel_vinho_novo":
            pais_sugerido = best_entry.pais or source_hint["pais"]
            region_sugerida = best_entry.region or inferred_region
            tipo_sugerido = best_entry.tipo or source_hint["tipo"]
            uva_sugerida = ", ".join(best_entry.uvas) if best_entry.uvas else inferred_grape
            clima_sugerido = inferred_clima if inferred_clima != "—" else "Usar mapeamento atual da região no app."
            suelo_sugerido = inferred_suelo if inferred_suelo != "—" else "Usar mapeamento atual da região no app."
        else:
            pais_sugerido = source_hint["pais"]
            region_sugerida = inferred_region
            tipo_sugerido = source_hint["tipo"]
            uva_sugerida = inferred_grape
            clima_sugerido = inferred_clima
            suelo_sugerido = inferred_suelo

        analysis.append(
            {
                "status": status,
                "source_file": wine["source_file"],
                "producer": wine["producer"],
                "item": wine["item"],
                "ano_raw": wine["ano_raw"],
                "ano": wine["ano"],
                "qty_total": wine["qty_total"],
                "rows_count": wine["rows_count"],
                "locations": sorted(list(wine["locations"]), key=location_sort_key),
                "best_pod": best_entry.pod if best_entry else None,
                "best_descripcion": best_entry.descripcion if best_entry else None,
                "best_bodega": best_entry.bodega if best_entry else None,
                "best_score": round(best_score, 4),
                "best_margin": round(margin, 4),
                "best_producer_score": round(best_producer_score, 4),
                "best_item_similarity": round(item_similarity, 4),
                "best_item_subset": item_subset,
                "best_year_delta": year_diff if year_diff != 99 else None,
                "pais_sugerido": pais_sugerido,
                "region_sugerida": region_sugerida,
                "tipo_sugerido": tipo_sugerido,
                "uva_sugerida": uva_sugerida,
                "clima_sugerido": clima_sugerido,
                "suelo_sugerido": suelo_sugerido,
            }
        )

    analysis.sort(
        key=lambda row: (
            row["status"],
            row["source_file"],
            row["producer"],
            row["item"],
            str(row["ano_raw"] or ""),
        )
    )

    status_counts = defaultdict(int)
    for row in analysis:
        status_counts[row["status"]] += 1

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "bodega_minus2_only_non_tasca",
        "pending_rows_total": len(pending),
        "pending_unique_wines": len(analysis),
        "status_counts": dict(status_counts),
        "data": analysis,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")

    headers = [
        "status",
        "source_file",
        "producer",
        "item",
        "ano_raw",
        "qty_total",
        "rows_count",
        "locations",
        "best_pod",
        "best_descripcion",
        "best_score",
        "best_margin",
        "best_producer_score",
        "pais_sugerido",
        "region_sugerida",
        "tipo_sugerido",
        "uva_sugerida",
        "clima_sugerido",
        "suelo_sugerido",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for row in analysis:
            csv_row = dict(row)
            csv_row["locations"] = " / ".join(row["locations"]) if row["locations"] else ""
            writer.writerow({k: csv_row.get(k, "") for k in headers})

    print(f"pending_rows_total={len(pending)}")
    print(f"pending_unique_wines={len(analysis)}")
    for status, count in sorted(status_counts.items()):
        print(f"{status}={count}")
    print(f"json={OUT_JSON}")
    print(f"csv={OUT_CSV}")


if __name__ == "__main__":
    main()
