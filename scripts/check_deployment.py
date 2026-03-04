#!/usr/bin/env python3
"""
Script de verificación pre-deployment para Vercel
"""
import os
import json
import subprocess
import sys
import re

def check_file(filepath, required=True):
    """Verifica si un archivo existe"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else ("❌" if required else "⚠️")
    print(f"{status} {filepath}")
    return exists

def check_json_valid(filepath):
    """Verifica que un archivo JSON sea válido"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"   └─ JSON válido ✅")
        return True
    except json.JSONDecodeError as e:
        print(f"   └─ Error JSON: {e} ❌")
        return False
    except Exception as e:
        print(f"   └─ Error: {e} ❌")
        return False

def check_update_notice_system(index_path="index.html", sw_path="sw.js", version_path="version.json"):
    """Valida que el sistema de aviso/notas de actualización esté presente y coherente."""
    print("\n🔔 Sistema de notas de actualización:")

    if not os.path.exists(index_path):
        print(f"❌ {index_path} no existe")
        return False

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        print(f"❌ No se pudo leer {index_path}: {e}")
        return False

    required_markers = [
        'id="updateNoticeBanner"',
        'id="updateNoticeBtn"',
        'data-translate="updateBannerTitle"',
        'data-translate="updateBannerText"',
        'data-translate="updateBannerHighlightsTitle"',
        'data-translate="updateBannerBullet1"',
        'data-translate="updateBannerBullet2"',
        'data-translate="updateBannerBullet3"',
        'UPDATE_NOTICE_STORAGE_KEY',
        'APP_RELEASE_ID'
    ]

    ok = True
    for marker in required_markers:
        if marker in html:
            print(f"✅ Marker: {marker}")
        else:
            print(f"❌ Faltando marker: {marker}")
            ok = False

    translation_keys = [
        "updateBannerTitle:",
        "updateBannerText:",
        "updateBannerHighlightsTitle:",
        "updateBannerBullet1:",
        "updateBannerBullet2:",
        "updateBannerBullet3:",
        "updateBannerButton:"
    ]

    for key in translation_keys:
        occurrences = html.count(key)
        # Esperamos ES/EN/PT => 3 ocurrencias mínimas.
        if occurrences >= 3:
            print(f"✅ Traducción {key} en 3 idiomas")
        else:
            print(f"❌ Traducción incompleta para {key} (encontradas: {occurrences}, esperadas: 3)")
            ok = False

    # Verificar coherencia básica de release entre index/sw/version
    release_match = re.search(r"APP_RELEASE_ID\s*=\s*'([^']+)'", html)
    app_release_id = release_match.group(1).strip() if release_match else ""
    if app_release_id:
        print(f"✅ APP_RELEASE_ID detectado: {app_release_id}")
    else:
        print("❌ No se pudo detectar APP_RELEASE_ID en index.html")
        ok = False

    sw_build = ""
    if os.path.exists(sw_path):
        try:
            with open(sw_path, "r", encoding="utf-8") as f:
                sw_text = f.read()
            sw_match = re.search(r"SW_BUILD\s*=\s*'([^']+)'", sw_text)
            sw_build = sw_match.group(1).strip() if sw_match else ""
            if sw_build:
                print(f"✅ SW_BUILD detectado: {sw_build}")
            else:
                print("❌ No se pudo detectar SW_BUILD en sw.js")
                ok = False
        except Exception as e:
            print(f"❌ Error leyendo {sw_path}: {e}")
            ok = False
    else:
        print(f"❌ {sw_path} no existe")
        ok = False

    if os.path.exists(version_path):
        try:
            with open(version_path, "r", encoding="utf-8") as f:
                version_payload = json.load(f)
            service_worker_tag = str(version_payload.get("features", {}).get("service_worker", "")).strip()
            if service_worker_tag:
                print(f"✅ version.json service_worker: {service_worker_tag}")
            else:
                print("❌ version.json sin features.service_worker")
                ok = False

            if app_release_id and sw_build and app_release_id == sw_build:
                print("✅ APP_RELEASE_ID y SW_BUILD consistentes")
            elif app_release_id and sw_build:
                print(f"❌ APP_RELEASE_ID ({app_release_id}) y SW_BUILD ({sw_build}) no coinciden")
                ok = False

            if app_release_id and service_worker_tag:
                expected_suffix = f"stock-cava-{app_release_id}"
                if service_worker_tag == expected_suffix:
                    print("✅ version.json service_worker consistente con APP_RELEASE_ID")
                else:
                    print(f"❌ service_worker inconsistente (esperado: {expected_suffix})")
                    ok = False
        except Exception as e:
            print(f"❌ Error leyendo {version_path}: {e}")
            ok = False
    else:
        print(f"❌ {version_path} no existe")
        ok = False

    return ok

