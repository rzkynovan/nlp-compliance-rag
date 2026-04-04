from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Literal
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "Compliance Audit RAG"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    LLAMAPARSE_API_KEY: str = Field(..., env="LLAMAPARSE_API_KEY")
    
    DATABASE_URL: Optional[str] = Field(None, env="DATABASE_URL")
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    MLFLOW_TRACKING_URI: str = Field("http://localhost:5000", env="MLFLOW_TRACKING_URI")
    
    CHROMADB_PERSIST_DIR: str = Field(
        default="../data/processed/chroma_db",
        env="CHROMADB_PERSIST_DIR"
    )
    CHROMADB_COLLECTION_BI: str = "bi_regulations"
    CHROMADB_COLLECTION_OJK: str = "ojk_regulations"
    
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1
    RETRIEVAL_TOP_K: int = 5
    
    MAX_FILE_SIZE: int = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS: set = {".pdf", ".md", ".txt"}
    
    COST_OPTIMIZATION_MODE: Literal["development", "production"] = "development"
    DAILY_BUDGET_LIMIT_USD: float = 5.0
    ENABLE_CACHE: bool = True
    CACHE_TTL_HOURS: int =24
    
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 10
    RATE_LIMIT_TOKENS_PER_MINUTE: int = 100000
    
    class Config:
        env_file = ".env"
        case_sensitive = True


MODEL_COSTS = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()