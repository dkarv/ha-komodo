import asyncio
from unittest.mock import MagicMock, patch

from homeassistant.components.update import UpdateEntityFeature
from releaseprobe import InvalidImageReferenceError, ReleaseInfo, UnknownVersionError, UpdateCheck
from releaseprobe.changelog import ReleaseNote

from custom_components.komodo import coordinator as coordinator_module
from custom_components.komodo.coordinator import KomodoCoordinator
from custom_components.komodo.data.service import (
    FAILURE_RETRY_BASE,
    UPDATE_INFO_TTL,
    KomodoUpdateInfo,
)
from custom_components.komodo.update import KomodoUpdateEntity

SOURCE = "https://github.com/org/app"


def _check(**kwargs):
    defaults = dict(
        image="ghcr.io/org/app:latest",
        current_version="1.0.0",
        latest_version="1.1.0",
        current_info=ReleaseInfo(version="24.04", source=SOURCE),
    )
    return UpdateCheck(**{**defaults, **kwargs})


def test_apply_release_info_uses_resolved_version_not_label():
    info = KomodoUpdateInfo(0)
    info.apply_labels({"org.opencontainers.image.version": "24.04"})
    note = ReleaseNote(version="v1.1.0", name="Release 1.1", url="https://rel", body="text")
    info.apply_release_info(_check(release_notes=[note]))

    assert info.current_version == "1.0.0"
    assert info.new_version == "1.1.0"
    assert info.release_summary == "Release 1.1"
    assert info.release_url == "https://rel"
    assert "text" in info.release_notes


def test_apply_release_info_without_notes_falls_back_to_source():
    info = KomodoUpdateInfo(0)
    info.apply_release_info(_check())

    assert info.release_notes is None
    assert info.release_url == SOURCE


def test_apply_release_info_same_version_explains_rebuild():
    info = KomodoUpdateInfo(0)
    info.apply_release_info(_check(latest_version=None))

    assert info.new_version == "update available"
    assert "no new version" in info.release_summary


def test_apply_unknown_version_shows_what_releaseprobe_knows():
    info = KomodoUpdateInfo(0)
    info.apply_labels({"org.opencontainers.image.version": "main"})
    err = UnknownVersionError(
        "nope",
        tag="latest",
        digests=["ghcr.io/org/app@sha256:0123456789abcdef"],
        current_info=ReleaseInfo(source=SOURCE),
        reason="floating tag 'latest', no version label",
    )
    info.apply_unknown_version(err, {})

    assert info.current_version == "latest (sha256:0123456789ab)"
    assert info.release_summary == (
        "Couldn't determine the installed version (floating tag 'latest', no version label)"
    )
    assert info.release_url == SOURCE
    assert info.refresh_after == UPDATE_INFO_TTL


def test_apply_invalid_image_shows_digest():
    info = KomodoUpdateInfo(0)
    info.apply_invalid_image(
        InvalidImageReferenceError("'app' has no explicit tag"),
        {"org.opencontainers.image.source": SOURCE},
        ["app@sha256:0123456789abcdef"],
    )

    assert info.current_version == "sha256:0123456789ab"
    assert "no explicit tag" in info.release_summary
    assert info.release_url == SOURCE


def test_apply_failure_backs_off():
    info = KomodoUpdateInfo(0)
    info.apply_failure({}, "HTTP 429")
    assert info.refresh_after == FAILURE_RETRY_BASE
    assert info.failures == 1
    assert "HTTP 429" in info.release_summary
    assert info.is_fresh(FAILURE_RETRY_BASE - 1)
    assert not info.is_fresh(FAILURE_RETRY_BASE)

    # The next probe inherits the failure count and waits twice as long.
    retry = KomodoUpdateInfo(0, info.failures)
    retry.apply_failure({}, "HTTP 429")
    assert retry.refresh_after == 2 * FAILURE_RETRY_BASE

    many = KomodoUpdateInfo(0, 20)
    many.apply_failure({}, "boom")
    assert many.refresh_after == UPDATE_INFO_TTL

    retry.apply_release_info(_check())
    assert retry.failures == 0