def verify_deployment():
    """Verifica que todo esté listo para deployment"""
    print("🔍 Verificando preparación para deploy en Vercel...\n")
    
    all_good = True
    
    # Archivos esenciales
    print("📄 Archivos esenciales:")
    all_good &= check_file("index.html")
    all_good &= check_file("manifest.json")
    if check_file("manifest.json"):
        all_good &= check_json_valid("manifest.json")
    
    all_good &= check_file("sw.js")
    all_good &= check_file("vercel.json")
    if check_file("vercel.json"):
        all_good &= check_json_valid("vercel.json")
    
    all_good &= check_file("data/bodega_webapp.json")
    if check_file("data/bodega_webapp.json"):
        all_good &= check_json_valid("data/bodega_webapp.json")
    
    # Favicon
    print("\n🎨 Favicon:")
    all_good &= check_file("favicon.ico")
    
    # PWA Icons
    print("\n📱 PWA Icons:")
    icon_sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    for size in icon_sizes:
        all_good &= check_file(f"imgs/icon-{size}.png")
    
    # Apple Icons
    print("\n🍎 Apple Touch Icons:")
    all_good &= check_file("imgs/apple-touch-icon.png")
    all_good &= check_file("imgs/apple-touch-icon-ipad.png")
    
    # Configuración
    print("\n⚙️ Configuración:")
    all_good &= check_file(".gitignore")
    check_file("README.md", required=False)
    
    # Verificar que no existan archivos temporales en el root
    print("\n🧹 Limpieza:")
    temp_files = ["icon-192.png", "icon-512.png"]
    clean = True
    for f in temp_files:
        if os.path.exists(f):
            print(f"⚠️  Archivo temporal encontrado: {f} (debería eliminarse)")
            clean = False
    if clean:
        print("✅ No hay archivos temporales en el root")
    
    # Verificar manifest.json
    print("\n📱 Verificación de Manifest:")
    try:
        with open("manifest.json", 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            
        print(f"   Nombre: {manifest.get('name')}")
        print(f"   Short name: {manifest.get('short_name')}")
        print(f"   Theme color: {manifest.get('theme_color')}")
        print(f"   Background color: {manifest.get('background_color')}")
        print(f"   Íconos: {len(manifest.get('icons', []))}")
        
        # Verificar que los íconos existan
        icons_valid = True
        for icon in manifest.get('icons', []):
            icon_path = icon.get('src')
            if not os.path.exists(icon_path):
                print(f"   ❌ Ícono no encontrado: {icon_path}")
                icons_valid = False
        
        if icons_valid:
            print(f"   ✅ Todos los íconos del manifest existen")
        else:
            all_good = False
            
    except Exception as e:
        print(f"   ❌ Error al verificar manifest: {e}")
        all_good = False

    # Guard de integridad de datos de usuarios
    print("\n🔒 Integridad de datos de usuarios:")
    guard_cmd = [sys.executable, "scripts/check_user_data_integrity.py"]
    guard = subprocess.run(guard_cmd, capture_output=True, text=True)
    if guard.stdout:
        print(guard.stdout.rstrip())
    if guard.stderr:
        print(guard.stderr.rstrip())
    if guard.returncode != 0:
        print("❌ Falló la validación de integridad de datos de usuarios")
        all_good = False
    else:
        print("✅ Validación de integridad de datos de usuarios OK")

    # Guard del sistema de notas de actualización (regla obligatoria)
    all_good &= check_update_notice_system()
    
    # Resultado final
    print("\n" + "="*60)
    if all_good:
        print("✅ TODO LISTO PARA DEPLOYMENT EN VERCEL!")
        print("\n📝 Próximos pasos:")
        print("   1. git add .")
        print("   2. git commit -m 'Ready for deployment'")
        print("   3. git push")
        print("   4. Conecta con Vercel: https://vercel.com/new")
        print("\n   O usa Vercel CLI:")
        print("   $ vercel")
    else:
        print("❌ Hay problemas que resolver antes del deployment")
    
    print("="*60)
    return all_good

if __name__ == "__main__":
    verify_deployment()
