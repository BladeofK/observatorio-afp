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
    gemini_model: str = "gemini-2.5-flash"
    llm_max_por_minuto_ip: int = 5
    llm_max_diario: int = 200

    # Fuentes.
    # POR CONFIRMAR (fase 1): URL y parámetros de descarga del valor cuota en spensiones.cl.
    # Revisar la página de valores cuota y ajustar antes de la primera ingesta real.
    url_valor_cuota: str = (
        "https://www.spensiones.cl/apps/valoresCuotaFondo/vcfAFPxls.php"
        "?aaaaini={anio_ini}&aaaafin={anio_fin}&tf={fondo}&fecconf={fecha}"
    )
    url_mindicador: str = "https://mindicador.cl/api/{indicador}/{anio}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
