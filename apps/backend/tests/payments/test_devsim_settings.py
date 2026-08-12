"""Tests for the dev payment simulator settings fields."""
from common.infrastructure.settings import Settings


def test_dev_payment_simulator_enabled_defaults_to_false():
    s = Settings()
    assert s.dev_payment_simulator_enabled is False


def test_dev_state_secret_has_documented_default():
    s = Settings()
    assert s.dev_state_secret == "dev-state-secret-change-me"


def test_dev_payment_simulator_enabled_can_be_overridden():
    s = Settings(dev_payment_simulator_enabled=True)
    assert s.dev_payment_simulator_enabled is True


def test_dev_state_secret_can_be_overridden():
    s = Settings(dev_state_secret="my-custom-secret")
    assert s.dev_state_secret == "my-custom-secret"
