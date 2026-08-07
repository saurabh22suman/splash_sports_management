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
    assert s.payments_provider == "razorpay"     # default
