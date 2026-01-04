"""Button platform for Dyson IR."""
import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ACTION_CODE,
    CONF_ACTION_NAME,
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    DOMAIN,
)
from .coordinator import DysonIRCoordinator
from .entity import DysonIREntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities."""
    coordinator: DysonIRCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    actions = config_entry.data.get(CONF_ACTIONS, [])

    entities = [
        DysonIRButton(coordinator, config_entry.entry_id, action) for action in actions
    ]

    async_add_entities(entities)


class DysonIRButton(DysonIREntity, ButtonEntity):
    """Button entity for a specific IR action."""

    def __init__(
        self, coordinator: DysonIRCoordinator, entry_id: str, action: dict[str, str]
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry_id)
        self._action_name = action[CONF_ACTION_NAME]
        self._action_code = action[CONF_ACTION_CODE]

        # Override unique_id and name for this specific button
        self._attr_name = (
            f"{coordinator.config_entry.data.get('name')} {self._action_name}"
        )
        self._attr_unique_id = (
            f"{DOMAIN}_{entry_id}_{self._action_name.lower().replace(' ', '_')}"
        )

        # Load blaster config (now a list of actions from ActionSelector)
        self._blaster_actions = coordinator.config_entry.data.get(
            CONF_BLASTER_ACTION, []
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug(
            "Button pressed: %s. Blaster actions: %s", self.name, self._blaster_actions
        )
        if not self._blaster_actions:
            _LOGGER.error("No blaster actions configured")
            return

        import copy

        from homeassistant.helpers import script

        # Deep copy to avoid mutating the original config
        actions = copy.deepcopy(self._blaster_actions)

        def inject_code(obj: Any) -> None:
            """Recursively inject IR code into action data."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if (
                        key in ("command", "code", "value", "payload")
                        and value == "IR_CODE"
                    ):
                        obj[key] = (
                            [self._action_code]
                            if key == "command"
                            else self._action_code
                        )
                        _LOGGER.debug("Injected IR code into %s: %s", key, obj[key])
                    elif isinstance(value, (dict, list)):
                        inject_code(value)
            elif isinstance(obj, list):
                for item in obj:
                    inject_code(item)

        inject_code(actions)

        _LOGGER.debug("Blaster actions to execute after injection: %s", actions)

        try:
            script_obj = script.Script(
                self.hass,
                actions,
                self.name,
                DOMAIN,
            )
            await script_obj.async_run(context=self._context)
            _LOGGER.debug("Executed blaster actions for %s", self._action_name)
        except Exception as err:
            _LOGGER.error(
                "Failed to execute blaster actions for %s: %s", self._action_name, err
            )
