#!/usr/bin/env python3
"""
Aplica curadoria round 2 no dossiê CSV da BODEGA -2.
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "reports" / "bodega_minus2_dossier_one_by_one_curated.csv"
CONFIG_JSON = ROOT / "config" / "bodega_minus2_round2_curation.json"
OUTPUT_CSV = ROOT / "reports" / "bodega_minus2_dossier_one_by_one_curated_v2.csv"
OUTPUT_DATA_CSV = ROOT / "data" / "vinhos_para_analise_bodega_minus2_curado_v2.csv"
REPORT_JSON = ROOT / "reports" / "bodega_minus2_round2_curation_report.json"


def normalize(value: str) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("—", "-").replace("–", "-")
    text = re.sub(r"[’']", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def key(source_file: str, producer: str, item: str, ano_raw: str) -> tuple[str, str, str, str]:
    return (
        normalize(source_file),
        normalize(producer),
        normalize(item),
        normalize(ano_raw),
    )


def merge_origin(existing: str, new: str) -> str:
    existing = (existing or "").strip()
    if not existing:
        return new
    parts = [p.strip() for p in existing.split("|") if p.strip()]
    if new not in parts:
        parts.append(new)
    return " | ".join(parts)


def main() -> None:
    rows = list(csv.DictReader(INPUT_CSV.open("r", encoding="utf-8")))
    config = json.load(CONFIG_JSON.open("r", encoding="utf-8"))
    origin = config.get("origin", "usuario_round2")
    entries = config.get("entries", [])

    by_key = {}
    for entry in entries:
        by_key[key(entry["source_file"], entry["producer"], entry["item"], entry["ano_raw"])] = entry

    matched_keys = set()
    updated_rows = 0

    for row in rows:
        k = key(
            row.get("source_file", ""),
            row.get("producer", ""),
            row.get("item", ""),
            row.get("ano_raw", ""),
        )
        entry = by_key.get(k)
        if not entry:
            continue

        matched_keys.add(k)
        updated_rows += 1

        row["tipo_sugerido"] = entry.get("tipo_sugerido", row.get("tipo_sugerido", ""))
        row["uva_sugerida"] = entry.get("uva_sugerida", row.get("uva_sugerida", ""))
        row["region_sugerida"] = entry.get("region_sugerida", row.get("region_sugerida", ""))
        row["pais_sugerido"] = entry.get("pais_sugerido", row.get("pais_sugerido", ""))

        if not row.get("clima_sugerido"):
            row["clima_sugerido"] = "Usar mapeamento atual da região no app."
        if not row.get("suelo_sugerido"):
            row["suelo_sugerido"] = "Usar mapeamento atual da região no app."

        row["curadoria_origem"] = merge_origin(row.get("curadoria_origem", ""), origin)
        note = row.get("curadoria_nota", "").strip()
        new_note = entry.get("curadoria_nota", "").strip()
        if new_note:
            row["curadoria_nota"] = new_note
        elif not note:
            row["curadoria_nota"] = "Curadoria manual round 2 aplicada."

    missing_entries = []
    for entry in entries:
        k = key(entry["source_file"], entry["producer"], entry["item"], entry["ano_raw"])
        if k not in matched_keys:
            missing_entries.append(entry)

    headers = list(rows[0].keys()) if rows else []
    for h in ("curadoria_origem", "curadoria_nota"):
        if h not in headers:
            headers.append(h)

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    with OUTPUT_DATA_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_rows": len(rows),
        "config_entries": len(entries),
        "updated_rows": updated_rows,
        "matched_entries": len(matched_keys),
        "missing_entries": missing_entries,
        "output_csv": str(OUTPUT_CSV),
        "output_data_csv": str(OUTPUT_DATA_CSV),
    }
    with REPORT_JSON.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"input_rows={len(rows)}")
    print(f"config_entries={len(entries)}")
    print(f"updated_rows={updated_rows}")
    print(f"matched_entries={len(matched_keys)}")
    print(f"missing_entries={len(missing_entries)}")
    print(f"output_csv={OUTPUT_CSV}")
    print(f"output_data_csv={OUTPUT_DATA_CSV}")
    print(f"report={REPORT_JSON}")


if __name__ == "__main__":
    main()
