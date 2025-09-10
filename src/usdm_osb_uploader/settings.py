from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    osb_base_url: str = "http://3.111.176.137:5005/api"

    model_config = SettingsConfigDict()

settings = Settings()