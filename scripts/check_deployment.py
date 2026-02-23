#!/usr/bin/env python3
"""
Script de verificación pre-deployment para Vercel
"""
import os
import json

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
