from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATA_SCHEDULER_URI: str = "data_scheduler:50051"
    ERGAST_API_URL: str = "https://api.jolpi.ca/ergast/f1"
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
