#!/usr/bin/env python3
"""
Script para verificar que todos los recursos de PWA estén correctamente configurados
"""
import os
import json

def check_file(filepath):
    """Verifica si un archivo existe"""
    exists = os.path.exists(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {filepath}")
    return exists

def verify_pwa():
    """Verifica todos los componentes de la PWA"""
    print("🔍 Verificando configuración de PWA...\n")
    
    all_good = True
    
    # Verificar manifest.json
    print("📱 Manifest:")
    if check_file("manifest.json"):
        with open("manifest.json", "r") as f:
            manifest = json.load(f)
            print(f"   Nombre: {manifest.get('name')}")
            print(f"   Íconos: {len(manifest.get('icons', []))} configurados")
    else:
        all_good = False
    
    print("\n📱 Favicon:")
    all_good &= check_file("favicon.ico")
    all_good &= check_file("imgs/favicon-16x16.png")
    all_good &= check_file("imgs/favicon-32x32.png")
    
    print("\n📱 Apple Touch Icons:")
    all_good &= check_file("imgs/apple-touch-icon.png")
    all_good &= check_file("imgs/apple-touch-icon-ipad.png")
    
    print("\n📱 PWA Icons (Android/Chrome):")
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    for size in sizes:
        all_good &= check_file(f"imgs/icon-{size}.png")
    
    print("\n" + "="*50)
    if all_good:
        print("✅ PWA completamente configurada!")
        print("\n📝 Próximos pasos:")
        print("   1. Sube los archivos a tu servidor")
        print("   2. Asegúrate de servir con HTTPS")
        print("   3. Prueba la instalación en Android/iOS")
    else:
        print("❌ Faltan algunos archivos")
    
    return all_good

if __name__ == "__main__":
    verify_pwa()
