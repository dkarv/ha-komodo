import pytest
from unittest.mock import MagicMock

from komodo_api.types import StackState

from custom_components.komodo.data.stack import KomodoStack


def _stack_with_state(state):
    item = MagicMock()
    item.info.state = state
    item.id = "stack_id"
    item.name = "stack"
    item.info.server_id = "server_id"
    return KomodoStack(item)


# Only DOWN (not deployed) and UNKNOWN (server unreachable) have no container.
# Every other state, and every future-added state, is inspectable.
@pytest.mark.parametrize("state,expected", [
    (StackState.DEPLOYING, True),
    (StackState.RUNNING, True),
    (StackState.PAUSED, True),
    (StackState.STOPPED, True),
    (StackState.CREATED, True),
    (StackState.RESTARTING, True),
    (StackState.DEAD, True),
    (StackState.REMOVING, True),
    (StackState.UNHEALTHY, True),
    (StackState.DOWN, False),
    (StackState.UNKNOWN, False),
    (None, False),
])
def test_has_inspectable_container(state, expected):
    assert _stack_with_state(state).has_inspectable_container is expected
