"""Test component setup."""
from homeassistant.setup import async_setup_component

from custom_components.rewire.const import DOMAIN


async def test_async_setup(hass):
    """Test the component gets setup."""
    setup = await async_setup_component(hass, DOMAIN, {})
    assert setup is True