def _coordinator():
    coordinator = object.__new__(KomodoCoordinator)

    async def run_in_executor(job):
        return job()

    coordinator.hass = MagicMock()
    coordinator.hass.async_add_executor_job = run_in_executor
    return coordinator


def test_probe_passes_digests_and_tags_cache():
    info = KomodoUpdateInfo(0)
    cache = {}
    with patch.object(coordinator_module, "check_for_update", return_value=_check()) as mock_check:
        asyncio.run(
            _coordinator()._probe_release_info(
                info, "ghcr.io/org/app:latest", {}, ["sha256:abc"], cache
            )
        )

    assert mock_check.call_args.kwargs["current_digests"] == ["sha256:abc"]
    assert mock_check.call_args.kwargs["tags_cache"] is cache
    assert info.new_version == "1.1.0"


def test_probe_unknown_version_is_shown():
    info = KomodoUpdateInfo(0)
    with patch.object(
        coordinator_module,
        "check_for_update",
        side_effect=UnknownVersionError("nope", tag="main", reason="floating tag 'main'"),
    ):
        asyncio.run(
            _coordinator()._probe_release_info(info, "ghcr.io/org/app:main", {}, [], {})
        )

    assert info.current_version == "main"
    assert "floating tag 'main'" in info.release_summary
    assert "Couldn't determine" in info.release_summary
    assert info.refresh_after == UPDATE_INFO_TTL


def test_probe_transient_failure_retries_sooner():
    info = KomodoUpdateInfo(0)
    with patch.object(
        coordinator_module, "check_for_update", side_effect=RuntimeError("HTTP 429")
    ):
        asyncio.run(
            _coordinator()._probe_release_info(info, "ghcr.io/org/app:v1", {}, [], {})
        )

    assert info.refresh_after == FAILURE_RETRY_BASE
    assert "HTTP 429" in info.release_summary


def _entity_with(update_info):
    entity = object.__new__(KomodoUpdateEntity)
    entity._service_name = "app"
    service = MagicMock()
    service.update_info = update_info
    entity._find_service = lambda: service
    return entity


def test_release_notes_feature_only_with_notes():
    info = KomodoUpdateInfo(0)
    entity = _entity_with(info)
    entity._update_attrs()
    assert entity.supported_features == UpdateEntityFeature.INSTALL

    info.release_notes = "## 1.1.0"
    entity._update_attrs()
    assert entity.supported_features == (
        UpdateEntityFeature.INSTALL | UpdateEntityFeature.RELEASE_NOTES
    )


def _installing_entity(check_side_effect=None):
    entity = _entity_with(KomodoUpdateInfo(0))
    entity._stack_id = "stack-id"
    entity._stack_name = "immich"
    entity._service_name = "immich-machine-learning"
    calls = []
    api = MagicMock()

    async def deploy(params):
        calls.append(("deploy", params))
        return MagicMock()

    async def check(params):
        calls.append(("check", params))
        if check_side_effect:
            raise check_side_effect

    async def refresh():
        calls.append(("refresh", None))

    async def wait(api, update, description):
        return update

    api.execute.deployStack = deploy
    api.write.checkStackForUpdate = check
    entity.coordinator = MagicMock()
    entity.coordinator.my_api = api
    entity.coordinator.async_refresh = refresh
    return entity, calls, wait


def test_install_deploys_one_service_then_rechecks_stack():
    entity, calls, wait = _installing_entity()
    with patch("custom_components.komodo.update.wait_for_completion", wait):
        asyncio.run(entity.async_install(None, False))

    assert [name for name, _ in calls] == ["deploy", "check", "refresh"]
    assert calls[0][1].services == ["immich-machine-learning"]
    assert calls[1][1].stack == "stack-id"
    assert calls[1][1].skip_auto_update is True


def test_install_refreshes_even_if_recheck_fails():
    entity, calls, wait = _installing_entity(RuntimeError("forbidden"))
    with patch("custom_components.komodo.update.wait_for_completion", wait):
        asyncio.run(entity.async_install(None, False))

    assert [name for name, _ in calls] == ["deploy", "check", "refresh"]
