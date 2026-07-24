"""Distro to UpdateProvider mapping."""

from collections.abc import Callable

from siun.providers import UpdateProvider, UpdateProviderAur, UpdateProviderPacman

DISTRO_MAP: dict[str, list[Callable[[], UpdateProvider]]] = {
    "arch": [UpdateProviderAur, UpdateProviderPacman],
    "manjaro": [UpdateProviderAur, UpdateProviderPacman],
    "ubuntu": [],  # No UpdateProvider for apt implemented
    "debian": [],
    "fedora": [],  # No UpdateProvider for dnf/yum implemented
    "centos": [],
    "redhat": [],
    "rhel": [],
}
