"""Module for desktop notifications."""

from enum import Enum
from string import Template
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from siun.models import FormatObject


# NOTE: The reason for all this INSTALLED_FEATURES logic is to provide a nice
# error message if a user tries to configure the notification without
# installing the required dependencies.
INSTALLED_FEATURES: set[str] = set()

try:
    from dbus import Byte as DBusByte
    from dbus import Interface as DBusInterface
    from dbus import SessionBus

    INSTALLED_FEATURES.add("notification")
except ImportError:
    DBusByte = int  # dbus.Byte is a subtype of int, so this will pass Config validation

# Typing alias for dbus.Byte, so the correct type can be inferred later
NotificationByte: type = cast(type, DBusByte)


class NotificationUrgency(Enum):
    """Urgency levels for notifications."""

    low = NotificationByte(0)
    normal = NotificationByte(1)
    critical = NotificationByte(2)


class UpdateNotification(BaseModel):
    """Desktop notification struct."""

    app_name: str = "siun"
    notification_id: int = 0
    icon: str = Field(default="siun-icon")
    title: str = Field(default="$status_text")
    message: str = Field(default="$available_updates")
    actions: list = []
    hints: dict = {}
    timeout: int = Field(default=5000)
    urgency: NotificationUrgency | None = None
    threshold: str  # NOTE: This field gets validated in the Config model

    model_config = ConfigDict(extra="forbid")

    @field_validator("urgency", mode="before")
    def urgency_must_be_enum(
        cls,
        value: str | None,
    ) -> NotificationUrgency | None:
        """Make sure urgency is a valid NotificationUrgency."""
        if value is None:
            return value

        try:
            urgency: NotificationUrgency = NotificationUrgency[value].value
        except KeyError as err:
            message = f"input should be a valid urgency (low|normal|critical), unable to parse '{value}' as urgency"
            raise ValueError(message) from err
        return urgency

    def show(self):
        """Show notification."""
        session_bus = SessionBus()
        notify = session_bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
        notify_interface = DBusInterface(notify, "org.freedesktop.Notifications")

        notify_interface.Notify(
            self.app_name,
            self.notification_id,
            self.icon,
            self.title,
            self.message,
            self.actions,
            self.hints,
            self.timeout,
        )

    def fill_templates(self, format_object: "FormatObject"):
        """Fill template strings with format variables."""
        title_template = Template(self.title)
        self.title = title_template.safe_substitute(**format_object.model_dump())
        message_template = Template(self.message)
        self.message = message_template.safe_substitute(**format_object.model_dump())
