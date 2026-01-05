import copy
import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import script
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ACTION_TYPE_BUTTON,
    CONF_ACTION_CODE,
    CONF_ACTION_NAME,
    CONF_ACTION_TYPE,
    CONF_ACTIONS,
    CONF_BLASTER_ACTION,
    DOMAIN,
)
from .coordinator import RewireCoordinator
from .entity import RewireEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entity."""
    coordinator: RewireCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    actions = config_entry.data.get(CONF_ACTIONS, [])

    entities = []
    for action in actions:
        if action.get(CONF_ACTION_TYPE) == ACTION_TYPE_BUTTON:
            entities.append(RewireButton(coordinator, config_entry.entry_id, action))

    async_add_entities(entities)


class RewireButton(RewireEntity, ButtonEntity):
    """Button representation of a stateless button."""

    def __init__(self, coordinator: RewireCoordinator, entry_id: str, action: dict[str, Any]) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry_id)
        self._action_name = action[CONF_ACTION_NAME]
        self._action_code = action[CONF_ACTION_CODE]

        # Override unique_id and name for this specific button
        self._attr_name = f"{coordinator.config_entry.data.get('name')} {self._action_name}"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{self._action_name.lower().replace(' ', '_')}"

        # Load blaster config (now a list of actions from ActionSelector)
        self._blaster_actions = coordinator.config_entry.data.get(CONF_BLASTER_ACTION, [])

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug("Button pressed: %s. Blaster actions: %s", self.name, self._blaster_actions)
        if not self._blaster_actions:
            _LOGGER.error("No blaster actions configured")
            return

        actions = copy.deepcopy(self._blaster_actions)

        def inject_code(obj: Any) -> None:
            """Recursively inject IR code into action data."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ("command", "code", "value", "payload") and value == "IR_CODE":
                        obj[key] = [self._action_code] if key == "command" else self._action_code
                        _LOGGER.debug("Injected IR code into %s: %s", key, obj[key])
                    elif isinstance(value, (dict, list)):
                        inject_code(value)
            elif isinstance(obj, list):
                for item in obj:
                    inject_code(item)

        inject_code(actions)

        _LOGGER.debug("Blaster actions to execute after injection: %s", actions)

        # Execute actions
        for action in actions:
            # Handle Service Call (preferred for new config flow)
            if "service" in action:
                try:
                    domain, service_name = action["service"].split(".", 1)
                    target = action.get("target")
                    data = action.get("data")

                    _LOGGER.debug(
                        "Calling service %s.%s with data %s and target %s",
                        domain,
                        service_name,
                        data,
                        target,
                    )

                    await self.hass.services.async_call(
                        domain,
                        service_name,
                        service_data=data,
                        target=target,
                        context=self._context,
                        blocking=True,
                    )
                except Exception as err:
                    _LOGGER.error("Failed to execute service call %s: %s", action["service"], err)

            # Fallback for Device Actions or other script syntax (Old Config)
            else:
                try:
                    # Wrap single action in list for script
                    script_obj = script.Script(
                        self.hass,
                        [action],
                        self.name,
                        DOMAIN,
                    )
                    await script_obj.async_run(context=self._context)
                except Exception as err:
                    _LOGGER.error("Failed to execute script action %s: %s", action, err)
            _LOGGER.debug("Executed blaster actions for %s", self._action_name)
