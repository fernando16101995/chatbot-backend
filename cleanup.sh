#!/bin/bash

# Script para limpiar archivos innecesarios del proyecto

echo "🧹 Limpiando proyecto..."

# 1. Eliminar modelos ML entrenados (sklearn ya no se usa)
echo "Eliminando modelos sklearn..."
rm -rf models/

# 2. Eliminar scripts de entrenamiento ML
echo "Eliminando scripts de entrenamiento..."
rm -rf ml/

# 3. Eliminar dataset de Reddit
echo "Eliminando dataset..."
rm -rf datasets/

# 4. Eliminar modelo session.py (no se usa)
echo "Eliminando modelo session.py..."
rm -f app/models/session.py

# 5. Eliminar carpeta schemas vacía
echo "Eliminando carpeta schemas vacía..."
rmdir app/schemas 2>/dev/null || true

# 6. Eliminar todos los __pycache__ del proyecto (no del venv)
echo "Eliminando __pycache__ del código fuente..."
find app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 7. Eliminar archivos .pyc
echo "Eliminando archivos .pyc..."
find app -type f -name "*.pyc" -delete 2>/dev/null || true

echo "✅ Limpieza completada!"
echo ""
echo "📂 Estructura limpia:"
tree -L 2 -I 'venv|__pycache__|.git' .
