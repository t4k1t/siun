"""Distro to UpdateProvider mapping."""

from siun.providers import UpdateProvider, UpdateProviderAur, UpdateProviderPacman

DISTRO_MAP: dict[str, list[type[UpdateProvider]]] = {
    "arch": [UpdateProviderAur, UpdateProviderPacman],
    "manjaro": [UpdateProviderAur, UpdateProviderPacman],
    "ubuntu": [],  # No UpdateProvider for apt implemented
    "debian": [],
    "fedora": [],  # No UpdateProvider for dnf/yum implemented
    "centos": [],
    "redhat": [],
    "rhel": [],
}
