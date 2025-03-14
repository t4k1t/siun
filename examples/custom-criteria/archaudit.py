"""Check arch-audit for vulnerable packages."""

import subprocess


class SiunCriterion:
    """Custom criterion."""

    def is_fulfilled(self, criteria_settings: dict, available_updates: list):
        """Check if any available updates are in arch-audit list."""
        audit_packages = []
        arch_audit_run = subprocess.run(  # noqa: S603
            ["/usr/bin/arch-audit", "-q", "-u"],  # -u only reports vulnerable packages for which updates are available
            check=True,
            capture_output=True,
            text=True,
        )
        audit_packages = arch_audit_run.stdout.splitlines()

        return bool(set(available_updates) & set(audit_packages))
