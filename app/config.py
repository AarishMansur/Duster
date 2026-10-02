from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./fivegoodones.db"
    companies_file: str = "config/companies.txt"

    classifier: str = "heuristic"
    ollama_base_url: str = "http://localhost:11434"

    backboard_api_key: str = ""
    backboard_base_url: str = "https://app.backboard.io/api"
    backboard_model: str = "llama-3.1-8b-instruct"
    compare_models: str = "llama-3.1-8b-instruct,qwen2.5-7b-instruct,mistral-7b-instruct"

    tinker_api_key: str = ""
    tinker_model_name: str = ""


settings = Settings()
