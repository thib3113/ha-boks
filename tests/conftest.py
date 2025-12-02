"""Fixtures for Boks integration tests."""
import pytest

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the custom_components dir."""
    yield