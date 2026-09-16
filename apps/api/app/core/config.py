from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    app_name:str="Observatorio de Presión Residencial"
    database_url:str="postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
    cors_origins:str="http://localhost:3000"
    model_config=SettingsConfigDict(env_file=".env",extra="ignore")
    @property
    def origins(self): return [x.strip() for x in self.cors_origins.split(",") if x.strip()]
@lru_cache
def get_settings(): return Settings()
