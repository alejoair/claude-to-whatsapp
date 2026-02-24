"""Data models for scheduled tasks."""

import json
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class ScheduleType(Enum):
    """Tipos de schedule."""
    CRON = "cron"
    ONCE = "once"
    INTERVAL = "interval"


class TaskType(Enum):
    """Tipos de tarea."""
    REMINDER = "reminder"
    ACTION = "action"


@dataclass
class Schedule:
    """Configuración de schedule."""
    type: ScheduleType
    expression: Optional[str] = None  # cron expression
    datetime: Optional[str] = None    # ISO datetime para "once"
    every: Optional[int] = None       # para interval
    unit: Optional[str] = None        # seconds, minutes, hours, days

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "expression": self.expression,
            "datetime": self.datetime,
            "every": self.every,
            "unit": self.unit
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Schedule":
        return cls(
            type=ScheduleType(data["type"]),
            expression=data.get("expression"),
            datetime=data.get("datetime"),
            every=data.get("every"),
            unit=data.get("unit")
        )


@dataclass
class Task:
    """Tarea programada."""
    id: str
    type: TaskType
    schedule: Schedule
    payload: dict
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "schedule": self.schedule.to_dict(),
            "payload": self.payload,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_run": self.last_run,
            "next_run": self.next_run,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"],
            type=TaskType(data["type"]),
            schedule=Schedule.from_dict(data["schedule"]),
            payload=data["payload"],
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_run=data.get("last_run"),
            next_run=data.get("next_run"),
            description=data.get("description")
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Task":
        return cls.from_dict(json.loads(json_str))


def create_reminder_task(
    task_id: str,
    message: str,
    schedule: Schedule,
    description: Optional[str] = None
) -> Task:
    """Crea una tarea de tipo reminder."""
    return Task(
        id=task_id,
        type=TaskType.REMINDER,
        schedule=schedule,
        payload={"message": message},
        description=description
    )


def create_action_task(
    task_id: str,
    prompt: str,
    schedule: Schedule,
    description: Optional[str] = None
) -> Task:
    """Crea una tarea de tipo action (ejecuta prompt con Claude)."""
    return Task(
        id=task_id,
        type=TaskType.ACTION,
        schedule=schedule,
        payload={"prompt": prompt},
        description=description
    )
