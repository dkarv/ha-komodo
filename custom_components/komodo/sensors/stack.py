from ..coordinator import KomodoCoordinator
from .common import KomodoSensor, KomodoOptionSensor, KomodoEntity
from komodo_api.types import StackState
from ..const import DOMAIN
from ..utils import create_stack_device_info

def create_stack_sensors(
    coordinator: KomodoCoordinator, 
    entry_id: str,
) -> list[KomodoSensor]:
    """
    Returns a list of sensors.
    """
    sensors: list[KomodoSensor] = []
    for stack in coordinator.data.stacks.values():
        device_info = create_stack_device_info(stack.id, stack.name, stack.server_id, DOMAIN)

        item_id = f"{entry_id}_{stack.id}"

        def extractor(data, sid=stack.id):
            stk = data.get_stack(sid)
            return stk.state.name

        def joiner(data, sid=stack.id):
            stk = data.get_stack(sid)
            if stk.alerts:
                return ", ".join(stk.alerts)
            return ""

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
        sensors.append(
            KomodoSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=joiner,
                key="alert_list",
                device_info=device_info,
            ) 
        )

    return sensors
