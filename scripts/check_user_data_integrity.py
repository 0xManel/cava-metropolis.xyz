#!/usr/bin/env python3
"""
Verifica integridade de dados críticos adicionados por usuários antes de deploy.

Checks principais:
- Estrutura e tipos de campos sensíveis em establecimientos.{pvp,unidades,localizacion}
- Possíveis perdas de dados comparando com o último backup em data/backups
- Regressões de normalização em região de Victoria (valor genérico "Victoria")
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "bodega_webapp.json"
BACKUP_DIR = ROOT / "data" / "backups"
EST_KEYS = ("spa", "tasca_fina", "victoria", "galeria", "bodega")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def as_catalog_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("wines") or []
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    return []


def latest_backup_file() -> Path | None:
    if not BACKUP_DIR.exists():
        return None
    candidates = sorted(BACKUP_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def norm_loc(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def build_by_pod(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for wine in items:
        pod = str(wine.get("pod") or "").strip()
        if not pod:
            continue
        out[pod] = wine
    return out


def validate_types(items: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for wine in items:
        pod = str(wine.get("pod") or "N/A")
        ests = wine.get("establecimientos")
        if ests is None:
            warnings.append(f"{pod}: sin 'establecimientos'")
            continue
        if not isinstance(ests, dict):
            errors.append(f"{pod}: 'establecimientos' inválido ({type(ests).__name__})")
            continue
        for key in EST_KEYS:
            est = ests.get(key)
            if est is None:
                continue
            if not isinstance(est, dict):
                errors.append(f"{pod}.{key}: bloque inválido ({type(est).__name__})")
                continue
            pvp = est.get("pvp")
            unidades = est.get("unidades")
            localizacion = est.get("localizacion")
            if pvp is not None and not is_number(pvp):
                errors.append(f"{pod}.{key}.pvp inválido ({type(pvp).__name__})")
            if unidades is not None and not (isinstance(unidades, int) and not isinstance(unidades, bool)):
                errors.append(f"{pod}.{key}.unidades inválido ({type(unidades).__name__})")
            if localizacion is not None and not isinstance(localizacion, str):
                errors.append(f"{pod}.{key}.localizacion inválida ({type(localizacion).__name__})")
    return errors, warnings


def compare_with_backup(
    current_by_pod: dict[str, dict[str, Any]],
    backup_by_pod: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str], list[str], list[str]]:
    location_losses: list[str] = []
    pvp_losses: list[str] = []
    units_losses: list[str] = []
    missing_pods: list[str] = []

    common_pods = sorted(set(current_by_pod) & set(backup_by_pod))
    for pod in common_pods:
        cur_ests = current_by_pod[pod].get("establecimientos") or {}
        bak_ests = backup_by_pod[pod].get("establecimientos") or {}
        if not isinstance(cur_ests, dict) or not isinstance(bak_ests, dict):
            continue
        for key in EST_KEYS:
            cur_est = cur_ests.get(key) if isinstance(cur_ests.get(key), dict) else {}
            bak_est = bak_ests.get(key) if isinstance(bak_ests.get(key), dict) else {}

            bak_loc = norm_loc(bak_est.get("localizacion"))
            cur_loc = norm_loc(cur_est.get("localizacion"))
            if bak_loc and not cur_loc:
                location_losses.append(f"{pod}.{key} localizacion '{bak_loc}' -> vazio")

            bak_pvp = bak_est.get("pvp")
            cur_pvp = cur_est.get("pvp")
            if bak_pvp is not None and cur_pvp is None:
                pvp_losses.append(f"{pod}.{key} pvp {bak_pvp} -> null")

            bak_units = bak_est.get("unidades")
            cur_units = cur_est.get("unidades")
            if bak_units is not None and cur_units is None:
                units_losses.append(f"{pod}.{key} unidades {bak_units} -> null")

    for pod in sorted(set(backup_by_pod) - set(current_by_pod)):
        missing_pods.append(pod)

    return location_losses, pvp_losses, units_losses, missing_pods


def main() -> int:
    print("🔒 Verificando integridade de dados de usuários...\n")

    if not CATALOG_PATH.exists():
        print(f"❌ Catálogo não encontrado: {CATALOG_PATH}")
        return 1

    current_items = as_catalog_items(load_json(CATALOG_PATH))
    current_by_pod = build_by_pod(current_items)
    print(f"📦 Catálogo atual: {len(current_items)} vinhos ({len(current_by_pod)} PODs)")

    type_errors, type_warnings = validate_types(current_items)
    if type_errors:
        print(f"❌ Erros de tipo: {len(type_errors)}")
        for row in type_errors[:20]:
            print(f"   - {row}")
        if len(type_errors) > 20:
            print(f"   ... +{len(type_errors) - 20} erros")
    else:
        print("✅ Tipos de campos críticos OK")

    if type_warnings:
        print(f"⚠️ Avisos estruturais: {len(type_warnings)}")
        for row in type_warnings[:10]:
            print(f"   - {row}")
        if len(type_warnings) > 10:
            print(f"   ... +{len(type_warnings) - 10} avisos")

    victoria_plain = [
        str(w.get("pod") or "N/A")
        for w in current_items
        if isinstance(w.get("region"), str) and w.get("region", "").strip().lower() == "victoria"
    ]
    if victoria_plain:
        print(f"❌ Região 'Victoria' genérica encontrada: {len(victoria_plain)}")
        print("   - " + ", ".join(victoria_plain[:20]))
    else:
        print("✅ Formato de região Victoria OK")

    backup_path = latest_backup_file()
    if not backup_path:
        print("⚠️ Sem backup em data/backups para comparação de perdas")
        failed = bool(type_errors or victoria_plain)
        print("\n" + ("❌" if failed else "✅") + " Resultado final: " + ("FALHOU" if failed else "OK"))
        return 1 if failed else 0

    backup_items = as_catalog_items(load_json(backup_path))
    backup_by_pod = build_by_pod(backup_items)
    print(f"🧷 Backup base: {backup_path.name} ({len(backup_items)} vinhos)")

    location_losses, pvp_losses, units_losses, missing_pods = compare_with_backup(current_by_pod, backup_by_pod)
    total_losses = len(location_losses) + len(pvp_losses) + len(units_losses) + len(missing_pods)

    if location_losses:
        print(f"❌ Perdas de localização detectadas: {len(location_losses)}")
        for row in location_losses[:20]:
            print(f"   - {row}")
        if len(location_losses) > 20:
            print(f"   ... +{len(location_losses) - 20} perdas")

    if pvp_losses:
        print(f"❌ Perdas de PVP detectadas: {len(pvp_losses)}")
        for row in pvp_losses[:20]:
            print(f"   - {row}")
        if len(pvp_losses) > 20:
            print(f"   ... +{len(pvp_losses) - 20} perdas")

    if units_losses:
        print(f"❌ Perdas de unidades detectadas: {len(units_losses)}")
        for row in units_losses[:20]:
            print(f"   - {row}")
        if len(units_losses) > 20:
            print(f"   ... +{len(units_losses) - 20} perdas")

    if missing_pods:
        print(f"❌ PODs presentes no backup e ausentes agora: {len(missing_pods)}")
        print("   - " + ", ".join(missing_pods[:20]))
        if len(missing_pods) > 20:
            print(f"   ... +{len(missing_pods) - 20} PODs")

    if total_losses == 0:
        print("✅ Sem perdas críticas de dados de usuários (vs backup)")

    failed = bool(type_errors or victoria_plain or total_losses > 0)
    print("\n" + ("❌" if failed else "✅") + " Resultado final: " + ("FALHOU" if failed else "OK"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
