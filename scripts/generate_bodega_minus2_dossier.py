#!/usr/bin/env python3
"""
Gera dossiê 1-por-1 para revisão de vinhos pendentes da BODEGA -2.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_PATH = ROOT / "reports" / "bodega_minus2_pending_wines_analysis.json"
ALIAS_PATH = ROOT / "config" / "bodega_minus2_manual_aliases.json"
OUT_MD = ROOT / "reports" / "bodega_minus2_dossier_one_by_one.md"
OUT_CSV = ROOT / "reports" / "bodega_minus2_dossier_one_by_one.csv"


def alias_key(source_file: str, producer: str, item: str, ano_raw: str) -> tuple[str, str, str, str]:
    return (
        str(source_file or "").strip(),
        str(producer or "").strip(),
        str(item or "").strip(),
        str(ano_raw or "").strip(),
    )


def main() -> None:
    analysis_doc = json.load(ANALYSIS_PATH.open("r", encoding="utf-8"))
    aliases_doc = json.load(ALIAS_PATH.open("r", encoding="utf-8"))

    resolved_aliases = {
        alias_key(
            a.get("source_file"),
            a.get("producer"),
            a.get("item"),
            a.get("ano_raw"),
        ): a
        for a in aliases_doc.get("aliases", [])
    }

    unresolved = []
    for row in analysis_doc.get("data", []):
        key = alias_key(row["source_file"], row["producer"], row["item"], row["ano_raw"])
        if key in resolved_aliases:
            continue
        unresolved.append(row)

    grouped = defaultdict(list)
    for row in unresolved:
        grouped[row["source_file"]].append(row)

    for source_file in grouped:
        grouped[source_file].sort(
            key=lambda r: (r["status"], r["producer"], r["item"], str(r["ano_raw"]))
        )

    # CSV
    headers = [
        "source_file",
        "status",
        "producer",
        "item",
        "ano_raw",
        "qty_total",
        "locations",
        "best_pod",
        "best_descripcion",
        "best_score",
        "best_margin",
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
        for src in sorted(grouped):
            for row in grouped[src]:
                out = dict(row)
                out["locations"] = " / ".join(row["locations"]) if row["locations"] else ""
                writer.writerow({k: out.get(k, "") for k in headers})

    # Markdown
    lines = []
    lines.append("# Dossier BODEGA -2 (Revisao 1 por 1)")
    lines.append("")
    lines.append(f"- Gerado em: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Total pendentes para revisao: {len(unresolved)}")
    status_counts = defaultdict(int)
    for row in unresolved:
        status_counts[row["status"]] += 1
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")
    lines.append("")
    lines.append("## Legenda")
    lines.append("- `provavel_vinho_novo`: criar ficha nova no catálogo.")
    lines.append("- `revisao_manual_obrigatoria`: provável correspondente existente, confirmar POD antes de aplicar.")
    lines.append("")

    idx = 1
    for src in sorted(grouped):
        lines.append(f"## {src}")
        lines.append("")
        for row in grouped[src]:
            lines.append(f"### {idx}. {row['producer']} | {row['item']} | {row['ano_raw']}")
            lines.append(f"- Status: `{row['status']}`")
            lines.append(f"- Qtd total CSV: `{row['qty_total']}`")
            lines.append(f"- Localizações: `{ ' / '.join(row['locations']) if row['locations'] else '—' }`")
            lines.append(
                f"- Melhor POD sugerido: `{row['best_pod'] or '—'}` | score `{row['best_score']}` | margem `{row['best_margin']}`"
            )
            lines.append(
                f"- Métricas de match: item `{row.get('best_item_similarity', '—')}` | produtor `{row.get('best_producer_score', '—')}` | delta ano `{row.get('best_year_delta', '—')}`"
            )
            lines.append(f"- Melhor descrição sugerida: `{row['best_descripcion'] or '—'}`")
            lines.append(
                f"- Sugestão de ficha: país `{row['pais_sugerido'] or '—'}` | região `{row['region_sugerida'] or '—'}` | tipo `{row['tipo_sugerido'] or '—'}` | uva `{row['uva_sugerida'] or '—'}`"
            )
            lines.append(f"- Clima sugerido: {row['clima_sugerido'] or '—'}")
            lines.append(f"- Suelo sugerido: {row['suelo_sugerido'] or '—'}")
            lines.append("- Decisão: [ ] confirmar POD existente  [ ] criar vinho novo")
            lines.append("")
            idx += 1

    with OUT_MD.open("w", encoding="utf-8") as file:
        file.write("\n".join(lines).rstrip() + "\n")

    print(f"unresolved={len(unresolved)}")
    print(f"md={OUT_MD}")
    print(f"csv={OUT_CSV}")


if __name__ == "__main__":
    main()
