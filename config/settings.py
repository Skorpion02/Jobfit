from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # LM Studio configuration
    lmstudio_base_url: str = "http://localhost:1234/v1"
    lmstudio_model: str = "local-model"  # Se seleccionará el primer modelo disponible
    use_lmstudio: bool = True  # Priorizar LM Studio por defecto
    
    # Model configurations
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model: str = "gpt-4o-mini"
    
    # Scraping settings
    scraping_timeout: int = 30
    max_retries: int = 3
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Processing limits
    max_cv_size_mb: int = 10
    max_job_description_length: int = 10000
    
    # Matching thresholds
    semantic_similarity_threshold: float = 0.7
    exact_match_threshold: float = 0.9
    
    # Export settings
    export_format: str = "docx"
    template_path: str = "data/templates/"
    temp_path: str = "data/temp/"
    
    class Config:
        env_file = ".env"

settings = Settings()