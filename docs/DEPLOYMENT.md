# 🚀 Checklist de Deployment - Vercel

## ✅ Preparación Completada

- [x] Logo "STOCK Cava" configurado
- [x] Todos los íconos PWA generados (15 archivos)
- [x] manifest.json actualizado con 8 íconos
- [x] index.html con meta tags iOS completos
- [x] favicon.ico multi-tamaño creado
- [x] vercel.json configurado (rutas, headers, caché)
- [x] .gitignore actualizado
- [x] README.md con documentación completa
- [x] package.json creado
- [x] Íconos viejos eliminados del root
- [x] Todos los archivos JSON validados

## 📋 Deploy en Vercel - Paso a Paso

### Método 1: Con GitHub (Recomendado) ⭐

```bash
# 1. Commitear todos los cambios
git add .
git commit -m "feat: PWA completa con logo STOCK Cava y todos los íconos"

# 2. (Si no tienes repo remoto) Crear en GitHub y conectar
git remote add origin https://github.com/TU_USUARIO/cava-metropolis.git
git push -u origin main

# 3. Ir a Vercel y conectar
# https://vercel.com/new
# - New Project
# - Import Git Repository
# - Seleccionar tu repo
# - Deploy (Vercel detecta todo automáticamente)
```

### Método 2: Con Vercel CLI ⚡

```bash
# 1. Instalar Vercel CLI (solo la primera vez)
npm i -g vercel

# 2. Login
vercel login

# 3. Deploy
vercel

# 4. Para producción
vercel --prod
```

## 🔍 Verificación Post-Deploy

Una vez deployado en Vercel:

### 1. Verificar PWA
- [ ] Abrir la URL en Chrome (escritorio)
- [ ] Abrir DevTools > Application > Manifest
- [ ] Verificar que todos los íconos carguen
- [ ] Verificar Service Worker esté registrado

### 2. Probar instalación móvil

**Android:**
- [ ] Abrir en Chrome móvil
- [ ] Debería aparecer banner de "Añadir a pantalla de inicio"
- [ ] Instalar y verificar ícono

**iOS:**
- [ ] Abrir en Safari
- [ ] Compartir → "Añadir a pantalla de inicio"
- [ ] Verificar ícono y nombre

### 3. Verificar Performance
- [ ] Google PageSpeed Insights
- [ ] PWA score en Lighthouse
- [ ] Verificar HTTPS activo

## 🎨 URLs de Vercel

Después del deploy tendrás:

- **Preview:** `cava-metropolis-xxx.vercel.app`
- **Producción:** `cava-metropolis.vercel.app`
- **Dominio custom:** Configurable en Vercel dashboard

## 🔧 Configuración Post-Deploy

### Dominio personalizado
1. Vercel Dashboard > Settings > Domains
2. Añadir dominio: `tudominio.com`
3. Configurar DNS según instrucciones

### Variables de entorno (si necesitas)
1. Vercel Dashboard > Settings > Environment Variables
2. Añadir claves API, etc.

### Analytics
Vercel ofrece analytics gratis:
1. Settings > Analytics > Enable

## 🐛 Troubleshooting

### "Build Failed"
- Verifica que vercel.json sea JSON válido
- Asegúrate de no tener errores en HTML/CSS

### "Service Worker no funciona"
- Vercel sirve automáticamente con HTTPS ✅
- Verifica headers en vercel.json
- Limpia caché del navegador

### "Los íconos no aparecen"
- Verifica rutas en manifest.json
- Asegúrate de que imgs/ esté en el repo
- Hard refresh (Cmd/Ctrl + Shift + R)

## 📝 Comandos Útiles

```bash
# Ver cambios sin commitear
git status

# Ver logs de Vercel
vercel logs

# Remover deployment
vercel remove [deployment-url]

# Ver lista de deployments
vercel ls

# Verificar configuración local
python3 check_deployment.py
```

## 🎯 Estado Actual

```
✅ Proyecto completamente preparado para Vercel
✅ 15 íconos PWA generados y optimizados
✅ Service Worker configurado
✅ Manifest válido
✅ Headers de seguridad configurados
✅ Caché optimizado
✅ Responsive y mobile-first
```

## 📞 Soporte

- Vercel Docs: https://vercel.com/docs
- Vercel Discord: https://vercel.com/discord
- PWA Docs: https://web.dev/progressive-web-apps/

---

**¡Listo para lanzar! 🚀**
