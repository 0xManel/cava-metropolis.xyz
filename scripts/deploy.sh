#!/bin/bash

# 🚀 Script de Deploy para stockcava.com

echo "🍷 STOCK Cava - Deployment Script"
echo "=================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "index.html" ]; then
    echo "❌ Error: Ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

# Verificar Python
echo "🔍 Verificando configuración..."
if command -v python3 &> /dev/null; then
    python3 scripts/check_deployment.py
else
    echo "⚠️  Python3 no encontrado, saltando verificación"
fi

echo ""
echo "📦 Preparando deployment..."

# Git status
echo ""
echo "📊 Estado de Git:"
git status --short

echo ""
echo "🎯 ¿Quieres hacer commit y push? (y/n)"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo ""
    echo "📝 Mensaje de commit:"
    read -r commit_msg
    
    if [ -z "$commit_msg" ]; then
        commit_msg="deploy: Production ready for stockcava.com"
    fi
    
    echo ""
    echo "🔄 Haciendo commit..."
    git add .
    git commit -m "$commit_msg"
    
    echo ""
    echo "📤 Haciendo push..."
    git push
    
    echo ""
    echo "✅ ¡Git actualizado!"
    echo ""
    echo "🌐 Próximos pasos para stockcava.com:"
    echo "   1. Ve a https://vercel.com/new"
    echo "   2. Importa tu repositorio"
    echo "   3. Deploy automático"
    echo "   4. Configura dominio stockcava.com en Settings → Domains"
    echo ""
    echo "📖 Guía completa: docs/DOMAIN_SETUP.md"
else
    echo ""
    echo "ℹ️  Deploy cancelado. Puedes hacerlo manualmente:"
    echo "   git add ."
    echo "   git commit -m 'deploy: Production ready'"
    echo "   git push"
fi

echo ""
echo "✨ Listo para stockcava.com!"
