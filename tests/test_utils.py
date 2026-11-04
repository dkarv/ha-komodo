import pytest

from custom_components.komodo.utils import (
    clean_image_name,
    create_stack_device_info,
    derive_changelog_url,
    extract_version_from_env,
    extract_version_from_image_tag,
    extract_version_from_labels,
    fix_host,
    parse_docker_percent,
    parse_docker_size,
    parse_vcs_url,
    split_docker_pair,
)


@pytest.mark.parametrize("input_host,expected", [
    ("http://192.168.1.1", "http://192.168.1.1"),
    ("https://example.com", "https://example.com"),
    ("192.168.1.1", "http://192.168.1.1"),
    ("example.com", "https://example.com"),
    ("192.168.1.1/", "http://192.168.1.1"),
    ("example.com/", "https://example.com"),
    ("http://example.com/", "http://example.com"),
    ("https://192.168.1.1/", "https://192.168.1.1"),
])
def test_fix_host(input_host, expected):
    assert fix_host(input_host) == expected


@pytest.mark.parametrize("text,expected", [
    ("12.5MiB", 12.5 * 1024**2),
    ("1.2kB", 1200),
    ("0B", 0),
    ("3GB", 3 * 1000**3),
    ("1.5GiB", 1.5 * 1024**3),
    ("--", None),
    ("", None),
    (None, None),
    ("12XB", None),
])
def test_parse_docker_size(text, expected):
    assert parse_docker_size(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("1.2kB / 3.4MB", ("1.2kB", "3.4MB")),
    ("12MiB / 1.9GiB", ("12MiB", "1.9GiB")),
    ("--", (None, None)),
    (None, (None, None)),
])
def test_split_docker_pair(text, expected):
    assert split_docker_pair(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("1.23%", 1.23),
    ("250.5%", 250.5),
    ("0.00%", 0.0),
    ("--", None),
    ("", None),
    (None, None),
])
def test_parse_docker_percent(text, expected):
    assert parse_docker_percent(text) == expected


@pytest.mark.parametrize(
    "raw_img,expected",
    [
        ("docker:29-dind", "docker:29-dind"),
        ("ghcr.io/moghtech/komodo-core:${COMPOSE_KOMODO_IMAGE_TAG:-2}", "ghcr.io/moghtech/komodo-core:2"),
        ("redis:${REDIS_TAG}", "redis:"),
        ("", ""),
        (None, ""),
    ],
)
def test_clean_image_name(raw_img, expected):
    assert clean_image_name(raw_img) == expected


def test_extract_version_from_labels():
    assert extract_version_from_labels({"org.opencontainers.image.version": "1.2.3"}) == "1.2.3"
    assert extract_version_from_labels({"version": "2.0.0"}) == "2.0.0"
    assert extract_version_from_labels({"image.version": "3.1.0"}) == "3.1.0"
    assert extract_version_from_labels({"org.label-schema.version": "4.0.0"}) == "4.0.0"
    assert (
        extract_version_from_labels(
            {"build_version": "Linuxserver.io version:- 12.4ubu2604-ls57 Build-date:- 2026-10-27"}
        )
        == "12.4ubu2604-ls57"
    )
    assert extract_version_from_labels({}) is None
    assert extract_version_from_labels({"org.opencontainers.image.version": "0"}) is None


def test_extract_version_from_env():
    # dind specific
    env_dind = ["DOCKER_VERSION=29.9.1", "DOCKER_BUILDX_VERSION=0.38.0", "DOCKER_COMPOSE_VERSION=5.6.0"]
    assert extract_version_from_env(env_dind, service_name="dind") == "29.9.1"

    # redis specific
    env_redis = ["REDIS_VERSION=7.4.12"]
    assert extract_version_from_env(env_redis, service_name="redis") == "7.4.12"

    # generic APP_VERSION
    assert extract_version_from_env(["APP_VERSION=1.5.0"], service_name="custom") == "1.5.0"

    # fallback to *_VERSION semver
    assert extract_version_from_env(["POSTGRES_VERSION=16.2.1"], service_name="db") == "16.2.1"

    # ignore build tools
    assert extract_version_from_env(["DOCKER_BUILDX_VERSION=0.38.0"], service_name="other") is None


def test_extract_version_from_image_tag():
    assert extract_version_from_image_tag("docker:29-dind") == "29-dind"
    assert extract_version_from_image_tag("redis:7-alpine") == "7-alpine"
    assert extract_version_from_image_tag("ghcr.io/org/repo:v1.2.3") == "v1.2.3"
    assert extract_version_from_image_tag("ghcr.io/org/repo:latest") is None
    assert extract_version_from_image_tag("ghcr.io/org/repo:stable") is None
    assert extract_version_from_image_tag("sha256:e39da29cc49bd85cabdc2fcb223e8d565048cf47cf4af042022d15510badcacd") is None


