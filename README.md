# 🎡 Sistema de Ruleta de Premios

API REST para gestión de eventos de ruleta de premios construida con **FastAPI + SQLAlchemy + PostgreSQL**.

---

## 📋 Requerimientos del proyecto

| # | Requerimiento |
|---|---|
| 1 | Migración masiva de bases de datos desde `.xlsx` o `.csv` |
| 2 | Registro de ruletas con fecha-hora de inicio y cierre |
| 3 | Registro de premios en existencia y entregados |
| 4 | Generación de tokens únicos por cliente |
| 5 | Envío de correos masivos en lotes de 500 clientes |
| 6 | Asignación aleatoria de premios |
| 7 | Asignación condicionada de premios a clientes específicos |
| 8 | Envío de correos de felicitación a ganadores |
| 9 | Notificación vía correo de referidos |
| 10 | Reenvío de correos individuales |
| 11 | Lista y gráfica porcentual de participación |

---

## 🗓️ Plan de entregas

| Semana | Fecha | Entregable |
|--------|-------|------------|
| **Semana 1** | 08 marzo | ✅ Diseño BD + modelos ORM + CRUD Ruletas |
| **Semana 2** | 15 marzo | CRUD Clientes, Premios, Agencias (importación XLSX/CSV) |
| **Semana 3** | 22 marzo | Maquetación ruleta (HTML5 + CSS3 + JS) |
| **Semana 4** | 29 marzo | Integración frontend con FastAPI |
| **Semana 5** | 05 abril | Pendientes y ajustes finales |

---

## 🗄️ Estructura del proyecto

```
ruleta_project/
│
├── main.py                          # Punto de entrada FastAPI
├── requirements.txt                 # Dependencias
├── .env.example                     # Plantilla de variables de entorno
├── alembic.ini                      # Configuración de migraciones
│
├── alembic/
│   ├── env.py                       # Entorno de migraciones Alembic
│   ├── script.py.mako               # Plantilla de archivos de migración
│   └── versions/                    # Archivos de migración generados
│
└── app/
    ├── __init__.py
    ├── config.py                    # Variables de entorno centralizadas
    │
    ├── database/
    │   ├── __init__.py
    │   └── database.py              # Motor SQLAlchemy + sesión
    │
    ├── models/
    │   ├── __init__.py
    │   └── models.py                # Modelos ORM (8 tablas)
    │
    ├── schemas/
    │   ├── __init__.py
    │   └── ruleta_schema.py         # Schemas Pydantic - Ruletas
    │
    ├── routers/
    │   ├── __init__.py
    │   └── ruletas.py               # Endpoints CRUD - Ruletas
    │
    └── services/
        ├── __init__.py
        └── cliente_service.py       # Lógica de negocio (portada desde Django)
```

---

## ⚙️ Instalación

### 1. Clonar el repositorio
```bash
git clone <url-del-repo>
cd ruleta_project
```

### 2. Crear y activar entorno virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con los valores reales
```

### 5. Crear la base de datos en PostgreSQL
```sql
CREATE DATABASE ruleta_db;
```

### 6. Ejecutar migraciones
```bash
# Crear la migración inicial desde los modelos ORM
alembic revision --autogenerate -m "crear_tablas_iniciales"

# Aplicar la migración
alembic upgrade head
```

### 7. Iniciar el servidor
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📡 Endpoints disponibles - Semana 1

### Ruletas

| Método | URL | Descripción |
|--------|-----|-------------|
| `POST` | `/ruletas/` | Crear nueva ruleta |
| `GET` | `/ruletas/?pagina=1` | Listar ruletas (20 por página) |
| `GET` | `/ruletas/{id}` | Consultar ruleta por ID |
| `PATCH` | `/ruletas/{id}` | Editar ruleta (campos opcionales) |
| `DELETE` | `/ruletas/{id}` | Eliminar ruleta |

### Utilidades

| Método | URL | Descripción |
|--------|-----|-------------|
| `GET` | `/` | Health check de la API |
| `GET` | `/docs` | Documentación Swagger UI |
| `GET` | `/redoc` | Documentación ReDoc |

---

## 🧪 Ejemplos de uso

### Crear una ruleta
```bash
curl -X POST "http://localhost:8000/ruletas/" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Ruleta Navidad 2026",
    "descripcion": "Evento especial de fin de año",
    "fecha_inicio": "2026-12-01T09:00:00",
    "fecha_cierre": "2026-12-31T23:59:59",
    "activa": true,
    "max_giros": 1
  }'
```

### Listar ruletas (página 1)
```bash
curl "http://localhost:8000/ruletas/?pagina=1"
```

### Listar solo ruletas activas
```bash
curl "http://localhost:8000/ruletas/?pagina=1&solo_activas=true"
```

### Editar una ruleta
```bash
curl -X PATCH "http://localhost:8000/ruletas/1" \
  -H "Content-Type: application/json" \
  -d '{"activa": false}'
```

### Eliminar una ruleta
```bash
curl -X DELETE "http://localhost:8000/ruletas/1"
```

---

## 🗂️ Modelos de base de datos

| Tabla | Descripción |
|-------|-------------|
| `ruletas` | Eventos de ruleta con fechas y configuración |
| `premios` | Premios por ruleta con inventario y probabilidades |
| `clientes` | Clientes con token único (portado desde Django) |
| `agencias` | Sucursales o puntos de venta |
| `participaciones` | Registro de cada giro realizado |
| `correos_log` | Historial de todos los correos enviados |
| `premios_condicionados` | Premios reservados para clientes específicos |
| `preguntas_seguridad` | Preguntas de validación de identidad |

---

## 🔧 Comandos útiles de Alembic

```bash
# Crear nueva migración automática
alembic revision --autogenerate -m "descripcion"

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Revertir la última migración
alembic downgrade -1

# Ver historial
alembic history --verbose

# Ver estado actual
alembic current

# Generar SQL sin ejecutar (modo offline)
alembic upgrade head --sql
```

---

## 🛠️ Stack tecnológico

- **FastAPI 0.115** — Framework API REST
- **SQLAlchemy 2.0** — ORM Python
- **PostgreSQL** — Base de datos relacional
- **Alembic 1.13** — Migraciones de base de datos
- **Pydantic v2** — Validación de datos
- **Uvicorn** — Servidor ASGI
- **fastapi-mail** — Envío de correos
- **openpyxl + pandas** — Importación XLSX/CSV (Semana 2)

---

## 📝 Notas de integración

Este proyecto integra código de un sistema legado en Django. Las funciones portadas están documentadas en `app/services/cliente_service.py` con comentarios que explican los cambios respecto al original.

---

*Documentación generada para entrega Semana 1 — 08 de marzo de 2026*
