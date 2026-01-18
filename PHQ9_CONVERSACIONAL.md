# Evaluación PHQ-9 Conversacional

## 🎯 ¿Qué es?

Sistema que integra las 9 preguntas del cuestionario PHQ-9 de forma **natural y conversacional** durante el chat, sin hacer las preguntas de golpe.

## 📋 ¿Cómo funciona?

### 1. Activación Automática
Cuando el sistema detecta **lenguaje depresivo** en los mensajes del usuario, automáticamente:
- ✅ Inicia una evaluación PHQ-9 conversacional en background
- ✅ Comienza a insertar preguntas de forma natural

### 2. Preguntas Espaciadas
- El bot hace **1 pregunta PHQ-9**
- Continúa con **conversación normal** (2-3 mensajes)
- Hace la **siguiente pregunta**
- Y así hasta completar las **9 preguntas**

### 3. Análisis Automático
- Cada respuesta del usuario se analiza con IA
- Se asigna un **score de 0-3** según la escala PHQ-9 estándar:
  - `0` = No presenta el síntoma
  - `1` = Varios días
  - `2` = Más de la mitad de los días
  - `3` = Casi todos los días

### 4. Resultado Final
Al completar las 9 preguntas:
- ✅ Score total (0-27)
- ✅ Severidad: minimal, mild, moderate, moderately_severe, severe
- ✅ Actualiza el `MentalHealthSummary` del usuario

---

## 🔧 Actualización de Base de Datos

**IMPORTANTE**: Debes actualizar tu base de datos para agregar la nueva tabla.

```bash
# Ejecutar el script de inicialización
python -m app.init_db
```

Esto creará la tabla: `phq9_conversational_assessments`

---

## 📡 Nuevos Endpoints

### 1. Consultar Progreso Actual
```http
GET /assessment/phq9/conversational/status
Authorization: Bearer <token>
```

**Respuesta**:
```json
{
  "has_active_assessment": true,
  "current_question": 4,
  "completed_questions": 3,
  "total_questions": 9,
  "progress_percentage": 33.3,
  "messages_since_last_question": 1,
  "started_at": "2026-01-18T10:30:00"
}
```

### 2. Historial de Evaluaciones Completadas
```http
GET /assessment/phq9/conversational/history?limit=10
Authorization: Bearer <token>
```

**Respuesta**:
```json
[
  {
    "id": 5,
    "total_score": 12,
    "severity": "moderate",
    "started_at": "2026-01-15T14:00:00",
    "completed_at": "2026-01-15T14:45:00",
    "responses": {
      "q1": {"response": "Sí, últimamente no tengo ganas de nada", "score": 2},
      "q2": {"response": "Me siento triste casi todos los días", "score": 3},
      ...
    }
  }
]
```

### 3. Cancelar Evaluación en Progreso
```http
DELETE /assessment/phq9/conversational/cancel
Authorization: Bearer <token>
```

---

## 🎬 Ejemplo de Flujo Completo

### Conversación Real:

```
Usuario: Me siento muy solo últimamente
Bot: Lamento escuchar eso. ¿Desde cuándo te sientes así?

[✅ Sistema detecta lenguaje depresivo → Inicia evaluación PHQ-9]

Usuario: Desde hace unas semanas
Bot: Entiendo, es difícil sentirse así. Me gustaría saber, 
     ¿has tenido poco interés o placer en hacer cosas últimamente?

[✅ Pregunta 1 del PHQ-9 insertada naturalmente]

Usuario: Sí, ya no me interesa nada
Bot: Es importante reconocer esos sentimientos. ¿Hay algo específico 
     que solías disfrutar?

[✅ Respuesta guardada, score inferido, continúa conversación normal]

Usuario: Antes me gustaba salir con amigos
Bot: Esa es una buena señal que recuerdes eso. Por cierto, 
     ¿te has sentido decaído, deprimido o sin esperanzas en las últimas semanas?

[✅ Pregunta 2 del PHQ-9 después de 2-3 mensajes]

... y así sucesivamente hasta completar las 9 preguntas
```

---

## ⚙️ Configuración

Puedes ajustar el espaciado entre preguntas modificando el threshold:

En [chat/routes.py](app/api/chat/routes.py):
```python
if conversational_phq9.should_ask_next_question(
    active_assessment, 
    messages_threshold=3  # Cambiar este número (default: 3)
):
```

- `messages_threshold=2`: Preguntas más frecuentes
- `messages_threshold=5`: Preguntas más espaciadas

---

## 🧪 Probar el Sistema

1. **Inicia el servidor**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Chatea normalmente** mencionando temas depresivos:
   - "Me siento muy triste"
   - "No tengo energía para nada"
   - "No duermo bien"

3. **El bot automáticamente**:
   - Detectará el contenido depresivo
   - Iniciará la evaluación conversacional
   - Insertará preguntas naturalmente

4. **Consulta el progreso**:
```bash
curl -X GET "http://localhost:8000/assessment/phq9/conversational/status" \
  -H "Authorization: Bearer <tu_token>"
```

---

## 📊 Las 9 Preguntas PHQ-9

1. ¿Has tenido poco interés o placer en hacer cosas últimamente?
2. ¿Te has sentido decaído, deprimido o sin esperanzas?
3. ¿Has tenido problemas para dormir o has dormido demasiado?
4. ¿Te has sentido cansado o con poca energía?
5. ¿Has notado cambios en tu apetito?
6. ¿Te has sentido mal contigo mismo o un fracaso?
7. ¿Has tenido problemas para concentrarte?
8. ¿Te mueves o hablas más lento, o estás más inquieto?
9. ¿Has tenido pensamientos de muerte o autolesión?

---

## 🔐 Seguridad y Privacidad

- ✅ Todas las respuestas se almacenan de forma segura
- ✅ Solo el usuario puede ver sus evaluaciones
- ✅ El sistema NO reemplaza un diagnóstico profesional
- ✅ En caso de riesgo alto, se recomienda buscar ayuda profesional

---

## 🚨 Importante

Este sistema es una **herramienta de screening**, NO un diagnóstico médico. Si detecta síntomas severos o pensamientos suicidas, SIEMPRE recomienda buscar ayuda profesional inmediatamente.
