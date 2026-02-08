from ..coordinator import KomodoCoordinator
from .common import KomodoSensor, KomodoOptionSensor, KomodoEntity
from komodo_api.types import StackState
from homeassistant.components.update import UpdateEntity
from homeassistant.helpers.device_registry import DeviceInfo
from ..const import DOMAIN

def create_stack_sensors(
    coordinator: KomodoCoordinator, 
    entry_id: str,
) -> list[KomodoSensor]:
    """
    Returns a list of sensors.
    """
    sensors: list[KomodoSensor] = []
    for stack in coordinator.data.stacks.values():
        device_info = DeviceInfo(
            identifiers={(DOMAIN, stack.id)},
            name=stack.name,
            manufacturer="Komodo",
            via_device=(DOMAIN, stack.server_id),
        )

        item_id = f"{entry_id}_{stack.id}"

        def extractor(data, sid=stack.id):
            stk = data.get_stack(sid)
            return stk.state.name

        sensors.append(
            KomodoOptionSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=extractor,
                key="stack_state",
                device_info=device_info,
                options=[state.name for state in StackState],
            )
        )

    return sensors
