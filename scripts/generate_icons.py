#!/usr/bin/env python3
"""
Script para generar todos los íconos necesarios para PWA (Android/iOS)
"""
from PIL import Image
import os

# Imagen de entrada (deberá ser guardada primero)
input_image = "imgs/logo_original.png"

# Tamaños necesarios para PWA completa
icon_sizes = [
    # PWA Android
    (72, "icon-72.png"),
    (96, "icon-96.png"),
    (128, "icon-128.png"),
    (144, "icon-144.png"),
    (152, "icon-152.png"),
    (192, "icon-192.png"),
    (384, "icon-384.png"),
    (512, "icon-512.png"),
    
    # Apple Touch Icons
    (180, "apple-touch-icon.png"),
    (167, "apple-touch-icon-ipad.png"),
    
    # Favicon
    (32, "favicon-32x32.png"),
    (16, "favicon-16x16.png"),
]

def generate_icons():
    """Genera todos los íconos necesarios desde la imagen original"""
    
    if not os.path.exists(input_image):
        print(f"Error: No se encontró {input_image}")
        return
    
    # Abrir imagen original
    print(f"Abriendo {input_image}...")
    img = Image.open(input_image)
    
    # Convertir a RGBA si no lo está
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    print(f"Imagen original: {img.size[0]}x{img.size[1]}")
    
    # Generar cada tamaño
    for size, filename in icon_sizes:
        print(f"Generando {filename} ({size}x{size})...")
        
        # Redimensionar con alta calidad
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Guardar como PNG
        output_path = os.path.join("imgs", filename)
        resized.save(output_path, "PNG", optimize=True)
        print(f"  ✓ Guardado: {output_path}")
    
    # Generar favicon.ico (multi-tamaño)
    print("\nGenerando favicon.ico...")
    favicon_sizes = [(16, 16), (32, 32), (48, 48)]
    favicon_images = [img.resize(size, Image.Resampling.LANCZOS) for size in favicon_sizes]
    favicon_images[0].save(
        "favicon.ico",
        format="ICO",
        sizes=favicon_sizes,
        append_images=favicon_images[1:]
    )
    print("  ✓ Guardado: favicon.ico")
    
    print("\n✅ Todos los íconos generados correctamente!")

if __name__ == "__main__":
    generate_icons()
