from unittest.mock import MagicMock

import pytest
from homeassistant.const import EntityCategory
from komodo_api.types import ContainerListItem, ContainerStateStatusEnum, ContainerStats

from custom_components.komodo.data.komodo_data import KomodoData
from custom_components.komodo.sensors.container import (
    CONTAINER_SENSORS,
    container_sensor_category,
    create_container_sensors,
)
from custom_components.komodo.const import (
    CONF_CONTAINER_CPU,
    CONF_CONTAINER_DISK,
    CONF_CONTAINER_ENTITIES,
    CONF_CONTAINER_MEMORY,
    CONF_CONTAINER_NETWORK,
    CONTAINER_CATEGORIES,
    enabled_container_categories,
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
    sensors = _by_id(create_container_sensors(_coordinator(), "e", frozenset()))
    assert sensors["e_s1_web_container_cpu_usage"].native_value == 1.0
    assert sensors["e_s1_web_container_memory_used"].native_value == 12 * 1024**2
    assert sensors["e_s1_web_container_network_rx"].native_value == 1500
    assert sensors["e_s1_web_container_network_tx"].native_value == 2_000_000
    assert sensors["e_s1_web_container_block_read"].native_value == 0
    assert sensors["e_s1_web_container_block_write"].native_value == 8000
    for key in CONTAINER_SENSORS:
        assert sensors[f"e_s1_db_{key}"].native_value is None


@pytest.mark.parametrize(
    "enabled",
    [frozenset(), frozenset(CONTAINER_CATEGORIES), frozenset({CONF_CONTAINER_CPU, CONF_CONTAINER_MEMORY})],
)
def test_container_sensor_attributes(enabled):
    sensors = create_container_sensors(_coordinator(), "e", enabled)
    assert len(sensors) == 2 * len(CONTAINER_SENSORS)
    for sensor in sensors:
        # No state class -> no long-term statistics
        assert sensor.state_class is None
        assert sensor.entity_category == EntityCategory.DIAGNOSTIC
        category = container_sensor_category(sensor.unique_id)
        assert category in CONTAINER_CATEGORIES
        assert sensor.entity_registry_enabled_default is (category in enabled)


def test_container_sensor_category():
    assert container_sensor_category("e_s1_web_container_cpu_usage") == CONF_CONTAINER_CPU
    assert container_sensor_category("e_s1_web_container_memory_used") == CONF_CONTAINER_MEMORY
    assert container_sensor_category("e_s1_web_container_network_tx") == CONF_CONTAINER_NETWORK
    assert container_sensor_category("e_s1_web_container_block_read") == CONF_CONTAINER_DISK
    assert container_sensor_category("e_s1_stack_state") is None
    assert container_sensor_category("e_s1_web_switch") is None
    # server CPU sensor
    assert container_sensor_category("e_srv1_cpu_usage") is None


def test_enabled_container_categories():
    assert enabled_container_categories({}) == frozenset()
    assert enabled_container_categories({CONF_CONTAINER_CPU: True, CONF_CONTAINER_DISK: False}) == {CONF_CONTAINER_CPU}
    # Legacy option enables all categories
    assert enabled_container_categories({CONF_CONTAINER_ENTITIES: True}) == frozenset(CONTAINER_CATEGORIES)
    assert enabled_container_categories({CONF_CONTAINER_ENTITIES: False}) == frozenset()
