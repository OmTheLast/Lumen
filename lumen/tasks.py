"""Persistent background task queue for Lumen."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Callable
from uuid import uuid4


TaskRunner = Callable[[str], str]


@dataclass
class TaskEvent:
    time: str
    message: str


@dataclass
class BackgroundTask:
    id: str
    title: str
    objective: str
    status: str = "queued"
    result: str = ""
    error: str = ""
    created_at: str = field(default_factory=lambda: _now())
    updated_at: str = field(default_factory=lambda: _now())
    events: list[TaskEvent] = field(default_factory=list)


class TaskStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self._tasks: dict[str, BackgroundTask] = {}
        self._load()

    def create(self, objective: str, title: str | None = None) -> BackgroundTask:
        objective = objective.strip()
        if not objective:
            raise ValueError("Task objective cannot be empty.")
        task = BackgroundTask(
            id=uuid4().hex[:10],
            title=(title or _title_from_objective(objective)),
            objective=objective,
            events=[TaskEvent(_now(), "Task queued.")],
        )
        with self._lock:
            self._tasks[task.id] = task
            self._save_locked()
            return _copy_task(task)

    def mark_running(self, task_id: str) -> BackgroundTask | None:
        return self._update(task_id, status="running", event="Task started.")

    def mark_done(self, task_id: str, result: str) -> BackgroundTask | None:
        return self._update(task_id, status="done", result=result.strip(), event="Task completed.")

    def mark_failed(self, task_id: str, error: str) -> BackgroundTask | None:
        return self._update(task_id, status="failed", error=error.strip(), event=f"Task failed: {error.strip()}")

    def append_event(self, task_id: str, message: str) -> BackgroundTask | None:
        return self._update(task_id, event=message)

    def get(self, task_id: str) -> BackgroundTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return _copy_task(task) if task is not None else None

    def list(self, limit: int = 12) -> list[BackgroundTask]:
        with self._lock:
            tasks = sorted(self._tasks.values(), key=lambda item: item.created_at, reverse=True)
            return [_copy_task(task) for task in tasks[:limit]]

    def snapshot(self, limit: int = 12) -> dict[str, list[dict[str, object]]]:
        return {"tasks": [task_to_dict(task) for task in self.list(limit=limit)]}

    def requeue_unfinished(self) -> list[BackgroundTask]:
        with self._lock:
            tasks = [
                task
                for task in sorted(self._tasks.values(), key=lambda item: item.created_at)
                if task.status in {"queued", "running"}
            ]
            for task in tasks:
                if task.status == "running":
                    task.status = "queued"
                    task.events.append(TaskEvent(_now(), "Recovered after restart."))
                task.updated_at = _now()
            if tasks:
                self._save_locked()
            return [_copy_task(task) for task in tasks]

    def _update(
        self,
        task_id: str,
        *,
        status: str | None = None,
        result: str | None = None,
        error: str | None = None,
        event: str | None = None,
    ) -> BackgroundTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            if status is not None:
                task.status = status
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            if event:
                task.events.append(TaskEvent(_now(), event))
                task.events = task.events[-24:]
            task.updated_at = _now()
            self._save_locked()
            return _copy_task(task)

    def _load(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return
        raw_tasks = payload.get("tasks") if isinstance(payload, dict) else None
        if not isinstance(raw_tasks, list):
            return
        for item in raw_tasks:
            task = task_from_dict(item)
            if task is not None:
                self._tasks[task.id] = task

    def _save_locked(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"tasks": [task_to_dict(task) for task in self._tasks.values()]}
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class TaskEngine:
    def __init__(self, store: TaskStore, runner: TaskRunner) -> None:
        self.store = store
        self.runner = runner
        self._queue: Queue[str] = Queue()
        self._thread: Thread | None = None
        self._stopping = False

    def start(self) -> None:
        if self._thread is not None:
            return
        for task in self.store.requeue_unfinished():
            self._queue.put(task.id)
        self._thread = Thread(target=self._run, name="lumen-background-tasks", daemon=True)
        self._thread.start()

    def submit(self, objective: str, title: str | None = None) -> BackgroundTask:
        task = self.store.create(objective, title=title)
        self._queue.put(task.id)
        return task

    def stop(self, timeout: float = 1.0) -> None:
        self._stopping = True
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while not self._stopping:
            try:
                task_id = self._queue.get(timeout=0.25)
            except Empty:
                continue
            task = self.store.mark_running(task_id)
            if task is None:
                continue
            try:
                self.store.append_event(task_id, "Planning and executing objective.")
                result = self.runner(task.objective)
            except Exception as exc:
                self.store.mark_failed(task_id, str(exc))
                continue
            self.store.mark_done(task_id, result or "Done.")


def task_to_dict(task: BackgroundTask) -> dict[str, object]:
    payload = asdict(task)
    payload["events"] = [asdict(event) for event in task.events]
    return payload


def task_from_dict(payload: object) -> BackgroundTask | None:
    if not isinstance(payload, dict):
        return None
    task_id = payload.get("id")
    objective = payload.get("objective")
    title = payload.get("title")
    if not isinstance(task_id, str) or not isinstance(objective, str) or not isinstance(title, str):
        return None
    raw_events = payload.get("events")
    events: list[TaskEvent] = []
    if isinstance(raw_events, list):
        for item in raw_events:
            if isinstance(item, dict) and isinstance(item.get("time"), str) and isinstance(item.get("message"), str):
                events.append(TaskEvent(item["time"], item["message"]))
    return BackgroundTask(
        id=task_id,
        title=title,
        objective=objective,
        status=str(payload.get("status") or "queued"),
        result=str(payload.get("result") or ""),
        error=str(payload.get("error") or ""),
        created_at=str(payload.get("created_at") or _now()),
        updated_at=str(payload.get("updated_at") or _now()),
        events=events,
    )


def _copy_task(task: BackgroundTask) -> BackgroundTask:
    return task_from_dict(task_to_dict(task)) or task


def _title_from_objective(objective: str) -> str:
    trimmed = " ".join(objective.split())
    if len(trimmed) <= 54:
        return trimmed
    return f"{trimmed[:51].rstrip()}..."


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