def test_parse_vcs_url():
    assert parse_vcs_url("https://github.com/astral-sh/uv.git") == "https://github.com/astral-sh/uv"
    assert parse_vcs_url("https://github.com/docker-library/docker.git#3e782bb:29/dind") == "https://github.com/docker-library/docker"
    assert parse_vcs_url("git@github.com:owner/repo.git") == "https://github.com/owner/repo"
    assert parse_vcs_url("https://gitlab.com/group/project.git") == "https://gitlab.com/group/project"
    assert parse_vcs_url(None) is None


def test_derive_changelog_url():
    # 1. From OCI source label with GitHub
    labels_gh = {"org.opencontainers.image.source": "https://github.com/owner/my-app.git"}
    assert derive_changelog_url("my-app:latest", labels=labels_gh, version="1.2.3") == "https://github.com/owner/my-app/releases/tag/v1.2.3"
    assert derive_changelog_url("my-app:latest", labels=labels_gh) == "https://github.com/owner/my-app/releases"

    # 2. From Komodo stack repo_link
    assert derive_changelog_url("my-app:latest", stack_repo_link="https://github.com/fabian/stack-repo") == "https://github.com/fabian/stack-repo/releases"

    # 3. From ghcr image reference
    assert derive_changelog_url("ghcr.io/faserf/hermes-agent-hub:latest") == "https://github.com/faserf/hermes-agent-hub/releases"

    # 4. From official Docker Hub image reference
    assert derive_changelog_url("redis:alpine") == "https://hub.docker.com/_/redis/tags"
    assert derive_changelog_url("docker:29-dind") == "https://hub.docker.com/_/docker/tags"

    # 5. From Docker Hub community image reference
    assert derive_changelog_url("tailscale/tailscale:latest") == "https://hub.docker.com/r/tailscale/tailscale/tags"

    # 6. From direct documentation / changelog label
    labels_doc = {"org.opencontainers.image.documentation": "https://docs.myproject.org/changelog"}
    assert derive_changelog_url("myproject:1.0", labels=labels_doc) == "https://docs.myproject.org/changelog"


def test_create_stack_device_info_configuration_url():
    from unittest.mock import MagicMock
    stack = MagicMock()
    stack.id = "s1"
    stack.name = "jarvis"
    stack.server_id = "srv1"
    stack.deployed_hash = "641203c12345678"
    stack.branch = "main"

    # With base_url and deployed_hash
    info = create_stack_device_info(stack, {"srv1": "dev_srv1"}, base_url="https://komodo.example.com")
    assert info["configuration_url"] == "https://komodo.example.com/stacks/s1"
    assert info["sw_version"] == "641203c1"

    # Without deployed_hash and branch="main", sw_version should be None (no "Firmware: main")
    stack.deployed_hash = None
    info_branch_main = create_stack_device_info(stack, {"srv1": "dev_srv1"})
    assert info_branch_main["sw_version"] is None

    # With a custom non-default branch, sw_version should be the branch
    stack.branch = "feature/awesome"
    info_branch_custom = create_stack_device_info(stack, {"srv1": "dev_srv1"})
    assert info_branch_custom["sw_version"] == "feature/awesome"

    # Without base_url
    info_no_url = create_stack_device_info(stack, {"srv1": "dev_srv1"})
    assert info_no_url.get("configuration_url") is None


def test_create_komodo_main_device_info():
    from unittest.mock import MagicMock

    from custom_components.komodo.const import DOMAIN
    from custom_components.komodo.utils import create_komodo_main_device_info

    coordinator = MagicMock()
    coordinator.komodo_version = "2.3.3"
    coordinator.host_url = "https://komodo.example.com"

    info = create_komodo_main_device_info("entry_123", coordinator)
    assert info["identifiers"] == {(DOMAIN, "entry_123")}
    assert info["name"] == "Komodo"
    assert info["manufacturer"] == "Komodo"
    assert info["model"] == "Fleet Controller"
    assert info["sw_version"] == "2.3.3"
    assert info["configuration_url"] == "https://komodo.example.com"


def test_derive_changelog_url_advanced():
    # Suffixes like (update available)
    labels = {"org.opencontainers.image.source": "https://github.com/owner/my-app"}
    assert derive_changelog_url("app", labels=labels, version="1.2.3 (update available)") == "https://github.com/owner/my-app/releases/tag/v1.2.3"

    # Git commit hash
    assert derive_changelog_url("app", labels=labels, version="eacaaad") == "https://github.com/owner/my-app/commit/eacaaad"

    # Generic or empty version
    assert derive_changelog_url("app", labels=labels, version="update available") == "https://github.com/owner/my-app/releases"
    assert derive_changelog_url("app", labels=labels, version="main") == "https://github.com/owner/my-app/releases"





