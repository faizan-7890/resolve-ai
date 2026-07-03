from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ResolveAI"
    SECRET_KEY: str  # Required — must be set via .env or environment variable
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database (PostgreSQL; override via .env)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/resolve_ai"

    # OpenAI configurations
    OPENAI_API_KEY: str = ""

    # NVIDIA NIM configurations
    NVIDIA_NIM_API_KEY: str = ""
    NIM_EMBEDDING_MODEL: str = "nvidia/llama-3.2-nv-embedqa-1b-v2"
    NIM_LLM_MODEL: str = "meta/llama-3-70b-instruct"

    # CORS — comma-separated list of allowed origins
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Qdrant vector database (maintained for legacy compatibility if needed)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "resolve_ai_memories"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


settings = Settings()
