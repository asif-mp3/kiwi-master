"""
Config Loader - Centralized configuration access for Thara.ai

Provides typed access to all configuration values from settings.yaml.
Replaces hardcoded values throughout the codebase.

Usage:
    from utils.config_loader import get_config, Config

    config = get_config()
    print(config.query.profile_sample_rows)  # 10000
    print(config.cache.query_cache_ttl_seconds)  # 300
"""

import yaml
import threading
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class DuckDBConfig:
    """DuckDB database configuration."""
    snapshot_path: str = "data_sources/snapshots/latest.duckdb"
    max_connections: int = 10
    connection_timeout_seconds: int = 30


@dataclass
class GoogleSheetsConfig:
    """Google Sheets configuration."""
    credentials_path: str = "credentials/service_account.json"
    spreadsheet_id: str = ""
    cache_check_interval_seconds: int = 60
    numeric_conversion_threshold: float = 0.8
    date_conversion_threshold: float = 0.5


@dataclass
class LLMConfig:
    """LLM (Gemini) configuration."""
    api_key_env: str = "GEMINI_API_KEY"
    max_retries: int = 3
    model: str = "gemini-2.5-pro"
    provider: str = "gemini"
    temperature: float = 0.0
    request_timeout_seconds: int = 60
    enable_streaming: bool = True


@dataclass
class ProjectConfig:
    """Project metadata."""
    environment: str = "local"
    name: str = "thara_ai"


@dataclass
class SchemaIntelligenceConfig:
    """Schema intelligence configuration."""
    embedding_model: str = "text-embedding-3-large"
    top_k: int = 5
    max_tables_in_prompt: int = 5


@dataclass
class QueryConfig:
    """Query processing configuration."""
    profile_sample_rows: int = 10000
    max_result_rows: int = 10000
    default_limit: int = 100
    max_healing_retries: int = 3
    max_healing_limit: int = 1000


@dataclass
class CacheConfig:
    """Caching configuration."""
    query_cache_max_size: int = 100
    query_cache_ttl_seconds: int = 300
    tts_cache_max_size_mb: int = 500
    tts_cache_ttl_hours: int = 24
    schema_cache_ttl_seconds: int = 3600


@dataclass
class VoiceConfig:
    """Voice/TTS configuration."""
    elevenlabs_api_key_env: str = "ELEVENLABS_API_KEY"
    default_voice_id: str = "pNInz6obpgDQGcFmaJgB"
    tamil_voice_id: str = "pNInz6obpgDQGcFmaJgB"
    request_timeout_seconds: int = 30


@dataclass
class TableRoutingConfig:
    """Table routing scoring weights."""
    has_product_dimension: int = 15
    has_location_dimension: int = 15
    has_date_dimension: int = 15
    has_metric: int = 20
    correct_granularity: int = 30
    date_range_covers_query: int = 20
    is_transactional: int = 15
    data_quality_high: int = 10


@dataclass
class Config:
    """Complete configuration for Thara.ai."""
    duckdb: DuckDBConfig
    google_sheets: GoogleSheetsConfig
    llm: LLMConfig
    project: ProjectConfig
    schema_intelligence: SchemaIntelligenceConfig
    query: QueryConfig
    cache: CacheConfig
    voice: VoiceConfig
    table_routing: TableRoutingConfig


# Singleton instance
_config: Optional[Config] = None
_config_lock = threading.Lock()
_config_path = Path("config/settings.yaml")


def _load_raw_config() -> dict:
    """Load raw YAML config from file."""
    if not _config_path.exists():
        return {}

    with open(_config_path) as f:
        return yaml.safe_load(f) or {}


