# 🎡 Sistema de Ruleta de Premios

> Plataforma completa de gamificación para eventos empresariales y comerciales.
> Construida con **FastAPI + PostgreSQL + HTML5 Canvas**.

![Version](https://img.shields.io/badge/versión-3.2.0-gold)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)

---

## ✨ Características principales

| Módulo | Descripción |
|---|---|
| 🎡 **Ruleta visual** | Canvas HTML5 con animación física, sectores por probabilidad y puntero animado |
| 🎨 **Temas por evento** | 9 temas predefinidos (San Valentín, Navidad, Mundial, etc.) + personalizado con colores propios |
| 👥 **Gestión de clientes** | Importación masiva XLSX/CSV, perfil completo, token único por cliente |
| 📧 **Correos automáticos** | Invitación con link directo, felicitación con datos de entrega, referidos, rechazo |
| 🤝 **Sistema de referidos** | Flujo completo: solicitud → aprobación admin → correo al referido |
| 📋 **Encuestas** | 4 tipos de pregunta antes del giro para recolección de datos |
| 🏆 **Premios condicionados** | Asignación garantizada de premio a cliente específico |
| 📦 **Control de entregas** | Registrar entrega física con fecha, hora, lugar + correo al ganador |
| 🔐 **Auth JWT** | Panel de administración protegido con tokens de 8 horas |
| 📊 **Reportes** | Participaciones por ruleta, porcentajes, ganadores y estado de entregas |

---

## 🚀 Instalación rápida

### Requisitos
- Python 3.12+
- PostgreSQL 15 (puerto configurado en `.env`)
- Node.js (solo para generar documentación Word)

### 1. Clonar e instalar dependencias

```bash
git clone <repo>
cd Ruleta
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar `.env`

Copia `.env.example` a `.env` y completa los valores:

```env
# Base de datos
DATABASE_URL=postgresql+psycopg://postgres:TU_PASSWORD@localhost:5432/ruleta_db

# Correo Gmail SMTP
MAIL_USERNAME=tucorreo@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx   # Contraseña de aplicación (sin espacios)
MAIL_FROM=tucorreo@gmail.com
MAIL_FROM_NAME=Ruleta de Premios
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_TLS=True
MAIL_SSL=False

# Servidor
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=True
APP_RELOAD=True
```

### 3. Crear la base de datos

```sql
-- En pgAdmin o psql
CREATE DATABASE ruleta_db;
```

### 4. Ejecutar migraciones

```bash
alembic upgrade head
```

### 5. Iniciar el servidor

```bash
uvicorn main:app --reload
```

El sistema crea automáticamente el administrador inicial:
- **Usuario:** `admin`
- **Contraseña:** `admin123`

> ⚠️ Cambia la contraseña desde el panel después del primer login.

---

## 🌐 URLs del sistema

| URL | Descripción |
|---|---|
| `http://localhost:8000/login` | Login del panel de administración |
| `http://localhost:8000/admin` | Panel de administración completo |
| `http://localhost:8000/frontend` | Ruleta del cliente |
| `http://localhost:8000/docs` | Documentación Swagger de la API |
| `http://localhost:8000/redoc` | Documentación ReDoc |

---

## 📁 Estructura del proyecto

```
Ruleta/
├── main.py                          # v3.2 — App principal + 8 routers
├── requirements.txt
├── .env                             # ⚠️ No subir a git
├── .env.example
├── .gitignore
├── alembic.ini
├── alembic/versions/                # Migraciones
│
├── frontend/
│   ├── ruleta.html                  # Ruleta visual — 5 pantallas + temas
│   ├── admin.html                   # Panel admin — 9 módulos
│   └── login.html                   # Login con JWT
│
└── app/
    ├── config.py                    # Variables de entorno
    ├── database/
    │   └── database.py              # Conexión SQLAlchemy
    │
    ├── models/
    │   ├── models.py                # 8 tablas principales
    │   ├── admin_model.py           # Tabla administradores
    │   ├── referido_model_orm.py    # Tabla solicitudes_referido
    │   └── encuesta_model.py        # Tablas encuesta
    │
    ├── schemas/
    │   ├── ruleta_schema.py
    │   ├── cliente_schema.py
    │   ├── premio_schema.py
    │   ├── agencia_schema.py
    │   ├── pregunta_schema.py
    │   └── giro_schema.py
    │
    ├── routers/
    │   ├── auth.py                  # Login + JWT + gestión admins
    │   ├── ruletas.py
    │   ├── clientes.py              # + importación XLSX/CSV
    │   ├── premios.py               # + condicionados
    │   ├── agencias.py
    │   ├── preguntas.py
    │   ├── ruleta_giro.py           # Giro + ganadores + entrega
    │   ├── referidos.py
    │   └── encuestas.py
    │
    └── services/
        ├── auth_service.py          # JWT + bcrypt
        ├── giro_service.py          # Algoritmo ponderado + condicionado
        ├── correo_service.py        # 4 plantillas HTML + Gmail SMTP
        └── referido_service.py      # Flujo completo de referidos
```

---

## 🎯 Flujo del cliente

```
1. Recibe correo de invitación con link ?token=XXX&ruleta_id=Y
         ↓
2. Pantalla de acceso — verifica token + selecciona ruleta
   • Si el evento no ha iniciado → countdown en tiempo real
   • Si ya participó en esa ruleta → muestra resultado anterior
         ↓
3. Completar perfil (solo si faltan datos: nombre, celular, etc.)
         ↓
4. Preguntas de encuesta (configuradas por el admin)
         ↓
5. ¡Girar la ruleta! 🎡
   • La ruleta frena exactamente en el sector ganador
   • Sectores con premio (coloridos) + sectores sin premio (grises)
         ↓
6. Resultado con confetti + opción de referir a un amigo
```

---

## 🎨 Temas visuales disponibles

| Tema | Evento | Partículas animadas |
|---|---|---|
| 🎡 Dorado Clásico | Por defecto | — |
| ❤️ San Valentín | 14 de febrero | ❤️ 💕 🌹 |
| 🌸 Día de las Madres | Mayo | 🌸 💐 🌺 |
| 🎄 Navidad | Diciembre | ❄️ 🎄 🎅 |
| ⚽ Mundial | Copa del Mundo | ⚽ 🏆 🌍 |
| 🎃 Halloween | Octubre | 🎃 🦇 👻 |
| 🌌 Galaxia | Futurista | ⭐ ✨ 🪐 |
| 🌴 Trópico | Verano/Playa | 🌴 🌺 🦜 |
| 💼 Empresarial | Corporativo | — |
| 🎨 Personalizado | Cualquier evento | 3 colores propios |

---

## 📊 Base de datos — 12 tablas

| Tabla | Descripción |
|---|---|
| `ruletas` | Eventos con fechas, tema visual y colores |
| `premios` | Inventario con probabilidades y condicionados |
| `clientes` | Participantes con perfil completo y token |
| `agencias` | Sucursales o agencias |
| `participaciones` | Registro de giros y premios ganados |
| `premios_condicionados` | Premios reservados por email |
| `correos_log` | Historial completo de correos enviados |
| `preguntas_seguridad` | Preguntas para verificación de identidad |
| `solicitudes_referido` | Flujo de referidos con motivo de rechazo |
| `administradores` | Usuarios del panel con hash bcrypt |
| `preguntas_encuesta` | Preguntas configurables por ruleta |
| `respuestas_encuesta` | Respuestas de los clientes por ruleta |

---

## 🔑 API — Endpoints principales

```
POST  /auth/login                    Iniciar sesión (devuelve JWT)
GET   /auth/me                       Perfil del admin autenticado

GET   /ruletas/                      Listar ruletas
POST  /ruletas/                      Crear ruleta (con tema y colores)
PATCH /ruletas/{id}                  Editar ruleta

GET   /clientes/                     Listar con filtros
POST  /clientes/importar/            Importar XLSX/CSV masivo

POST  /ruleta/girar/                 Ejecutar giro (token + ruleta_id)
GET   /ruleta/validar/{token}        Verificar token por ruleta
GET   /ruleta/ganadores/{id}         Todos los participantes
PATCH /ruleta/ganadores/{id}/entregar  Registrar entrega + correo

POST  /correos/masivo/               Envío masivo en lotes de 500
POST  /correos/reenviar/{id}         Reenvío individual

POST  /referidos/                    Crear solicitud de referido
PATCH /referidos/{id}/aprobar        Aprobar + crear cliente + correo
PATCH /referidos/{id}/rechazar       Rechazar + correo con motivo

GET   /encuestas/ruleta/{id}         Preguntas activas para cliente
POST  /encuestas/responder/          Guardar respuestas
```

---

## 📦 Dependencias principales

```txt
fastapi>=0.115
uvicorn[standard]
sqlalchemy>=2.0
psycopg[binary]
alembic
pydantic[email]
python-multipart
fastapi-mail
openpyxl
python-jose[cryptography]
passlib[bcrypt]
python-dotenv
```

---

## 📄 Licencia

Proyecto desarrollado como sistema propietario.
© 2026 Ruleta de Premios — Todos los derechos reservados.
