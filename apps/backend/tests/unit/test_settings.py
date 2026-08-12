from common.infrastructure.settings import Settings


def test_settings_exposes_razorpay_keys():
    s = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        razorpay_key_id="rzp_test_abc",
        razorpay_key_secret="rzp_test_secret_xyz",
        razorpay_webhook_secret="whsec_test_123",
    )
    assert s.razorpay_key_id == "rzp_test_abc"
    assert s.razorpay_key_secret == "rzp_test_secret_xyz"
    assert s.razorpay_webhook_secret == "whsec_test_123"
    assert s.payments_provider == "razorpay"  # default


def test_settings_app_url_default():
    """Test that app_url defaults to localhost:5173."""
    s = Settings()
    assert s.app_url == "http://localhost:5173"


def test_settings_app_url_from_env():
    """Test that app_url can be loaded from environment variable."""
    s = Settings(app_url="https://example.com")
    assert s.app_url == "https://example.com"