def _parse_config(raw: dict) -> Config:
    """Parse raw dict into typed Config object."""
    return Config(
        duckdb=DuckDBConfig(
            snapshot_path=raw.get("duckdb", {}).get("snapshot_path", "data_sources/snapshots/latest.duckdb"),
            max_connections=raw.get("duckdb", {}).get("max_connections", 10),
            connection_timeout_seconds=raw.get("duckdb", {}).get("connection_timeout_seconds", 30),
        ),
        google_sheets=GoogleSheetsConfig(
            credentials_path=raw.get("google_sheets", {}).get("credentials_path", "credentials/service_account.json"),
            spreadsheet_id=raw.get("google_sheets", {}).get("spreadsheet_id", ""),
            cache_check_interval_seconds=raw.get("google_sheets", {}).get("cache_check_interval_seconds", 60),
            numeric_conversion_threshold=raw.get("google_sheets", {}).get("numeric_conversion_threshold", 0.8),
            date_conversion_threshold=raw.get("google_sheets", {}).get("date_conversion_threshold", 0.5),
        ),
        llm=LLMConfig(
            api_key_env=raw.get("llm", {}).get("api_key_env", "GEMINI_API_KEY"),
            max_retries=raw.get("llm", {}).get("max_retries", 3),
            model=raw.get("llm", {}).get("model", "gemini-2.5-pro"),
            provider=raw.get("llm", {}).get("provider", "gemini"),
            temperature=raw.get("llm", {}).get("temperature", 0.0),
            request_timeout_seconds=raw.get("llm", {}).get("request_timeout_seconds", 60),
            enable_streaming=raw.get("llm", {}).get("enable_streaming", True),
        ),
        project=ProjectConfig(
            environment=raw.get("project", {}).get("environment", "local"),
            name=raw.get("project", {}).get("name", "thara_ai"),
        ),
        schema_intelligence=SchemaIntelligenceConfig(
            embedding_model=raw.get("schema_intelligence", {}).get("embedding_model", "text-embedding-3-large"),
            top_k=raw.get("schema_intelligence", {}).get("top_k", 5),
            max_tables_in_prompt=raw.get("schema_intelligence", {}).get("max_tables_in_prompt", 5),
        ),
        query=QueryConfig(
            profile_sample_rows=raw.get("query", {}).get("profile_sample_rows", 10000),
            max_result_rows=raw.get("query", {}).get("max_result_rows", 10000),
            default_limit=raw.get("query", {}).get("default_limit", 100),
            max_healing_retries=raw.get("query", {}).get("max_healing_retries", 3),
            max_healing_limit=raw.get("query", {}).get("max_healing_limit", 1000),
        ),
        cache=CacheConfig(
            query_cache_max_size=raw.get("cache", {}).get("query_cache_max_size", 100),
            query_cache_ttl_seconds=raw.get("cache", {}).get("query_cache_ttl_seconds", 300),
            tts_cache_max_size_mb=raw.get("cache", {}).get("tts_cache_max_size_mb", 500),
            tts_cache_ttl_hours=raw.get("cache", {}).get("tts_cache_ttl_hours", 24),
            schema_cache_ttl_seconds=raw.get("cache", {}).get("schema_cache_ttl_seconds", 3600),
        ),
        voice=VoiceConfig(
            elevenlabs_api_key_env=raw.get("voice", {}).get("elevenlabs_api_key_env", "ELEVENLABS_API_KEY"),
            default_voice_id=raw.get("voice", {}).get("default_voice_id", "pNInz6obpgDQGcFmaJgB"),
            tamil_voice_id=raw.get("voice", {}).get("tamil_voice_id", "pNInz6obpgDQGcFmaJgB"),
            request_timeout_seconds=raw.get("voice", {}).get("request_timeout_seconds", 30),
        ),
        table_routing=TableRoutingConfig(
            has_product_dimension=raw.get("table_routing", {}).get("has_product_dimension", 15),
            has_location_dimension=raw.get("table_routing", {}).get("has_location_dimension", 15),
            has_date_dimension=raw.get("table_routing", {}).get("has_date_dimension", 15),
            has_metric=raw.get("table_routing", {}).get("has_metric", 20),
            correct_granularity=raw.get("table_routing", {}).get("correct_granularity", 30),
            date_range_covers_query=raw.get("table_routing", {}).get("date_range_covers_query", 20),
            is_transactional=raw.get("table_routing", {}).get("is_transactional", 15),
            data_quality_high=raw.get("table_routing", {}).get("data_quality_high", 10),
        ),
    )


def get_config(force_reload: bool = False) -> Config:
    """
    Get the singleton Config instance.

    Args:
        force_reload: Force reload from file (ignores cache)

    Returns:
        Config: The configuration object
    """
    global _config

    if _config is not None and not force_reload:
        return _config

    with _config_lock:
        if _config is None or force_reload:
            raw = _load_raw_config()
            _config = _parse_config(raw)
        return _config


def reload_config() -> Config:
    """Force reload configuration from file."""
    return get_config(force_reload=True)


# Convenience functions for common config access
def get_query_config() -> QueryConfig:
    """Get query processing configuration."""
    return get_config().query


def get_cache_config() -> CacheConfig:
    """Get caching configuration."""
    return get_config().cache


def get_llm_config() -> LLMConfig:
    """Get LLM configuration."""
    return get_config().llm


def get_voice_config() -> VoiceConfig:
    """Get voice/TTS configuration."""
    return get_config().voice
