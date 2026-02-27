#!/usr/bin/env python3
"""
Importa localizações da Tasca Fina a partir de:
  scripts/tasca fina 18 de febrero (3).pdf

Fluxo:
1) Extrai linhas (nome, ano, qty, posição) da PDF via streams + ToUnicode.
2) Enriquecer ano/qty ausentes via data/lista_unica_vinos.csv (fonte antiga).
3) Faz matching seguro com data/bodega_webapp.json.
4) Aplica apenas establecimientos.tasca_fina.localizacion (não altera pvp/unidades).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
import zlib
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "scripts" / "tasca fina 18 de febrero (3).pdf"
LEGACY_CSV_PATH = ROOT / "data" / "lista_unica_vinos.csv"
DB_PATH = ROOT / "data" / "bodega_webapp.json"

EXTRACTED_CSV_PATH = ROOT / "reports" / "tasca_fina_18_febrero_3_extracted.csv"
REPORT_JSON_PATH = ROOT / "reports" / "tasca_fina_import_report.json"
UNMATCHED_CSV_PATH = ROOT / "reports" / "tasca_fina_import_unmatched.csv"

# Matching thresholds (conservador + fallback de alta cobertura lexical).
SCORE_MIN = 0.72
MARGIN_MIN = 0.03
HARD_SCORE = 0.83
LEXICAL_SCORE = 0.76
LEXICAL_COVER = 0.85
GATE_MIN = 0.40


@dataclass
class ExtractedRow:
    page: int
    y: float
    name: str
    ano: str
    qty: str
    pos: str
    compact_loc: str | None


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
        "chateau",
        "domaine",
        "dominio",
        "vino",
        "magnum",
        "grand",
        "cru",
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


def token_coverage(a: set[str], b: set[str]) -> float:
    if not a:
        return 0.0
    return len(a & b) / len(a)


def parse_year(value: Any) -> int | None:
    match = re.search(r"(19|20)\d{2}", str(value or ""))
    return int(match.group(0)) if match else None


def parse_qty(value: Any) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else None


def parse_compact_location(raw_position: str) -> str | None:
    text = normalize_spaces(raw_position).upper()
    if not text:
        return None

    if "JAM" in text and "CAV" not in text:
        return "JAM"

    # Ex.: CAV 2 - 10 DER / CAVA 4 - 4B IZQ / CAV 1 - EXP CEN
    match = re.search(
        r"\bCAVA?\s*(\d{1,2})\s*-\s*([A-Z0-9]{1,8})(?:\s+([A-Z]{2,6}|[A-Z]{1,3}\s+[A-Z]{1,3}))?",
        text,
    )
    if not match:
        return None

    cava = match.group(1)
    balda = match.group(2)
    pos_raw = (match.group(3) or "").strip().replace(" ", "_")
    pos = {
        "IZQUIERDA": "IZQ",
        "DERECHA": "DER",
        "CENTRO": "CEN",
    }.get(pos_raw, pos_raw)

    if pos:
        return f"{cava}·{balda}·{pos}"
    return f"{cava}·{balda}"


def parse_pdf_objects(pdf_bytes: bytes) -> dict[int, bytes]:
    pattern = re.compile(rb"(\d+)\s+0\s+obj\b(.*?)endobj", re.S)
    return {int(m.group(1)): m.group(2) for m in pattern.finditer(pdf_bytes)}


def get_obj_stream(obj_body: bytes) -> bytes | None:
    match = re.search(rb"stream\r?\n(.*?)\r?\nendstream", obj_body, re.S)
    if not match:
        return None
    raw = match.group(1)
    try:
        return zlib.decompress(raw)
    except Exception:
        return raw


def parse_tounicode_map(stream_data: bytes) -> dict[int, str]:
    text = stream_data.decode("latin1", "ignore")
    mapping: dict[int, str] = {}

    for section in re.finditer(r"beginbfchar\s*(.*?)\s*endbfchar", text, re.S):
        for src_hex, dst_hex in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", section.group(1)):
            mapping[int(src_hex, 16)] = bytes.fromhex(dst_hex).decode("utf-16-be", "ignore")

    for section in re.finditer(r"beginbfrange\s*(.*?)\s*endbfrange", text, re.S):
        for line in section.group(1).splitlines():
            line = line.strip()
            if not line:
                continue

            arr_match = re.match(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.+)\]", line)
            if arr_match:
                start = int(arr_match.group(1), 16)
                end = int(arr_match.group(2), 16)
                values = re.findall(r"<([0-9A-Fa-f]+)>", arr_match.group(3))
                for idx, code in enumerate(range(start, end + 1)):
                    if idx < len(values):
                        mapping[code] = bytes.fromhex(values[idx]).decode("utf-16-be", "ignore")
                continue

            seq_match = re.match(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", line)
            if seq_match:
                start = int(seq_match.group(1), 16)
                end = int(seq_match.group(2), 16)
                base = int(seq_match.group(3), 16)
                for idx, code in enumerate(range(start, end + 1)):
                    uni = base + idx
                    mapping[code] = bytes.fromhex(f"{uni:04X}").decode("utf-16-be", "ignore")

    return mapping


def decode_hex_text(hex_blob: str, cmap: dict[int, str]) -> str:
    if not hex_blob:
        return ""
    step = 4 if len(hex_blob) % 4 == 0 else 2
    out: list[str] = []
    for idx in range(0, len(hex_blob), step):
        chunk = hex_blob[idx : idx + step]
        if not chunk:
            continue
        code = int(chunk, 16)
        out.append(cmap.get(code, ""))
    return "".join(out)


def extract_rows_from_pdf(pdf_path: Path) -> list[ExtractedRow]:
    pdf_bytes = pdf_path.read_bytes()
    objects = parse_pdf_objects(pdf_bytes)

    # Font object -> ToUnicode map.
    font_maps: dict[int, dict[int, str]] = {}
    for obj_num, obj_body in objects.items():
        if b"/Type/Font" not in obj_body:
            continue
        tu_match = re.search(rb"/ToUnicode\s+(\d+)\s+0\s+R", obj_body)
        if not tu_match:
            continue
        tu_obj = int(tu_match.group(1))
        tu_stream = get_obj_stream(objects.get(tu_obj, b""))
        if tu_stream:
            font_maps[obj_num] = parse_tounicode_map(tu_stream)

    pages_root = objects.get(2, b"")
    page_refs = [int(v) for v in re.findall(rb"(\d+)\s+0\s+R", pages_root)]

    extracted: list[ExtractedRow] = []

    for page_obj in page_refs:
        page_body = objects.get(page_obj, b"")
        contents_match = re.search(rb"/Contents\s+(\d+)\s+0\s+R", page_body)
        if not contents_match:
            continue
        content_obj = int(contents_match.group(1))
        content_stream = get_obj_stream(objects.get(content_obj, b""))
        if not content_stream:
            continue

        content_text = content_stream.decode("latin1", "ignore")
        page_font_ref = {
            name.decode(): int(font_obj)
            for name, font_obj in re.findall(rb"/(F\d+)\s+(\d+)\s+0\s+R", page_body)
        }

        runs: list[dict[str, Any]] = []
        current_font: str | None = None
        current_x: float = 0.0
        current_y: float = 0.0

        for bt_block in re.findall(r"BT(.*?)ET", content_text, re.S):
            for line in bt_block.splitlines():
                line = line.strip()
                if not line:
                    continue

                font_match = re.search(r"/(F\d+)\s+[\d.]+\s+Tf", line)
                if font_match:
                    current_font = font_match.group(1)

                tm_match = re.search(r"([\-0-9.]+)\s+([\-0-9.]+)\s+Tm", line)
                if tm_match:
                    parts = line.split("Tm")[0].split()
                    if len(parts) >= 2:
                        current_x = float(parts[-2])
                        current_y = float(parts[-1])

                hex_chunks: list[str] = []
                hex_chunks.extend(re.findall(r"<([0-9A-Fa-f]+)>\s*Tj", line))
                tj_match = re.search(r"\[(.*?)\]\s*TJ", line)
                if tj_match:
                    hex_chunks.extend(re.findall(r"<([0-9A-Fa-f]+)>", tj_match.group(1)))

                if not hex_chunks:
                    continue

                font_obj = page_font_ref.get(current_font or "", 0)
                cmap = font_maps.get(font_obj, {})
                decoded = "".join(decode_hex_text(chunk, cmap) for chunk in hex_chunks)
                if not decoded:
                    continue

                if (
                    runs
                    and runs[-1]["font"] == current_font
                    and abs(runs[-1]["x"] - current_x) < 0.01
                    and abs(runs[-1]["y"] - current_y) < 0.01
                ):
                    runs[-1]["text"] += decoded
                else:
                    runs.append(
                        {
                            "font": current_font or "",
                            "x": current_x,
                            "y": current_y,
                            "text": decoded,
                        }
                    )

        # Agrupa por linha (y) com bucket de 0.5 para unir colunas.
        rows_by_y: dict[float, list[dict[str, Any]]] = defaultdict(list)
        for run in runs:
            y_bucket = round(run["y"] * 2) / 2.0
            rows_by_y[y_bucket].append(run)

        for y_bucket, row_runs in rows_by_y.items():
            cols = {"name": "", "ano": "", "qty": "", "pos": ""}
            for run in sorted(row_runs, key=lambda r: r["x"]):
                text = normalize_spaces(run["text"])
                if not text:
                    continue
                x = run["x"]
                if x < 220:
                    cols["name"] += text
                elif x < 320:
                    cols["ano"] += text
                elif x < 390:
                    cols["qty"] += text
                else:
                    cols["pos"] += text

            name = normalize_spaces(cols["name"])
            ano = normalize_spaces(cols["ano"])
            qty = normalize_spaces(cols["qty"])
            pos = normalize_spaces(cols["pos"])
            compact = parse_compact_location(pos)

            # Mantém somente linhas com posição válida no layout.
            if not name:
                continue
            if not compact:
                continue

            extracted.append(
                ExtractedRow(
                    page=page_obj,
                    y=y_bucket,
                    name=name,
                    ano=ano,
                    qty=qty,
                    pos=pos,
                    compact_loc=compact,
                )
            )

    # Remove duplicados exatos (page+y+name+pos).
    unique: dict[tuple[int, float, str, str], ExtractedRow] = {}
    for row in extracted:
        key = (row.page, row.y, row.name, row.pos)
        unique[key] = row
    return list(unique.values())


def enrich_rows_with_legacy(rows: list[ExtractedRow], legacy_csv_path: Path) -> list[ExtractedRow]:
    if not legacy_csv_path.exists():
        return rows

    with legacy_csv_path.open("r", encoding="utf-8") as file:
        legacy = list(csv.DictReader(file))

    lookup: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in legacy:
        source = (row.get("source_file") or "").lower()
        if "tasca fina 18 de febrero" not in source:
            continue
        lookup[(normalize_text(row.get("item", "")), normalize_text(row.get("posicion", "")))].append(row)

    enriched: list[ExtractedRow] = []
    for row in rows:
        ano = row.ano
        qty = row.qty
        key = (normalize_text(row.name), normalize_text(row.pos))
        candidates = lookup.get(key, [])

        if not parse_year(ano) and candidates:
            years = [c.get("ano", "") for c in candidates if parse_year(c.get("ano"))]
            if years:
                ano = years[0]

        if parse_qty(qty) is None and candidates:
            qtys = [c.get("qty", "") for c in candidates if parse_qty(c.get("qty")) is not None]
            if qtys:
                qty = qtys[0]

        enriched.append(
            ExtractedRow(
                page=row.page,
                y=row.y,
                name=row.name,
                ano=ano,
                qty=qty,
                pos=row.pos,
                compact_loc=row.compact_loc,
            )
        )

    return enriched


def score_match(row: ExtractedRow, candidate: CatalogEntry) -> tuple[float, float, bool, float, float]:
    row_norm = normalize_text(row.name)
    row_tokens = tokenize(row.name)

    desc_score = max(seq_ratio(row_norm, candidate.norm_desc), jaccard(row_tokens, candidate.tokens_desc))
    bodega_score = max(seq_ratio(row_norm, candidate.norm_bodega), jaccard(row_tokens, candidate.tokens_bodega))
    gate = max(desc_score, bodega_score)
    if gate < GATE_MIN:
        return (-1.0, 0.0, True, desc_score, bodega_score)

    score = max(desc_score, (0.75 * desc_score + 0.25 * bodega_score))
    year_ok = True

    row_year = parse_year(row.ano)
    if row_year is not None and candidate.ano is not None:
        if row_year == candidate.ano:
            score += 0.12
        elif abs(row_year - candidate.ano) == 1:
            score += 0.03
        elif abs(row_year - candidate.ano) > 2:
            score -= 0.12
            year_ok = False

    if row_tokens and row_tokens.issubset(candidate.tokens_desc):
        score += 0.04

    coverage = max(
        token_coverage(row_tokens, candidate.tokens_desc),
        token_coverage(row_tokens, candidate.tokens_bodega),
    )

    return (score, coverage, year_ok, desc_score, bodega_score)


def pick_best_match(row: ExtractedRow, entries: list[CatalogEntry]) -> tuple[CatalogEntry, float, float, float] | None:
    best: tuple[CatalogEntry, float, float, bool] | None = None
    second = -1.0

    for candidate in entries:
        score, coverage, year_ok, _desc, _bodega = score_match(row, candidate)
        if score < 0:
            continue
        if best is None or score > best[1]:
            second = best[1] if best is not None else second
            best = (candidate, score, coverage, year_ok)
        elif score > second:
            second = score

    if best is None:
        return None

    candidate, score, coverage, year_ok = best
    margin = score - second
    auto = (
        (score >= SCORE_MIN and margin >= MARGIN_MIN)
        or score >= HARD_SCORE
        or (score >= LEXICAL_SCORE and coverage >= LEXICAL_COVER and year_ok)
    )
    if not auto:
        return None

    return (candidate, score, margin, coverage)


def location_sort_key(value: str) -> tuple[int, str, str]:
    parts = [p.strip().upper() for p in str(value or "").split("·") if p.strip()]
    cave = parse_qty(parts[0]) if parts else None
    cave_n = cave if cave is not None else 999
    balda = parts[1] if len(parts) > 1 else ""
    return (cave_n, balda, value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Aplica atualizações no data/bodega_webapp.json")
    args = parser.parse_args()

    if not PDF_PATH.exists():
        raise SystemExit(f"PDF não encontrada: {PDF_PATH}")

    rows = extract_rows_from_pdf(PDF_PATH)
    rows = enrich_rows_with_legacy(rows, LEGACY_CSV_PATH)

    EXTRACTED_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EXTRACTED_CSV_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["page", "y", "name", "ano", "qty", "pos", "compact_loc"])
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (r.page, -r.y, r.name)):
            writer.writerow(
                {
                    "page": row.page,
                    "y": f"{row.y:.1f}",
                    "name": row.name,
                    "ano": row.ano,
                    "qty": row.qty,
                    "pos": row.pos,
                    "compact_loc": row.compact_loc or "",
                }
            )

    catalog = json.loads(DB_PATH.read_text(encoding="utf-8"))
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

    matched: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    pod_aggregate: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"rows": [], "locations": set(), "scores": [], "coverages": []}
    )

    for row in rows:
        if not row.compact_loc:
            continue
        result = pick_best_match(row, entries)
        if not result:
            unmatched.append(
                {
                    "name": row.name,
                    "ano": row.ano,
                    "qty": row.qty,
                    "pos": row.pos,
                    "compact_loc": row.compact_loc,
                }
            )
            continue

        entry, score, margin, coverage = result
        matched.append(
            {
                "pod": entry.pod,
                "name": row.name,
                "ano": row.ano,
                "qty": row.qty,
                "pos": row.pos,
                "compact_loc": row.compact_loc,
                "score": round(score, 4),
                "margin": round(margin, 4),
                "coverage": round(coverage, 4),
                "matched_bodega": entry.bodega,
                "matched_desc": entry.descripcion,
            }
        )

        payload = pod_aggregate[entry.pod]
        payload["rows"].append(row)
        payload["locations"].add(row.compact_loc)
        payload["scores"].append(score)
        payload["coverages"].append(coverage)

    applied_preview: list[dict[str, Any]] = []
    for pod, payload in pod_aggregate.items():
        locations = sorted(payload["locations"], key=location_sort_key)
        loc_value = " / ".join(locations)
        applied_preview.append(
            {
                "pod": pod,
                "rows_count": len(payload["rows"]),
                "locations_count": len(locations),
                "localizacion": loc_value,
                "avg_score": round(sum(payload["scores"]) / len(payload["scores"]), 4),
                "avg_coverage": round(sum(payload["coverages"]) / len(payload["coverages"]), 4),
            }
        )
    applied_preview.sort(key=lambda r: r["pod"])

    updates_applied = 0
    if args.apply:
        by_pod = {str(w.get("pod", "")).strip(): w for w in catalog}
        for row in applied_preview:
            wine = by_pod.get(row["pod"])
            if not wine:
                continue

            establishments = wine.get("establecimientos")
            if not isinstance(establishments, dict):
                establishments = {}
                wine["establecimientos"] = establishments

            tasca = establishments.get("tasca_fina")
            if not isinstance(tasca, dict):
                tasca = {"pvp": None, "unidades": None, "localizacion": None}
                establishments["tasca_fina"] = tasca

            existing = tasca.get("localizacion")
            existing_parts = {
                p.strip()
                for p in str(existing or "").split("/")
                if p and str(p).strip()
            }
            new_parts = {
                p.strip()
                for p in str(row["localizacion"] or "").split("/")
                if p and str(p).strip()
            }
            merged = sorted(existing_parts | new_parts, key=location_sort_key)
            tasca["localizacion"] = " / ".join(merged) if merged else None
            updates_applied += 1

        DB_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    unmatched_producers = Counter(normalize_text(r.get("name", "")) for r in unmatched).most_common(40)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "dry_run",
        "pdf_source": str(PDF_PATH),
        "rows_extracted": len(rows),
        "rows_matched": len(matched),
        "rows_unmatched": len(unmatched),
        "matched_unique_pods": len(applied_preview),
        "updates_applied": updates_applied,
        "tasca_locations_to_apply_unique": len(
            {
                part.strip()
                for row in applied_preview
                for part in str(row.get("localizacion", "")).split("/")
                if part.strip()
            }
        ),
        "top_unmatched_names_normalized": unmatched_producers,
        "preview_first_150": applied_preview[:150],
        "matched_first_200": matched[:200],
        "unmatched_first_200": unmatched[:200],
    }

    REPORT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with UNMATCHED_CSV_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["name", "ano", "qty", "pos", "compact_loc"])
        writer.writeheader()
        for row in unmatched:
            writer.writerow(row)

    print("TASCA import summary")
    print(f"- mode: {report['mode']}")
    print(f"- rows extracted: {report['rows_extracted']}")
    print(f"- rows matched: {report['rows_matched']}")
    print(f"- matched unique pods: {report['matched_unique_pods']}")
    print(f"- rows unmatched: {report['rows_unmatched']}")
    print(f"- updates applied: {report['updates_applied']}")
    print(f"- unique tasca locations applied: {report['tasca_locations_to_apply_unique']}")
    print(f"- report: {REPORT_JSON_PATH}")
    print(f"- unmatched csv: {UNMATCHED_CSV_PATH}")
    print(f"- extracted csv: {EXTRACTED_CSV_PATH}")


if __name__ == "__main__":
    main()

