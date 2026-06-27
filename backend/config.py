from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str
    fernet_key: str
    jwt_secret: str
    google_client_id: str
    resend_api: str
    resend_email_from: str


settings = Settings()
