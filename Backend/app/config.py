from pydantic_settings import BaseSettings
import cloudinary
import os
from dotenv import load_dotenv

load_dotenv()

def setup_cloudinary():
    cloudinary.config( 
        cloud_name = settings.cloudinary_name, 
        api_key = settings.cloudinary_api_key, 
        api_secret = settings.cloudinary_api_secret,
        secure = settings.cloudinary_secure
    )

class Settings(BaseSettings):
    database_password: str
    database_port: str
    database_hostname: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    redis_url: str = "redis://localhost:6379/0"
    cloudinary_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    cloudinary_secure: bool
    gmail_app_password: str
    paystack_secret_key: str
    brevo_api_key: str
    google_client_id: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
