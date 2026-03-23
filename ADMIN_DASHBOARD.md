# 🔐 Sistema de Administración - Dashboard de Métricas

## Crear Usuario Administrador

Ejecuta este comando desde la raíz del proyecto:

```bash
python create_admin.py admin@chatbot.com tuContraseña123
```

**Ejemplo práctico:**
```bash
python create_admin.py admin@ejemplo.com AdminPassword2024!
```

**Respuesta esperada:**
```
✅ Admin creado exitosamente
   Email: admin@ejemplo.com
   ID: 1
   Status: Activo
   Rol: Admin
```

## Endpoints del Dashboard (Solo para Admins)

### 1. Obtener Métricas Generales
```
GET /admin/dashboard/metrics
Authorization: Bearer <token_del_admin>
```

**Response:**
```json
{
  "timestamp": "2024-03-22T10:30:00",
  "admin_email": "admin@chatbot.com",
  "users": {
    "total": 45,
    "active": 42,
    "admins": 1,
    "new_this_week": 5,
    "requiring_attention": 3
  },
  "messages": {
    "total": 1250,
    "this_week": 220,
    "avg_per_user": 27.78
  },
  "phq9_assessments": {
    "total": 32,
    "this_week": 8,
    "avg_score": 6.5,
    "max_score": 9,
    "by_severity": {
      "minimal": 15,
      "mild": 10,
      "moderate": 5,
      "moderately_severe": 2,
      "severe": 0
    }
  },
  "depression_detections": {
    "total": 250,
    "positive": 45,
    "this_week": 30,
    "positive_rate": "18.0%"
  },
  "conversational_assessments": {
    "total": 20,
    "completed": 15,
    "in_progress": 5
  }
}
```

### 2. Listar Todos los Usuarios
```
GET /admin/dashboard/users?limit=50&offset=0
Authorization: Bearer <token_del_admin>
```

**Parámetros:**
- `limit`: Número de usuarios por página (default: 50)
- `offset`: Desplazamiento (default: 0)

**Response:**
```json
{
  "total": 45,
  "limit": 50,
  "offset": 0,
  "users": [
    {
      "id": 1,
      "email": "user1@chatbot.com",
      "is_active": true,
      "is_admin": false,
      "created_at": "2024-03-15T10:00:00",
      "messages_count": 120,
      "risk_level": "mild",
      "requires_attention": false,
      "last_assessment": "2024-03-20T15:30:00"
    },
    ...
  ]
}
```

### 3. Obtener Detalles de un Usuario
```
GET /admin/dashboard/user/{user_id}
Authorization: Bearer <token_del_admin>
```

**Response:**
```json
{
  "user": {
    "id": 5,
    "email": "juan@chatbot.com",
    "is_active": true,
    "is_admin": false,
    "created_at": "2024-03-10T08:00:00"
  },
  "health_summary": {
    "overall_risk_level": "moderate",
    "requires_attention": false,
    "latest_phq9_score": 8,
    "total_assessments": 3,
    "depression_detections": 12
  },
  "statistics": {
    "total_messages": 85,
    "total_assessments": 3,
    "total_detections": 12
  },
  "recent_assessments": [
    {
      "id": 12,
      "score": 8,
      "severity": "mild",
      "created_at": "2024-03-20T15:30:00"
    }
  ],
  "recent_detections": [
    {
      "id": 45,
      "detected": true,
      "risk_level": "medium",
      "confidence": 0.75,
      "detected_at": "2024-03-21T12:00:00"
    }
  ]
}
```

### 4. Obtener Usuarios de Alto Riesgo
```
GET /admin/dashboard/high-risk-users
Authorization: Bearer <token_del_admin>
```

**Response:**
```json
{
  "total_high_risk": 3,
  "users": [
    {
      "user_id": 8,
      "email": "carlos@chatbot.com",
      "risk_level": "severe",
      "latest_score": 7,
      "high_risk_detections": 5,
      "last_alert": "2024-03-21T14:00:00",
      "updated_at": "2024-03-21T14:05:00"
    },
    ...
  ]
}
```

## Cómo Obtener el Token de Administrador

1. **Login con el usuario admin:**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@chatbot.com",
    "password": "tuContraseña123"
  }'
```

2. **Respuesta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

3. **Usar el token en las peticiones al dashboard:**
```bash
curl -H "Authorization: Bearer <access_token>" \
  "http://localhost:8000/admin/dashboard/metrics"
```

## Seguridad

- ✅ Solo usuarios con `is_admin = true` pueden acceder
- ✅ Se requiere autenticación JWT válida
- ✅ Los endpoints retornan 403 Forbidden si no es admin
- ✅ Se registra quién accede al dashboard (via `admin_email` en respuesta)

## Ejemplo Completo en cURL

```bash
# 1. Login
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@chatbot.com","password":"AdminPassword2024!"}' \
  | jq -r '.access_token')

# 2. Obtener métricas
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/admin/dashboard/metrics" | jq '.'

# 3. Ver usuarios de alto riesgo
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/admin/dashboard/high-risk-users" | jq '.'
```

## Códigos de Error

| Código | Significado |
|--------|-----------|
| `200` | ✅ Éxito |
| `401` | ❌ Token inválido o expirado |
| `403` | ❌ No tiene permisos de admin |
| `404` | ❌ Usuario no encontrado |
