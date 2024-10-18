import datetime
import os
import re
from pathlib import Path
from typing import Generator


class SiunCriterion:
    """Check if time of last update has exceeded set time period."""

    def is_fulfilled(self, criteria_settings: dict, available_updates: list):
        """Check criterion."""
        regex = re.compile(r"^\[([0-9TZ:\+\-]+)\] \[ALPM\] upgraded.*")
        last_update = False
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        for line in _reverse_readline(Path("/var/log/pacman.log")):
            match = regex.match(line)
            if match:
                last_update = datetime.datetime.fromisoformat(match.group(1))
                break
        return last_update and (last_update + datetime.timedelta(hours=criteria_settings["lastupdate_age_hours"])) < now


def _reverse_readline(filename, buf_size=8192) -> Generator[str, None, None]:
    """Build a generator that returns the lines of a file in reverse order.

    https://stackoverflow.com/a/23646049
    """
    with open(filename, "rb") as fh:
        segment = None
        offset = 0
        fh.seek(0, os.SEEK_END)
        file_size = remaining_size = fh.tell()
        while remaining_size > 0:
            offset = min(file_size, offset + buf_size)
            fh.seek(file_size - offset)
            buffer = fh.read(min(remaining_size, buf_size))
            # Remove file's last "\n" if it exists, only for the first buffer
            if remaining_size == file_size and buffer[-1] == ord("\n"):
                buffer = buffer[:-1]
            remaining_size -= buf_size
            lines = buffer.split(b"\n")
            # Append last chunk's segment to this chunk's last line
            if segment is not None:
                lines[-1] += segment
            segment = lines[0]
            lines = lines[1:]
            # Yield lines in this chunk except the segment
            for line in reversed(lines):
                # Only decode on a parsed line, to avoid utf-8 decode error
                yield line.decode()
        # Don't yield None if the file was empty
        if segment is not None:
            yield segment.decode()
