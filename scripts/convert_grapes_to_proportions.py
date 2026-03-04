"""
Converte estrutura de uvas de simples array para array com proporções
Antes: ["Tempranillo", "Garnacha", "Graciano"]
Depois: [
  {"nome": "Tempranillo", "pct": null, "confianza": "alta"},
  {"nome": "Garnacha", "pct": null, "confianza": "alta"},
  {"nome": "Graciano", "pct": null, "confianza": "alta"}
]
"""

import json
import time

with open('data/bodega_webapp.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

converted = 0

for wine in data:
    uvas_old = wine.get('uvas', [])
    uvas_confianza = wine.get('uvas_confianza', 'alta')
    
    # Se já está no novo formato (é um dict dentro de array)
    if uvas_old and isinstance(uvas_old[0], dict):
        continue
    
    # Converter de array de strings para array de objects
    uvas_new = []
    if uvas_old:
        for uva_name in uvas_old:
            uvas_new.append({
                "nome": uva_name,
                "pct": None,  # Será preenchido depois
                "confianza": uvas_confianza
            })
    
    wine['uvas'] = uvas_new
    converted += 1

# Salvar
with open('data/bodega_webapp.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✓ Convertidos {converted} registros")
print(f"✓ Nova estrutura com proporções implementada")
