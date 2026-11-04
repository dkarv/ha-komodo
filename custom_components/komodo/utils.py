import ipaddress
import re
import asyncio
from komodo_api.lib import KomodoClient
from komodo_api.types import Update, UpdateStatus, GetUpdate
from typing import TYPE_CHECKING
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN

if TYPE_CHECKING:
    from .data.stack import KomodoStack

import logging

_LOGGER = logging.getLogger(__name__)

# DeviceInfo accepts via_device_id (replacing the deprecated via_device) since HA 2026.8.
_SUPPORTS_VIA_DEVICE_ID = (MAJOR_VERSION, MINOR_VERSION) >= (2026, 8)


def create_stack_device_info(
    stack: "KomodoStack", server_device_ids: dict[str, str],
) -> DeviceInfo:
    """Create device info for a stack, linked to the device of its server."""
    device_info = DeviceInfo(
        identifiers={(DOMAIN, stack.id)},
        name=stack.name,
        manufacturer="Komodo",
    )
    if not _SUPPORTS_VIA_DEVICE_ID:
        device_info["via_device"] = (DOMAIN, stack.server_id)
    elif (server_device_id := server_device_ids.get(stack.server_id)) is not None:
        device_info["via_device_id"] = server_device_id
    return device_info


def fix_host(host: str) -> str:
    """Normalize the host by adding a protocol."""

    host = host.rstrip("/")

    # If already has a protocol scheme, return as-is
    if host.startswith(("http://", "https://")):
        return host

    try:
        ipaddress.ip_address(host)
        return f"http://{host}"
    except ValueError:
        return f"https://{host}"


async def wait_for_completion(client: KomodoClient, update: Update, title: str):
    while not update.status == UpdateStatus.COMPLETE:
        await asyncio.sleep(1)
        update = await client.read.getUpdate(GetUpdate(id=update.id.oid))

    if update.success:
        _LOGGER.info("%s successful", title)
    else:
        logs = "\n".join(
            f"[{log.stage}] {log.stderr} {log.stdout}" for log in update.logs
        )
        _LOGGER.error("%s failed. Logs:\n%s", title, logs)
    return update


_DOCKER_SIZE_UNITS = {
    "b": 1,
    "kb": 1000,
    "mb": 1000**2,
    "gb": 1000**3,
    "tb": 1000**4,
    "kib": 1024,
    "mib": 1024**2,
    "gib": 1024**3,
    "tib": 1024**4,
}
_DOCKER_SIZE_RE = re.compile(r"^\s*([0-9]*\.?[0-9]+)\s*([a-zA-Z]+)\s*$")


def parse_docker_size(text: str | None) -> float | None:
    """Parse a docker stats size like '12.5MiB' or '1.2kB' into bytes."""
    if not text:
        return None
    match = _DOCKER_SIZE_RE.match(text)
    if match is None:
        return None
    factor = _DOCKER_SIZE_UNITS.get(match.group(2).lower())
    if factor is None:
        return None
    return float(match.group(1)) * factor


def parse_docker_percent(text: str | None) -> float | None:
    """Parse a docker stats percentage like '1.23%' into a float."""
    if not text:
        return None
    try:
        return float(text.strip().rstrip("%"))
    except ValueError:
        return None


def split_docker_pair(text: str | None) -> tuple[str | None, str | None]:
    """Split a docker stats pair like '1.2kB / 3.4MB' into its two halves."""
    if not text:
        return None, None
    parts = text.split("/")
    if len(parts) != 2:
        return None, None
    return parts[0].strip(), parts[1].strip()


def clean_image_name(img: str | None) -> str:
    """Normalize docker image name by resolving compose variable interpolations."""
    if not img:
        return ""
    # Resolve compose variable patterns like ${VAR:-default} or ${VAR}
    def repl(match: re.Match) -> str:
        default_val = match.group(2)
        if default_val is not None:
            return default_val
        return ""

    cleaned = re.sub(r"\$\{([^}:]+)(?::-([^}]+))?\}", repl, img)
    return cleaned.strip()


