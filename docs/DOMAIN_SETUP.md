# 🌐 Configuración de Dominio stockcava.com en Vercel

## 📋 Preparación completada

✅ Branding actualizado a "STOCK Cava"  
✅ SEO optimizado (meta tags, Open Graph, Twitter Card)  
✅ PWA configurada para stockcava.com  
✅ Manifest actualizado  
✅ Todos los íconos generados  

## 🚀 Pasos para Deploy en Vercel

### 1️⃣ Preparar Git

```bash
# Añadir todos los cambios
git add .

# Commit con descripción clara
git commit -m "feat: Deploy production ready - STOCK Cava con SEO optimizado"

# Push a GitHub
git push origin main
```

### 2️⃣ Deploy en Vercel

**Opción A: Conectar con GitHub (Recomendado)**

1. Ve a [vercel.com](https://vercel.com)
2. Login con GitHub
3. Click "Add New..." → "Project"
4. Importa tu repositorio `cava-metropolis`
5. Configuration (dejar por defecto):
   - Framework Preset: `Other`
   - Build Command: (vacío)
   - Output Directory: (vacío)
   - Install Command: (vacío)
6. Click "Deploy"
7. ¡Listo! Vercel te dará una URL temporal

**Opción B: Vercel CLI**

```bash
# Instalar CLI (solo primera vez)
npm i -g vercel

# Deploy
vercel

# Cuando te pida:
# - Set up and deploy? Y
# - Which scope? (tu cuenta)
# - Link to existing project? N
# - What's your project's name? stock-cava
# - In which directory? ./
# - Want to override settings? N

# Deploy a producción
vercel --prod
```

### 3️⃣ Configurar Dominio Personalizado stockcava.com

Una vez deployado:

1. **En Vercel Dashboard:**
   - Ve a tu proyecto → Settings → Domains
   - Click "Add Domain"
   - Escribe: `stockcava.com`
   - También añade: `www.stockcava.com`

2. **Configurar DNS (en tu proveedor de dominios):**

   Vercel te mostrará los registros DNS necesarios. Típicamente:

   **Para stockcava.com:**
   ```
   Tipo: A
   Nombre: @
   Valor: 76.76.21.21
   ```

   **Para www.stockcava.com:**
   ```
   Tipo: CNAME
   Nombre: www
   Valor: cname.vercel-dns.com
   ```

3. **Espera la propagación:**
   - DNS puede tardar de minutos a 48 horas
   - Vercel verificará automáticamente
   - Cuando esté listo, verás "Valid Configuration" ✓

### 4️⃣ Configurar SSL (Automático)

Vercel automáticamente:
- ✅ Genera certificado SSL/TLS (Let's Encrypt)
- ✅ Fuerza HTTPS
- ✅ Redirecciona www → sin www (o viceversa, configurable)

## 🎯 URLs Finales

Después de la configuración:

- **Producción:** https://stockcava.com
- **Con www:** https://www.stockcava.com (redirige a stockcava.com)
- **Vercel URL:** https://stock-cava.vercel.app (backup)

## ✅ Checklist Post-Deploy

Después del deploy, verifica:

- [ ] stockcava.com carga correctamente
- [ ] HTTPS funciona (candado verde)
- [ ] "STOCK Cava" aparece en el título
- [ ] Logo "STOCK Cava" visible encima de METROPOLIS
- [ ] PWA instalable en móvil
- [ ] Service Worker activo (DevTools > Application)
- [ ] Todos los íconos cargan
- [ ] Búsqueda funciona
- [ ] Filtros (SPA, TASCA FINA, VICTORIA) funcionan
- [ ] Modo claro/oscuro funciona
- [ ] Multi-idioma funciona

## 🔧 Configuraciones Adicionales en Vercel

### Redirects (Opcional)

Si quieres que www → sin www:
1. Settings → Domains
2. Click en www.stockcava.com
3. Marca "Redirect to stockcava.com"

### Environment Variables (Si necesitas)

Settings → Environment Variables
- Aquí puedes añadir API keys si en el futuro las necesitas

### Analytics

Settings → Analytics → Enable
- Analytics gratuito de Vercel

## 🐛 Troubleshooting

### DNS no propaga
- Usar: https://dnschecker.org/
- Esperar hasta 48h (normal: 1-2 horas)
- Verificar que los registros estén correctos en tu proveedor

### "Domain is not configured"
- Verifica que el dominio esté verificado en Vercel
- Revisa los registros DNS en tu proveedor
- Espera unos minutos y recarga

### Service Worker no actualiza
- En producción, limpia caché del navegador
- Hard reload: Cmd/Ctrl + Shift + R
- O en DevTools: Application > Service Workers > Unregister

## 📱 Probar PWA en Móvil

### Android:
1. Abre https://stockcava.com en Chrome
2. Verás banner "Añadir a pantalla de inicio"
3. O: Menú (⋮) → "Instalar app"
4. El ícono aparecerá en tu pantalla

### iOS:
1. Abre https://stockcava.com en Safari
2. Botón compartir (□↑)
3. "Añadir a pantalla de inicio"
4. El ícono "STOCK Cava" aparecerá

## 📊 Monitoring

Vercel Dashboard te da:
- **Analytics:** Visitas, páginas vistas
- **Logs:** Errores y accesos
- **Deployment History:** Todos tus deploys
- **Preview Deployments:** Cada push genera preview

## 🎨 Performance

Tu sitio es estático HTML, tendrás:
- ⚡ 100/100 en Lighthouse Performance
- ⚡ Carga instantánea
- ⚡ CDN global de Vercel
- ⚡ Compresión automática (Brotli/Gzip)

---

## 📞 Soporte

- **Vercel Docs:** https://vercel.com/docs
- **Vercel Support:** support@vercel.com
- **Community:** https://github.com/vercel/vercel/discussions

---

**¡Tu PWA STOCK Cava está lista para producción! 🚀**
