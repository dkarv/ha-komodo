from ..coordinator import KomodoCoordinator
from .base import KomodoSensor

def create_stack_sensors(
    coordinator: KomodoCoordinator, id: str,
) -> list[KomodoSensor]:
    """
    Returns a list of sensors.
    """
    return [
        KomodoSensor(
            coordinator=coordinator,
            extractor= lambda item: item.info.state,
            category = "stack",
            key = "state",
            id = stack.name,
        ) for stack in coordinator.data.stacks
    ] + [
        KomodoSensor(
            coordinator=coordinator,
            extractor= lambda item: any(service.update_available for service in item.info.services),
            category = "stack",
            key = "updateavailable",
            id = stack.name,
        ) for stack in coordinator.data.stacks
    ]
