from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    env_name: str = "Local"
    base_url: str = "https://scissors-nqsz.onrender.com"
    SQLALCHEMY_DATABASE_URL: str = "postgresql://miwbrjkx:QJomZKQhh0ugvXXC7322wQCUBdJnX0z7@stampy.db.elephantsql.com/miwbrjkx"
    
class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    print(f"Loading settings for: {settings.env_name}")
    return settings