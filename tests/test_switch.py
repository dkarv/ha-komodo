from unittest.mock import MagicMock

import pytest
from komodo_api.types import ContainerListItem, ContainerStateStatusEnum, StackState

from custom_components.komodo.data.komodo_data import KomodoData
from custom_components.komodo.switch import (
    create_switch_entities_for_services,
    create_switch_entities_for_stacks,
)

from .test_komodo_data import _stack_item, _stack_service


def _coordinator(container_state):
    item = _stack_item("s1", [("web", False), ("db", False)])
    item.info.state = StackState.RUNNING
    data = KomodoData()
    data.add_stacks([item])
    data.add_stack_services([
        _stack_service("s1", "web", ContainerListItem(name="w", id="c1", state=container_state)),
        # db has no container
        _stack_service("s1", "db"),
    ])
    coordinator = MagicMock()
    coordinator.data = data
    return coordinator


@pytest.mark.parametrize("state,expected", [
    (ContainerStateStatusEnum.RUNNING, True),
    (ContainerStateStatusEnum.EXITED, False),
    (ContainerStateStatusEnum.PAUSED, False),
])
def test_service_switch_state(state, expected):
    switches = create_switch_entities_for_services(MagicMock(), _coordinator(state), "e")
    by_name = {s.name: s for s in switches}
    assert by_name["web"].is_on is expected
    assert by_name["db"].is_on is None


def test_stack_switch_created():
    switches = create_switch_entities_for_stacks(
        MagicMock(), _coordinator(ContainerStateStatusEnum.RUNNING), "e"
    )
    assert [s.unique_id for s in switches] == ["e_s1_stack_switch"]
    assert switches[0].is_on is True


@pytest.mark.asyncio
async def test_query_container_uses_coordinator_id():
    switch = create_switch_entities_for_services(
        MagicMock(), _coordinator(ContainerStateStatusEnum.RUNNING), "e"
    )[0]
    assert await switch.query_container() == "c1"
