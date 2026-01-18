# Chatbot Backend con LLaMA 3.1 8B

Backend de FastAPI con autenticación JWT y chatbot con IA usando LLaMA 3.1 8B.

## Características

- ✅ Autenticación JWT (registro/login)
- ✅ Chat con LLaMA 3.1 8B (modelo local, gratis)
- ✅ Streaming de respuestas en tiempo real
- ✅ Memoria de contexto por usuario
- ✅ Historial de conversación persistente
- ✅ API REST documentada con Swagger

## Requisitos

- Python 3.10+
- PostgreSQL (o SQLite para desarrollo)
- Ollama instalado (ya configurado)

## Instalación

### 1. Crear entorno virtual e instalar dependencias

```bash
cd ~/chatbot_backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Crear archivo `.env` en la raíz:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/chatbot_db
# O para desarrollo con SQLite:
# DATABASE_URL=sqlite:///./chatbot.db
```

### 3. Crear tablas de base de datos

```bash
python -m app.init_db
```

### 4. Levantar servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

### Autenticación

#### POST /auth/register
Registrar nuevo usuario.
```json
{
  "email": "user@example.com",
  "password": "tu_password"
}
```

#### POST /auth/login
Iniciar sesión y obtener token JWT.
```json
{
  "email": "user@example.com",
  "password": "tu_password"
}
```

Respuesta:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### Chat

#### POST /chat/stream
Chat con streaming (respuestas en tiempo real).

Headers:
```
Authorization: Bearer <tu_token>
Content-Type: application/json
```

Body:
```json
{
  "message": "¿Qué es Python?",
  "use_context": true
}
```

Respuesta: Server-Sent Events (streaming)

#### GET /chat/history?limit=50
Obtener historial de conversación.

Headers:
```
Authorization: Bearer <tu_token>
```

#### DELETE /chat/history
Borrar todo el historial de conversación.

## Uso con Android

### Ejemplo con Retrofit

```kotlin
// Para streaming, usa OkHttp directamente
val client = OkHttpClient()
val token = "Bearer tu_token_aqui"

val request = Request.Builder()
    .url("http://TU_IP:8000/chat/stream")
    .header("Authorization", token)
    .post(
        """{"message": "Hola", "use_context": true}"""
            .toRequestBody("application/json".toMediaType())
    )
    .build()

client.newCall(request).execute().use { response ->
    val source = response.body?.source()
    while (source?.exhausted() == false) {
        val line = source.readUtf8Line() ?: continue
        if (line.startsWith("data: ")) {
            val chunk = line.removePrefix("data: ")
            if (chunk == "[DONE]") break
            // Mostrar chunk en UI
            runOnUiThread { tvChat.append(chunk) }
        }
    }
}
```

### Conectar desde Android

- **Emulador**: `http://10.0.2.2:8000/`
- **Dispositivo físico**: `http://TU_IP_LOCAL:8000/`

Obtener IP en WSL:
```bash
ip addr show eth0 | grep inet
```

## Documentación Interactiva

Abrir en el navegador:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Estructura del Proyecto

```
chatbot_backend/
├── app/
│   ├── api/
│   │   ├── auth/          # Endpoints de autenticación
│   │   └── chat/          # Endpoints de chat
│   ├── core/              # Configuración, DB, seguridad
│   ├── models/            # Modelos SQLAlchemy
│   ├── services/          # Lógica de negocio (Ollama)
│   ├── init_db.py         # Script para crear tablas
│   └── main.py            # Punto de entrada
├── requirements.txt
├── .env                   # Variables de entorno
└── README.md
```

## Modelos de IA Disponibles

Ver modelos disponibles en Ollama:
```bash
ollama list
```

Cambiar modelo en `app/services/ollama_service.py`:
```python
self.model = "llama3.1:8b"  # o "mistral", "phi3", etc.
```

Descargar otros modelos:
```bash
ollama pull llama3.2:3b      # Más rápido, menor calidad
ollama pull mistral:7b       # Alternativa a LLaMA
ollama pull codellama:7b     # Especializado en código
```

## Troubleshooting

### Error: "Connection refused" al llamar a Ollama
Verificar que Ollama esté corriendo:
```bash
systemctl status ollama
# O iniciar manualmente:
ollama serve
```

### Errores de base de datos
Verificar que `DATABASE_URL` en `.env` sea correcta y que la base de datos exista.

Para SQLite (desarrollo):
```env
DATABASE_URL=sqlite:///./chatbot.db
```

### Token expirado (401)
Los tokens expiran en 60 minutos. Hacer login nuevamente para obtener uno nuevo.

## Próximas Mejoras

- [ ] Refresh tokens
- [ ] Rate limiting
- [ ] Sistema de roles (admin/user)
- [ ] Conversaciones múltiples por usuario
- [ ] Export de conversaciones
- [ ] Integración con RAG (documentos propios)
- [ ] Fine-tuning del modelo

## Licencia

MIT
