from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./fivegoodones.db"
    companies_file: str = "config/companies.txt"

    ollama_base_url: str = "http://localhost:11434"

    backboard_api_key: str = ""
    backboard_base_url: str = "https://api.backboard.io"
    backboard_model: str = "llama-3.1-8b-instruct"


settings = Settings()
