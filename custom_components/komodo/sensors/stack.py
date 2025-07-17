from ..coordinator import KomodoCoordinator
from .common import KomodoSensor, KomodoOptionSensor, KomodoEntity
from komodo_api.types import StackState
from homeassistant.components.update import UpdateEntity

def create_stack_sensors(
    coordinator: KomodoCoordinator, 
    id: str,
) -> list[KomodoSensor]:
    """
    Returns a list of sensors.
    """
    return [
        KomodoOptionSensor(
            coordinator=coordinator,
            id=id,
            extractor= lambda item: item.stacks[stack.name].info.state.name,
            category = "stack",
            key = "state",
            name = stack.name,
            options = [state.name for state in StackState],
        ) for stack in coordinator.data.stacks.values()
    ]
