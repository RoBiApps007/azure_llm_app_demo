from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application settings using Pydantic v2.
    Loads variables from environment or .env file.
    """
    # Project Metadata
    PYTHONPATH: str = Field(..., description="Python path for different located Concerto libraries to reduce import issues")
    PROJECT_NAME: str =  Field(..., description="Name of the project/application")
    LOGGING_DEFAULT_LEVEL: str = Field(..., description="Default logging level for the application")
    LOGGING_APP_ID: str = Field(..., description="Name for the logging configuration")
    LOGGING_FILE_NAME: str = Field(..., description="Filename for logging output")
    LOGGING_MAX_FILE_SIZE: int = Field(..., description="Maximum size of the log file in MB")
    LOGGING_BACKUP_COUNT: int = Field(..., description="Number of backup log files to keep")
    LOGGING_DELIMITER: str = Field(..., description="Delimiter used in log entries")
    LOGGING_DATE_FORMAT: str = Field(..., description="Date format used in log entries")
    LOGGING_SYSLOG_HOST: str = Field(..., description="Hostname for the syslog server")
    LOGGING_SYSLOG_PORT: int = Field(..., description="Port for the syslog server")
    LOGGING_POLL_INTERVAL: float = Field(..., description="Poll interval for the syslog server in seconds")
    LOGGING_IDLE_TIMEOUT_S: int = Field(default=300, description="Idle time in seconds before the syslog server shuts down.")

    # Bi-Lytix Junior Foundry Settings
    LYTIX_JUNIOR_FOUNDRY_KEY: SecretStr = Field(..., description="API Key for Bi-Lytix Junior Foundry endpoint")
    LYTIX_JUNIOR_FOUNDRY_MODEL: str = Field(..., description="Model name for Bi-Lytix Junior Foundry endpoint")
    LYTIX_JUNIOR_FOUNDRY_URL: str = Field(..., description="URL for Bi-Lytix Junior Foundry endpoint")
    LYTIX_JUNIOR_FOUNDRY_MODEL_VERSION: str = Field(..., description="Model version for Bi-Lytix Junior Foundry endpoint")
    # OpenAI Settings
    OPENAI_API_KEY: SecretStr = Field(..., description="API Key for OpenAI services")
    DB_DOCS_LIMIT: int = Field(..., description="Maximum number of documents allowed in the vector database")
    USER_AGENT: str = Field(..., description="User agent string for HTTP requests")
    # Embedding Model Settings
    EMBEDDING_MODEL: str = Field(..., description="Model name for embedding generation")
    EMBEDDING_MODEL_VERSION: str = Field(..., description="Version of the embedding model")

    # Google Gemini APUI Settings
    GEMINI_API_KEY: SecretStr = Field(..., description="API Key for Google Gemini API")
    GEMINI_DEFAULT_MODEL: str = Field(..., description="Model name for Google Gemini API")

    # Pydantic Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


def get_settings() -> Settings:
    """
    Returns a cached instance of the settings.
    This pattern allows for easy mocking in tests.
    """
    return Settings()
