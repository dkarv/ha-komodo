from ..coordinator import KomodoCoordinator
from .base import KomodoSensor

def create_server_sensors(
    coordinator: KomodoCoordinator, id: str,
) -> list[KomodoSensor]:
    """
    Returns a list of sensors.
    """
    return [
        KomodoSensor(
            coordinator=coordinator,
            extractor= lambda item: item.info.state,
            category = "server",
            key = "state",
            id = server.name,
        ) for server in coordinator.data.servers
    ]
