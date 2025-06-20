from ..coordinator import KomodoCoordinator
from base import KomodoSensor
from komodo_api.types import ServerListItem

def create_server_sensors(
    coordinator: KomodoCoordinator, id: str,
) -> list[KomodoSensor]:
    """
    Returns a list of sensors.
    """
    return [
        KomodoSensor(
            coordinator=coordinator,
            extractor= lambda item: item.state,
            category = "server",
            key = "state",
            id = server.id
        ) for server in coordinator.data.servers
    ]
