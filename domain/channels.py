from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelMessage:
    channel: str
    user_id: str
    text: str


def normalize_channel_message(channel: str, payload: dict) -> ChannelMessage:
    if channel == "sms":
        return ChannelMessage(channel=channel, user_id=str(payload.get("user_id", "unknown")), text=str(payload.get("message", "")))
    if channel == "email":
        subject = str(payload.get("subject", ""))
        body = str(payload.get("body", payload.get("message", "")))
        return ChannelMessage(channel=channel, user_id=str(payload.get("user_id", "unknown")), text=f"{subject}\n{body}".strip())
    if channel == "voice":
        transcript = str(payload.get("transcript", payload.get("message", "")))
        return ChannelMessage(channel=channel, user_id=str(payload.get("user_id", "unknown")), text=transcript)
    return ChannelMessage(channel=channel, user_id=str(payload.get("user_id", "unknown")), text=str(payload.get("message", "")))
