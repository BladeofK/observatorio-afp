# Observatorio de Fondos de Pensiones 🇨🇱

Plataforma de datos que ingiere diariamente información pública del sistema de AFP chileno
(valor cuota de los fondos A–E, UF, dólar), la procesa con **arquitectura Medallón** en
**BigQuery**, la expone mediante una **API REST en Cloud Run** y permite hacer preguntas en
lenguaje natural gracias a un **LLM (Gemini)** con barreras de seguridad.

Diseñada para operar **dentro de la capa gratuita de Google Cloud**, con límites duros que
impiden gastar dinero (ver [docs/blindaje-costos.md](docs/blindaje-costos.md)).

## Arquitectura

```mermaid
flowchart LR
    subgraph Fuentes públicas
        SP[Superintendencia de Pensiones<br/>valor cuota]
        MI[mindicador.cl<br/>UF · dólar]
    end

    SCH[Cloud Scheduler<br/>diario 08:00] -->|dispara| JOB

    subgraph Cloud Run Job · ETL Python
        JOB[ingestar → validar → cargar]
    end

    SP --> JOB
    MI --> JOB
    JOB -->|archivo crudo| GCS[(GCS<br/>bronze/)]
    JOB -->|load job gratuito| B[(BigQuery<br/>bronze)]
    B -->|MERGE| S[(silver<br/>tipado y deduplicado)]
    S -->|CREATE OR REPLACE| G[(gold<br/>rentabilidades y ranking)]

    subgraph Cloud Run Service · FastAPI
        API[/fondos · /indicadores · /preguntar/]
    end

    G --> API
    API <-->|texto → SQL<br/>con barreras| LLM[Gemini API<br/>capa gratuita]
    API --> UI[Frontend Angular<br/>Firebase Hosting]
```

## Stack

| Capa | Tecnología |
|---|---|
| Ingesta y ETL | Python 3.12, httpx, Cloud Run Jobs, Cloud Scheduler |
| Almacenamiento | Cloud Storage (bronze crudo), BigQuery (bronze, silver, gold) |
| Transformación | SQL BigQuery: DDL particionado/clusterizado, `MERGE` incremental |
| API | FastAPI en Cloud Run (escala a cero, máx. 1 instancia) |
| IA | Gemini API (Google AI Studio) + validación de SQL con `sqlglot` |
| Infraestructura | Terraform, Artifact Registry, Secret Manager |
| Calidad | pytest, ruff, validaciones de datos entre capas, GitHub Actions |
| Control de costos | Cuota diaria de BigQuery, presupuesto con corte automático de facturación |

## Estructura del repositorio

```
observatorio-afp/
├── docs/                  # Diseño, plan de desarrollo y blindaje de costos
├── src/observatorio/
│   ├── config.py          # Configuración por variables de entorno
│   ├── bq.py              # Cliente BigQuery con tope de bytes por consulta
│   ├── etl/               # Fuentes, bronze, silver/gold, calidad y CLI del job
│   ├── api/               # FastAPI: rutas y límite de solicitudes
│   └── llm/               # Texto a SQL con barreras de seguridad
├── sql/
│   ├── ddl/               # Creación de tablas bronze y silver
│   ├── silver/            # MERGE bronze → silver
│   └── gold/              # Tablas analíticas
├── infra/terraform/       # Toda la infraestructura, límites de costo incluidos
├── tests/                 # Tests unitarios (no requieren GCP)
├── Dockerfile             # Imagen única para API y job ETL
└── .github/workflows/     # CI: lint + tests
```

## Ejecutar en local

Requisitos: Python 3.12+ y [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
```

```powershell
uv run pytest
```

Para conectarse a GCP en local:

```powershell
gcloud auth application-default login
```

```powershell
Copy-Item .env.example .env
```

```powershell
uv run python -m observatorio.etl.main diario
```

```powershell
uv run uvicorn observatorio.api.main:app --reload
```

La documentación interactiva de la API queda en `http://localhost:8000/docs`.

## Documentación

- [Diseño técnico](docs/diseno.md): modelo de datos por capa, API, LLM y decisiones.
- [Plan de desarrollo](docs/plan.md): fases, tareas y criterios de término.
- [Blindaje de costos](docs/blindaje-costos.md): cómo este proyecto nunca genera cobros.

## Fuentes de datos

- Superintendencia de Pensiones: valores cuota y patrimonio de los fondos de pensiones.
- [mindicador.cl](https://mindicador.cl): indicadores económicos diarios de Chile (UF, dólar).

Los datos son públicos. Este proyecto es educativo y no constituye asesoría financiera.
