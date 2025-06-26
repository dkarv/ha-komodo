from ..coordinator import KomodoCoordinator
from .base import KomodoSensor, KomodoOptionSensor
from komodo_api.types import StackState

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
    ] + [
        KomodoSensor(
            coordinator=coordinator,
            id=id,
            extractor= lambda item: any(service.update_available for service in item.stacks[stack.name].info.services),
            category = "stack",
            key = "updateavailable",
            name = stack.name,
        ) for stack in coordinator.data.stacks.values()
    ]
