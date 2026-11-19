"""Configuración central, leída desde variables de entorno (o un archivo .env en local)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

MIB = 1024 * 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # GCP
    gcp_project: str = ""
    bq_location: str = "US"
    bucket: str = ""
    dataset_bronze: str = "bronze"
    dataset_silver: str = "silver"
    dataset_gold: str = "gold"
    sql_dir: str = ""

    # Blindaje de costos: BigQuery aborta cualquier consulta que escanee más que esto.
    max_bytes_billed: int = 100 * MIB

    # LLM (Gemini vía AI Studio; la API key debe pertenecer a un proyecto SIN facturación)
    gemini_api_key: str = ""
    # Los modelos "lite" responden más rápido (los Flash 3.x "piensan" y tardan >12 s).
    gemini_model: str = "gemini-3.5-flash-lite"
    # Si el principal está saturado (503), sin cuota (429) o lento, se prueban estos en orden.
    gemini_modelos_respaldo: str = "gemini-flash-lite-latest,gemini-flash-latest"
    gemini_timeout_s: float = 25  # por intento
    gemini_presupuesto_s: float = 75  # por pregunta (Cloud Run corta a los 90 s)
    llm_max_por_minuto_ip: int = 5
    llm_max_diario: int = 200

    # Fuentes (verificadas en noviembre de 2026).
    url_pagina_valor_cuota: str = (
        "https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFP.php?tf=A"
    )
    url_valor_cuota: str = (
        "https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFPxls.php"
        "?aaaaini={anio_ini}&aaaafin={anio_fin}&tf={fondo}&fecconf={fecconf}"
    )
    url_mindicador: str = "https://mindicador.cl/api/{indicador}/{anio}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
