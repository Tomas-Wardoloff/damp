from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	app_name: str = "Livestock Health API"
	app_env: str = "development"
	app_debug: bool = True
	app_host: str = "0.0.0.0"
	app_port: int = 8000

	database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/livestock"
	ai_service_url: str = "https://damp-machine-learning.onrender.com"
	health_window_size: int = 5
	health_scheduler_enabled: bool = True
	health_scheduler_cycle_minutes: int = 60
	auto_create_tables: bool = True


settings = Settings()
