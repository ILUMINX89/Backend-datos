# Backend-datos

Base de microservicio para exponer datos de InfluxDB mediante una API REST con FastAPI.

## Arquitectura

```text
app/
├── api/
│   └── routes.py              # Endpoints HTTP
├── core/
│   └── config.py              # Variables de entorno/configuración
├── infrastructure/
│   └── influx.py              # Adaptador de acceso a InfluxDB
└── main.py                    # Entrada de FastAPI
```

La API queda desacoplada de InfluxDB: los consumidores (Dashboard Hogar u otros microservicios) llaman esta API en lugar de conectarse directamente a la base.

## Requisitos

- Python 3.11+
- InfluxDB 2.x / Cloud compatible con consultas Flux
- URL, token, organización y bucket de InfluxDB

## Instalación local

```bash
git clone https://github.com/ILUMINX89/Backend-datos.git
cd Backend-datos

python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` con los datos reales de InfluxDB:

```env
INFLUX_URL=http://IP_O_HOST:8086
INFLUX_TOKEN=TU_TOKEN
INFLUX_ORG=TU_ORG
INFLUX_BUCKET=TU_BUCKET
```

No subas `.env` al repositorio. Ya está excluido mediante `.gitignore`.

## Ejecutar

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger:

```text
http://localhost:8000/docs
```

## Endpoints

### Health API

```http
GET /health
```

### Health InfluxDB

```http
GET /health/influx
```

Permite comprobar que las credenciales y la conectividad con InfluxDB funcionan.

### Consultar un measurement

```http
GET /v1/influx/measurement/{measurement}?start=-1h&limit=1000
```

Ejemplo:

```http
GET /v1/influx/measurement/niveles_rx?start=-24h&limit=5000
```

Respuesta:

```json
{
  "measurement": "niveles_rx",
  "count": 2,
  "data": [
    {
      "_time": "2026-09-11T16:00:00Z",
      "_measurement": "niveles_rx",
      "_field": "valor",
      "_value": -3.4
    }
  ]
}
```

### Consultas Flux libres

Existe el endpoint:

```http
POST /v1/influx/query
```

Por seguridad viene deshabilitado. Para habilitarlo:

```env
ALLOW_RAW_FLUX=true
```

Body:

```json
{
  "query": "from(bucket: \"mi_bucket\") |> range(start: -1h)"
}
```

No se recomienda exponer este endpoint directamente a Internet ni habilitarlo para clientes no confiables.

## Docker

Construir:

```bash
docker build -t backend-datos .
```

Ejecutar:

```bash
docker run --rm -p 8000:8000 --env-file .env backend-datos
```

## Flujo recomendado

```text
InfluxDB
   ↓
Backend-datos API
   ↓
Dashboard Hogar / otros microservicios
```

La siguiente evolución recomendada es crear endpoints específicos por dominio (HFC, FTTH, alarmas, niveles, disponibilidad, etc.) en lugar de permitir que el frontend construya consultas Flux directamente.
