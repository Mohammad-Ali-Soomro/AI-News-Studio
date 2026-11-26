from backend.app.core.config import Settings, get_settings


def test_config_defaults():
    settings = Settings(_env_file=None)
    assert settings.PROJECT_NAME == "AI News Studio"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.MAX_ARTICLES_PER_FEED == 5
    assert settings.MEDIA_STORAGE_DIR.endswith("media")


def test_config_loads_environment_overrides(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-secret")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    monkeypatch.setenv("MAX_ARTICLES_PER_FEED", "3")
    monkeypatch.setenv("MEDIA_STORAGE_DIR", "./custom_media")

    get_settings.cache_clear()
    try:
        settings = Settings(_env_file=None)
        assert settings.SUPABASE_URL == "https://example.supabase.co"
        assert settings.SUPABASE_SERVICE_ROLE_KEY == "test-secret"
        assert settings.GEMINI_API_KEY == "test-gemini-key"
        assert settings.GEMINI_MODEL == "gemini-test-model"
        assert settings.MAX_ARTICLES_PER_FEED == 3
        assert settings.MEDIA_STORAGE_DIR == "./custom_media"
    finally:
        get_settings.cache_clear()
