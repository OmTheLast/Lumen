import time

from lumen.tasks import TaskEngine, TaskStore


def test_task_store_persists_tasks(tmp_path):
    path = tmp_path / "tasks.json"
    store = TaskStore(path)

    task = store.create("open a new tab")
    store.mark_done(task.id, "Opened tab.")

    restored = TaskStore(path)
    tasks = restored.list()

    assert len(tasks) == 1
    assert tasks[0].objective == "open a new tab"
    assert tasks[0].status == "done"
    assert tasks[0].result == "Opened tab."


def test_task_engine_runs_submitted_task(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    engine = TaskEngine(store, lambda objective: f"ran {objective}")

    engine.start()
    task = engine.submit("reload tab")
    deadline = time.time() + 2
    while time.time() < deadline:
        updated = store.get(task.id)
        if updated and updated.status == "done":
            break
        time.sleep(0.02)
    engine.stop()

    updated = store.get(task.id)
    assert updated is not None
    assert updated.status == "done"
    assert updated.result == "ran reload tab"


def test_task_store_requeues_running_tasks_on_restart(tmp_path):
    store = TaskStore(tmp_path / "tasks.json")
    task = store.create("continue work")
    store.mark_running(task.id)

    restored = TaskStore(tmp_path / "tasks.json")
    tasks = restored.requeue_unfinished()

    assert tasks[0].id == task.id
    assert restored.get(task.id).status == "queued"
