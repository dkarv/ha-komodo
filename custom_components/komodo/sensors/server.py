from ..coordinator import KomodoCoordinator
from .common import KomodoSensor, KomodoOptionSensor
from komodo_api.types import ServerState

def create_server_sensors(
    coordinator: KomodoCoordinator, 
    id: str,
) -> list[KomodoSensor]:
    """
    Returns a list of sensors.
    """
    return [
        KomodoOptionSensor(
            coordinator=coordinator,
            id = id,
            extractor= lambda item: item.servers[server.name].info.state.name,
            category = "server",
            key = "state",
            name = server.name,
            options = [state.name for state in ServerState],
        ) for server in coordinator.data.servers.values()
    ]
