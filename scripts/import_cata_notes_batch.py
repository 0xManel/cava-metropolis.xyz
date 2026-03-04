#!/usr/bin/env python3
"""
Importa notas de cata + card críticos para o catálogo.

Formato esperado do arquivo de entrada (TXT):
Nome original|Safra|Região|Uva|Preço|Notas de Cata (sommelier simples)|Card Críticos
...

Observações:
- Aceita linhas com pipes extras no bloco de críticos.
- Ignora críticos sem pontuação (N/A, NA, sem número).
- Faz match principal por (descrição normalizada + safra), com fallback por descrição.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "bodega_webapp.json"
DEFAULT_INPUT = ROOT / "reports" / "cata_lote_01.txt"
DEFAULT_REPORT_JSON = ROOT / "reports" / "cata_import_report.json"
DEFAULT_REPORT_CSV = ROOT / "reports" / "cata_import_unmatched.csv"


CRITIC_PATTERN = re.compile(
    r"(?:^|\|)\s*(JS|WA|TA|PEÑ[IÍ]N|PENIN|WS|VM|DECANTER)\s*:\s*([0-9]{2,3}(?:[.,][0-9]+)?\+?)",
    flags=re.IGNORECASE,
)


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_name(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s*-\s*$", "", text)  # remove hífen pendente final
    return normalize_text(text)


def canonical_critic_label(value: str) -> str:
    key = normalize_text(value).replace(" ", "")
    mapping = {
        "js": "JS",
        "wa": "WA",
        "ta": "TA",
        "penin": "Peñín",
        "penin": "Peñín",
        "ws": "WS",
        "vm": "VM",
        "decanter": "Decanter",
    }
    return mapping.get(key, value.strip() or "Crítico")


def extract_critics(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not raw:
        return out
    text = raw.strip()
    if re.search(r"\b(n/?a|na)\b", text, flags=re.IGNORECASE) and not re.search(r"\d{2,3}", text):
        return out
    for match in CRITIC_PATTERN.finditer(text):
        label = canonical_critic_label(match.group(1))
        score = match.group(2).replace(",", ".").strip()
        if not score:
            continue
        out[label] = score
    return out


def parse_line(raw_line: str) -> dict[str, str] | None:
    line = raw_line.strip()
    if not line:
        return None
    if line.lower().startswith("nome original|"):
        return None

    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 6:
        return None

    name = parts[0]
    year = parts[1]
    region = parts[2]
    grape = parts[3]
    rest = parts[4:]

    # Encontrar início da nota de cata (normalmente "Nariz:")
    cata_start = None
    for idx, token in enumerate(rest):
        if re.search(r"\bnariz\b\s*:", token, flags=re.IGNORECASE):
            cata_start = idx
            break
    if cata_start is None:
        for idx, token in enumerate(rest):
            if re.search(r"\bboca\b\s*:", token, flags=re.IGNORECASE):
                cata_start = idx
                break
    if cata_start is None:
        cata_start = 1 if len(rest) > 1 else 0

    pre_cata = rest[:cata_start]
    cata_and_critics = "|".join(rest[cata_start:]).strip()

    # Preço: último token antes da cata que tenha € ou R$
    price = ""
    for token in reversed(pre_cata):
        if "€" in token or "R$" in token or re.search(r"\b\d+[.,]?\d*\s*eur\b", token, re.I):
            price = token.strip()
            break
    if not price and pre_cata:
        price = pre_cata[-1].strip()

    # Split cata x críticos (quando há bloco JS/WA/...)
    critics_match = CRITIC_PATTERN.search(cata_and_critics)
    if critics_match:
        cata = cata_and_critics[: critics_match.start()].strip(" |")
        critics_raw = cata_and_critics[critics_match.start() :].strip(" |")
    else:
        cata = cata_and_critics.strip(" |")
        critics_raw = ""

    return {
        "name": name,
        "year": year,
        "region": region,
        "grape": grape,
        "price": price,
        "cata": cata,
        "critics_raw": critics_raw,
    }


def load_input(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            parsed = parse_line(raw)
            if parsed:
                rows.append(parsed)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Importar notas de cata para catálogo.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-csv", type=Path, default=DEFAULT_REPORT_CSV)
    parser.add_argument("--write", action="store_true", help="Persistir mudanças no catálogo.")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Arquivo de entrada não encontrado: {args.input}")

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    input_rows = load_input(args.input)

    by_name_year: dict[tuple[str, str], list[dict[str, Any]]] = {}
    by_name_only: dict[str, list[dict[str, Any]]] = {}
    for wine in catalog:
        desc = normalize_name(wine.get("descripcion"))
        year = str(wine.get("ano") or "").strip()
        by_name_year.setdefault((desc, year), []).append(wine)
        by_name_only.setdefault(desc, []).append(wine)

    matched = 0
    updated = 0
    unmatched: list[dict[str, str]] = []
    touched_pods: list[str] = []

    for row in input_rows:
        key_name = normalize_name(row["name"])
        key_year = str(row["year"] or "").strip()

        candidates = by_name_year.get((key_name, key_year), [])
        if not candidates:
            fallback = by_name_only.get(key_name, [])
            if len(fallback) == 1:
                candidates = fallback

        if not candidates:
            unmatched.append(row)
            continue

        # Desempate por região quando necessário
        chosen = candidates[0]
        if len(candidates) > 1:
            reg = normalize_text(row["region"])
            regional = [w for w in candidates if normalize_text(w.get("region")) == reg]
            if len(regional) == 1:
                chosen = regional[0]

        matched += 1
        critics = extract_critics(row.get("critics_raw", ""))
        changed = False

        cata_text = (row.get("cata") or "").strip()
        if cata_text and cata_text != "—":
            if chosen.get("nota_cata") != cata_text:
                chosen["nota_cata"] = cata_text
                changed = True

        if critics:
            if chosen.get("card_criticos") != critics:
                chosen["card_criticos"] = critics
                changed = True

        if changed:
            updated += 1
            pod = str(chosen.get("pod") or "").strip()
            if pod:
                touched_pods.append(pod)

    report = {
        "input_file": str(args.input),
        "catalog_file": str(args.catalog),
        "rows_input": len(input_rows),
        "matched": matched,
        "updated": updated,
        "unmatched": len(unmatched),
        "touched_pods_count": len(set(touched_pods)),
        "touched_pods_preview": sorted(set(touched_pods))[:60],
    }

    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with args.report_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["name", "year", "region", "grape", "price", "cata", "critics_raw"],
        )
        writer.writeheader()
        for row in unmatched:
            writer.writerow(row)

    if args.write:
        args.catalog.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"report_json={args.report_json}")
    print(f"report_csv={args.report_csv}")
    if args.write:
        print("catalog_write=done")
    else:
        print("catalog_write=dry_run")


if __name__ == "__main__":
    main()
