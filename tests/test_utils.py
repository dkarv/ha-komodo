import pytest

from custom_components.komodo.utils import (
    clean_image_name,
    extract_version_from_env,
    extract_version_from_image_tag,
    extract_version_from_labels,
    fix_host,
    parse_docker_percent,
    parse_docker_size,
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

