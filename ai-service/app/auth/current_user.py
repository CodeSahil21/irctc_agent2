from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    email: str | None = None
    name: str | None = None