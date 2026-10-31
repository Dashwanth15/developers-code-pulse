from app.core.config import Settings


def test_settings_defaults():
    """Validates default configuration settings."""
    settings = Settings()
    assert settings.APP_NAME == "Developers Code Pulse"
    assert settings.API_V1_STR == "/api/v1"
    assert "http://localhost:3000" in settings.CORS_ORIGINS


def test_cors_origins_parsing():
    """Tests CORS origin string parsing."""
    settings = Settings(CORS_ORIGINS=["https://app.dcp.io", "http://localhost:3000"])
    assert len(settings.CORS_ORIGINS) == 2
    assert "https://app.dcp.io" in settings.CORS_ORIGINS
