# Cava Metropolis — Architecture

## Overview
Single-page PWA for managing a multi-establishment wine cellar. Static frontend served via Vercel, with offline-first capabilities.

## Project Structure
```
cava-metropolis/
  index.html          # Main SPA (HTML + CSS + JS in single file)
  manifest.json       # PWA manifest
  sw.js               # Service worker (network-first + cache fallback)
  icon-192.png        # PWA icon 192x192
  icon-512.png        # PWA icon 512x512
  data/
    bodega_webapp.json # Wine reference data (2069 entries)
  docs/
    ROADMAP.md         # Project phases
  ARCHITECTURE.md      # This file
  .gitignore
```

## Data Model (`bodega_webapp.json`)
Each wine reference contains:
| Field | Type | Description |
|-------|------|-------------|
| `pod` | string | Primary key (e.g. "POD016918") |
| `descripcion` | string | Wine name/description |
| `pais` | string | Country of origin |
| `region` | string | Wine region / D.O. |
| `bodega` | string | Winery name |
| `ano` | number\|null | Vintage year |
| `tipo` | `{codigo, nombre}` | Wine type (TO/BL/ROS/ESP/GEN/DU) |
| `formato` | `{cl, ml, etiqueta}` | Bottle format |
| `uvas` | string[] | Grape varieties |
| `uvas_confianza` | string | Confidence level of grape data |
| `bodega_general` | `{unidades, localizacion}` | General cellar info |
| `establecimientos` | object | Per-establishment data |

### Establishments
Each establishment entry (`spa`, `tasca_fina`, `victoria`, `galeria`) contains:
- `pvp`: Sale price (number | null)
- `unidades`: Stock count (number | null)
- `localizacion`: Physical location in cellar (string | null)

**Note:** `galeria` data exists in JSON but is NOT rendered in the UI (Phase 3).

## Frontend Architecture

### Pre-Processing (computed once on load)
- `searchIndex[]` — Flattened, accent-stripped search strings per reference
- `pvpMedio{}` — Average price across visible establishments (spa, tasca_fina, victoria)
- `subsets{}` — Sets of indices per establishment for fast filtering

### Filtering & Sorting
- **Filters:** TODOS | SPA | TASCA FINA | VICTORIA (pill buttons)
- **Sort:** ABC (alphabetical) | PVP (price ascending)
- Search uses `removeAccents()` + 150ms debounce

### Edit Persistence
- Edits stored in `localStorage` key `cava_edits`
- Format: `Array<{pod, path, value}>` where `path` is dot-notation (e.g. `establecimientos.spa.pvp`)
- Applied on top of fetched JSON on every load
- **TODO:** Replace with API calls in Phase 2

### Kept Systems
- Gold particle canvas animation
- Dark/Light theme toggle with canvas animation
- Multi-language (ES/EN/PT) with typewriter placeholder effect
- Grape family color system (GRAPE_FAMILIES map)
- Glassmorphism UI pattern
- Mobile keyboard detection (visualViewport API)
- PWA (manifest + service worker)
