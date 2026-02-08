from komodo_api.types import ServerState
from ..coordinator import KomodoCoordinator
from .common import KomodoSensor, KomodoOptionSensor
from homeassistant.helpers.device_registry import DeviceInfo
from ..const import DOMAIN


def create_server_sensors(
    coordinator: KomodoCoordinator, 
    entry_id: str,
) -> list[KomodoSensor]:
    """Return a list of sensors, one device per server."""
    sensors: list[KomodoSensor] = []
    for server in coordinator.data.servers.values():
        device_info = DeviceInfo(
            identifiers={(DOMAIN, server.id)},
            name=server.name,
            manufacturer="Komodo",
        )

        item_id = f"{entry_id}_{server.id}"

        def extractor(data, sid=server.id):
            srv = data.get_server(sid)
            return srv.state.name

        sensors.append(
            KomodoOptionSensor(
                coordinator=coordinator,
                item_id=item_id,
                extractor=extractor,
                key="server_state",
                device_info=device_info,
                options=[state.name for state in ServerState],
            )
        )

    return sensors
