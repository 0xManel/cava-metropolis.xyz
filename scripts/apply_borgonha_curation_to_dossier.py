#!/usr/bin/env python3
"""
Aplica curadoria manual da Borgonha ao dossiê de vinhos pendentes.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = ROOT / "reports" / "bodega_minus2_dossier_one_by_one.csv"
OUTPUT_CSV = ROOT / "reports" / "bodega_minus2_dossier_one_by_one_curated.csv"


def normalize(s: str) -> str:
    return (s or "").strip().lower()


def detect_tipo_uva(source_file: str, producer: str, item: str) -> tuple[str, str, str]:
    src = normalize(source_file)
    prod = normalize(producer)
    it = normalize(item)

    # Defaults by source
    if "borgoña_blancos" in src:
        tipo = "Blanco"
        uva = "Chardonnay"
    elif "borgoña_tintos" in src:
        tipo = "Tinto"
        uva = "Pinot Noir"
    else:
        return ("", "", "")

    note = ""

    # Correções explícitas do usuário
    if prod == "j. drouhin" and "clos des mouches" in it:
        tipo = "Tinto"
        uva = "Pinot Noir"
        note = "Correção manual: Clos des Mouches (versão tinta no contexto da lista)."
    if prod == "pierre morey" and it == "meursault":
        tipo = "Blanco"
        uva = "Chardonnay"
        note = "Correção manual: Meursault padrão branco."
    if prod == "chandon de briailles" and "corton clos du roi" in it:
        tipo = "Tinto"
        uva = "Pinot Noir"
        note = "Correção manual: Corton Clos du Roi Grand Cru tinto."
    if prod == "louis jadot" and "bonnes-mares" in it:
        tipo = "Tinto"
        uva = "Pinot Noir"
        note = "Correção manual: Bonnes-Mares Grand Cru tinto."
    if prod == "lucien muzard" and ("maladiere" in it or "maladière" in it):
        tipo = "Blanco"
        uva = "Chardonnay"
        note = "Mantido conforme curadoria enviada; confirmar rótulo final."

    return (tipo, uva, note)


def main() -> None:
    rows = list(csv.DictReader(INPUT_CSV.open("r", encoding="utf-8")))
    curated_count = 0

    for row in rows:
        tipo, uva, note = detect_tipo_uva(
            row.get("source_file", ""),
            row.get("producer", ""),
            row.get("item", ""),
        )
        if not tipo:
            continue

        curated_count += 1
        row["pais_sugerido"] = "França"
        row["region_sugerida"] = "Borgoña"
        row["tipo_sugerido"] = tipo
        row["uva_sugerida"] = uva
        row["clima_sugerido"] = "Continental."
        row["suelo_sugerido"] = "Calcário e marga."
        row["curadoria_origem"] = "usuario_borgonha_2026-02-26"
        row["curadoria_nota"] = note

    headers = list(rows[0].keys()) if rows else []
    if "curadoria_origem" not in headers:
        headers.append("curadoria_origem")
    if "curadoria_nota" not in headers:
        headers.append("curadoria_nota")

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"rows_total={len(rows)}")
    print(f"rows_curated_borgonha={curated_count}")
    print(f"output={OUTPUT_CSV}")


if __name__ == "__main__":
    main()
