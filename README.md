# 🍷 STOCK Cava — Cava Metropolis

Aplicación web progresiva (PWA) para gestión de carta de vinos multi-establecimiento.

## 🚀 Características

- ✨ PWA instalable en Android/iOS
- 🔍 Búsqueda rápida de referencias
- 📱 Diseño responsivo con glassmorphism
- 🌐 Multi-idioma (ES/EN/PT)
- 🎨 Modo claro/oscuro
- 📊 Gestión de establecimientos (SPA, Tasca Fina, Victoria)
- 💾 Funciona offline con Service Worker

## 📦 Estructura del Proyecto

```
cava-metropolis/
├── 📱 Aplicación PWA (root)
│   ├── index.html          # Aplicación principal
│   ├── manifest.json       # Configuración PWA
│   ├── sw.js              # Service Worker
│   ├── favicon.ico        # Favicon
│   ├── vercel.json        # Deploy config
│   └── package.json       # Metadata
│
├── 📁 data/               # Base de datos
│   └── bodega_webapp.json # Catálogo de vinos
│
├── 🖼️ imgs/               # Recursos visuales
│   ├── icon-*.png         # PWA icons (72-512px)
│   ├── apple-touch-icon*.png # iOS icons
│   ├── favicon-*.png      # Favicons
│   ├── banner.svg         # Banner
│   └── logo_original.png  # Logo fuente
│
├── 🛠️ scripts/            # Scripts de desarrollo
│   ├── server.py          # Servidor local
│   ├── generate_icons.py  # Generador de íconos
│   ├── verify_pwa.py      # Validador PWA
│   └── check_deployment.py # Verificador pre-deploy
│
├── 📚 docs/               # Documentación
│   ├── ARCHITECTURE.md    # Arquitectura técnica
│   ├── DEPLOYMENT.md      # Guía de deployment
│   └── ROADMAP.md         # Roadmap del proyecto
│
├── ⚙️ config/             # Configuraciones
│   └── plantas.config.json # Config establecimientos
│
└── 🗑️ temp/               # Temporales (ignorado en Git)
    └── *.bak, *.xlsx, etc.
```

## 🔧 Deploy en Vercel

### Opción 1: Deploy con Git (Recomendado)

1. **Sube el proyecto a GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/tu-usuario/cava-metropolis.git
   git push -u origin main
   ```

2. **Conecta con Vercel:**
   - Ve a [vercel.com](https://vercel.com)
   - Haz clic en "New Project"
   - Importa tu repositorio de GitHub
   - Vercel detectará automáticamente la configuración
   - Haz clic en "Deploy"

### Opción 2: Deploy con Vercel CLI

1. **Instala Vercel CLI:**
   ```bash
   npm i -g vercel
   ```

2. **Deploy:**
   ```bash
   cd /ruta/a/cava-metropolis
   vercel
   ```

3. **Para producción:**
   ```bash
   vercel --prod
   ```

## 🛠️ Desarrollo Local

```bash
# Opción 1: Servidor de desarrollo incluido
python3 scripts/server.py

# Opción 2: Python simple
python3 -m http.server 8000

# Opción 3: Node.js
npx serve
```

Abre en el navegador: `http://localhost:8000`

## 📱 Instalación como PWA

### Android (Chrome):
1. Abre la URL de la app
2. Toca el menú (⋮) → "Añadir a pantalla de inicio"
3. O verás un banner de instalación automático

### iOS (Safari):
1. Abre la URL de la app
2. Toca el botón de compartir (□↑)
3. "Añadir a pantalla de inicio"

## 🎨 Personalización

### Cambiar colores del tema

Edita las variables CSS en [index.html](index.html):

```css
:root {
    --bg-color: #08080b;
    --gold-accent: #D4AF37;
    --text-main: #FDFBF7;
    /* ... */
}
```

### Actualizar datos de vinos

Modifica [data/bodega_webapp.json](data/bodega_webapp.json):

```json
{
  "referencias": [
    {
      "ref": "V001",
      "nombre": "Vino Ejemplo",
      "precio": 25.00,
      "disponibilidad": {
        "spa": true,
        "tasca_fina": false,
        "victoria": true
      }
    }
  ]
}
```

## 🔒 Configuración de Seguridad

El archivo `vercel.json` incluye:
- Headers de seguridad (CSP, XSS Protection)
- Configuración de caché optimizada
- Service Worker habilitado
- HTTPS forzado

## 📝 Tecnologías

- HTML5 + CSS3 (Vanilla)
- JavaScript ES6+
- Service Worker API
- Web Manifest
- Glassmorphism Design

## 🌐 Dominios Personalizados

En Vercel:
1. Ve a "Settings" → "Domains"
2. Añade tu dominio
3. Configura los DNS según las instrucciones

## 📊 Analytics

Para añadir analytics, inserta antes del `</head>` en [index.html](index.html):

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

## 🐛 Troubleshooting

### La PWA no se instala
- Verifica que estés en HTTPS
- Revisa que `manifest.json` sea válido
- Asegúrate de que el Service Worker se registre correctamente

### Los íconos no aparecen
- Verifica que las rutas en `manifest.json` sean correctas
- Limpia la caché del navegador
- Verifica que los archivos existan en `imgs/`

### Los cambios no se reflejan
- Desregistra el Service Worker en DevTools
- Limpia caché y recarga hard (Cmd/Ctrl + Shift + R)
- Incrementa la versión del caché en `sw.js`

## 📄 Licencia

Proyecto privado - © 2026 Cava Metropolis

---

**Deploy Status:** [![Vercel](https://img.shields.io/badge/vercel-deployed-success)](https://vercel.com)

Para soporte: [contacto@cavametropolis.com](mailto:contacto@cavametropolis.com)
