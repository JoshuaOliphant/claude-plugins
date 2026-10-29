"""Group notifications into batches for delivery.

Notifications are grouped per channel (each channel has its own webhook
path), ordered by score inside the channel, and then cut into chunks of at
most ``batch_size``.
"""

from __future__ import annotations

from collections import defaultdict

from ..domain.models import Batch, Notification


def channel_endpoint(base: str, channel: str) -> str:
    return base.rstrip("/") + "/" + channel


class Batcher:
    def __init__(self, batch_size: int, endpoint: str):
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.batch_size = batch_size
        self.endpoint = endpoint

    def group(self, notifications: list[Notification]) -> dict[str, list[Notification]]:
        groups: dict[str, list[Notification]] = defaultdict(list)
        for note in notifications:
            groups[note.channel].append(note)
        for notes in groups.values():
            notes.sort(key=lambda n: (-n.score, n.ticket_id))
        return dict(sorted(groups.items()))

    def build(self, notifications: list[Notification]) -> list[Batch]:
        batches: list[Batch] = []
        number = 1
        for channel, notes in self.group(notifications).items():
            url = channel_endpoint(self.endpoint, channel)
            for start in range(0, len(notes), self.batch_size):
                chunk = notes[start:start + self.batch_size]
                batches.append(Batch(number, channel, url, chunk))
                number += 1
        return batches