def extract_version_from_labels(labels: dict[str, str] | None) -> str | None:
    """Extract a software version from standard container labels."""
    if not labels:
        return None

    # Priority 1: standard OCI / Docker version labels
    for key in (
        "org.opencontainers.image.version",
        "version",
        "image.version",
        "org.label-schema.version",
    ):
        if val := labels.get(key):
            val = val.strip()
            if val and val != "0":
                return val

    # Priority 2: LinuxServer.io build_version format
    if bv := labels.get("build_version"):
        m = re.search(r"version:-\s*([^\s]+)", bv, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val and val != "0":
                return val

    return None


def extract_version_from_env(env: list[str] | None, service_name: str | None = None) -> str | None:
    """Extract software version from container environment variables."""
    if not env:
        return None

    env_dict: dict[str, str] = {}
    for item in env:
        if "=" in item:
            k, v = item.split("=", 1)
            env_dict[k.strip()] = v.strip()

    norm_service = (service_name or "").upper().replace("-", "_")

    # Service-specific matches (e.g. DOCKER_VERSION for dind, REDIS_VERSION for redis)
    if norm_service in ("DIND", "DOCKER") and (ver := env_dict.get("DOCKER_VERSION")):
        return ver

    exact_keys = (
        f"{norm_service}_VERSION",
        "APP_VERSION",
        "APPLICATION_VERSION",
        "VERSION",
        "RELEASE",
        "IMAGE_VERSION",
    )
    for key in exact_keys:
        if ver := env_dict.get(key):
            ver = ver.strip()
            if ver and ver != "0":
                return ver

    # Fallback to any *_VERSION variable with a semver-like value
    ignored_tools = ("BUILDX", "COMPOSE", "INIT", "CLI", "WRAPPER")
    for k, v in env_dict.items():
        k_upper = k.upper()
        if k_upper.endswith("_VERSION") and not any(tool in k_upper for tool in ignored_tools):
            v_clean = v.strip()
            if v_clean and v_clean != "0" and re.search(r"^\d+(\.\d+)+", v_clean):
                return v_clean

    return None


def extract_version_from_image_tag(image: str | None) -> str | None:
    """Extract a version tag from an image reference if not a generic floating tag."""
    if not image or image.startswith("sha256:"):
        return None

    # Strip digest if present
    repo_and_tag = image.split("@")[0]
    if ":" not in repo_and_tag:
        return None

    tag = repo_and_tag.split(":")[-1].strip()
    if not tag or tag in ("latest", "stable", "nightly", "edge", "master", "main"):
        return None

    return tag


def parse_vcs_url(url: str | None) -> str | None:
    """Clean and normalize a VCS/source URL into a browsable HTTP(S) URL."""
    if not url:
        return None

    u = url.strip().removeprefix("git+")

    # SSH format: git@github.com:owner/repo(.git)
    ssh_match = re.search(r"git@([^:]+):([^/#?]+)/([^/#?]+?)(?:\.git)?(?:[#?].*)?$", u)
    if ssh_match:
        host, owner, repo = ssh_match.group(1), ssh_match.group(2), ssh_match.group(3)
        return f"https://{host}/{owner}/{repo}"

    # HTTP/HTTPS format: https://github.com/owner/repo(.git)(#ref)
    http_match = re.search(r"https?://([^/#?]+)/([^/#?]+)/([^/#?]+?)(?:\.git)?(?:[#?].*)?$", u)
    if http_match:
        host, owner, repo = http_match.group(1), http_match.group(2), http_match.group(3)
        return f"https://{host}/{owner}/{repo}"

    return None


def derive_changelog_url(
    image: str | None,
    labels: dict[str, str] | None = None,
    stack_repo_link: str | None = None,
    version: str | None = None,
) -> str | None:
    """Dynamically derive the best changelog or release URL for any container image or stack.

    Supports GitHub releases/tags, GitLab, Bitbucket, Docker Hub, LinuxServer.io, and Git providers.
    Never hardcoded to specific projects; dynamically works across registries and repositories.
    """
    labels = labels or {}

    # Candidate 1: Direct changelog/release label
    for key in (
        "org.opencontainers.image.changelog",
        "org.opencontainers.image.documentation",
        "org.opencontainers.image.url",
    ):
        val = labels.get(key)
        if val:
            val_clean = val.strip()
            # If documentation/url points directly to a changelog or release
            if any(term in val_clean.lower() for term in ("release", "changelog", "tags")):
                return val_clean

    # Candidate 2: VCS source repository label (OCI standard or label-schema)
    source_candidate = (
        labels.get("org.opencontainers.image.source")
        or labels.get("org.label-schema.vcs-url")
        or stack_repo_link
    )
    if source_candidate:
        clean_vcs = parse_vcs_url(source_candidate)
        if clean_vcs:
            if "github.com" in clean_vcs:
                if version and version not in ("0", "update available", "unknown"):
                    tag_candidate = version.removeprefix("v")
                    # Return direct releases tag link or general releases page
                    return f"{clean_vcs}/releases/tag/v{tag_candidate}"
                return f"{clean_vcs}/releases"
            if "gitlab.com" in clean_vcs:
                return f"{clean_vcs}/-/releases"
            return clean_vcs

    # Candidate 3: General project URL label
    if proj_url := labels.get("org.opencontainers.image.url"):
        clean_url = proj_url.strip()
        if clean_url.startswith("http"):
            return clean_url

    # Candidate 4: Registry-based repository link (Docker Hub, GHCR, Quay)
    if image and not image.startswith("sha256:"):
        cleaned_img = clean_image_name(image).split("@")[0].split(":")[0]
        if "/" in cleaned_img:
            parts = cleaned_img.split("/")
            # ghcr.io/owner/repo
            if parts[0] == "ghcr.io" and len(parts) >= 3:
                owner, repo = parts[1], parts[2]
                return f"https://github.com/{owner}/{repo}/releases"
            # quay.io/owner/repo
            if parts[0] == "quay.io" and len(parts) >= 3:
                return f"https://quay.io/repository/{parts[1]}/{parts[2]}"
            # gcr.io or docker.pkg.github.com
            if parts[0] == "docker.pkg.github.com" and len(parts) >= 3:
                return f"https://github.com/{parts[1]}/{parts[2]}/releases"
            # Docker Hub user/repo
            if len(parts) == 2 and "." not in parts[0] and ":" not in parts[0]:
                return f"https://hub.docker.com/r/{parts[0]}/{parts[1]}/tags"
        elif cleaned_img:
            # Official Docker Hub image (e.g. nginx, redis, docker)
            return f"https://hub.docker.com/_/{cleaned_img}/tags"

    return None


