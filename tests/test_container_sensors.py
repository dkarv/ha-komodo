from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory
from komodo_api.types import ContainerListItem, ContainerStateStatusEnum, ContainerStats

from custom_components.komodo.data.komodo_data import KomodoData
from custom_components.komodo.sensors.container import (
    CONTAINER_SENSORS,
    create_container_sensors,
    is_container_sensor,
)

from .test_komodo_data import _stack_item, _stack_service


def _coordinator():
    data = KomodoData()
    data.add_stacks([_stack_item("s1", [("web", False), ("db", False)])])
    data.add_stack_services([
        _stack_service("s1", "web", ContainerListItem(
            name="w",
            id="c1",
            state=ContainerStateStatusEnum.RUNNING,
            stats=ContainerStats(
                name="w",
                cpu_perc="1.00%",
                mem_perc="2.00%",
                mem_usage="12MiB / 1GiB",
                net_io="1.5kB / 2MB",
                block_io="0B / 8kB",
                pids="3",
            ),
        )),
        # db has no container
        _stack_service("s1", "db"),
    ])
    coordinator = MagicMock()
    coordinator.data = data
    return coordinator


def _by_id(sensors):
    return {s.unique_id: s for s in sensors}


def test_container_sensor_values():
    sensors = _by_id(create_container_sensors(_coordinator(), "e", False))
    assert sensors["e_s1_web_container_cpu_usage"].native_value == 1.0
    assert sensors["e_s1_web_container_memory_used"].native_value == 12 * 1024**2
    assert sensors["e_s1_web_container_network_rx"].native_value == 1500
    assert sensors["e_s1_web_container_network_tx"].native_value == 2_000_000
    assert sensors["e_s1_web_container_block_read"].native_value == 0
    assert sensors["e_s1_web_container_block_write"].native_value == 8000
    for key in CONTAINER_SENSORS:
        assert sensors[f"e_s1_db_{key}"].native_value is None


@pytest.mark.parametrize("enabled", [True, False])
def test_container_sensor_attributes(enabled):
    sensors = create_container_sensors(_coordinator(), "e", enabled)
    assert len(sensors) == 2 * len(CONTAINER_SENSORS)
    for sensor in sensors:
        # No state class -> no long-term statistics
        assert sensor.state_class is None
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        assert sensor.entity_registry_enabled_default is enabled
        assert is_container_sensor(sensor.unique_id)


def test_is_container_sensor():
    assert not is_container_sensor("e_s1_stack_state")
    assert not is_container_sensor("e_s1_web_switch")
    # server CPU sensor
    assert not is_container_sensor("e_srv1_cpu_usage")
