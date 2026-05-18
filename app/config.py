from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    adsense_client: str = ""
    rate_limit: str = "10/minute"
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/17.5 Safari/605.1.15"
    )
    media_proxy_allowed_hosts: tuple[str, ...] = (
        "cdninstagram.com",
        "fbcdn.net",
        "threads.com",
        "threads.net",
    )


settings = Settings()
