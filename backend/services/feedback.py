"""Feedback submission service with compensating rollback semantics."""
from __future__ import annotations

import shutil
import threading
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from backend.paths import get_config_dir, get_data_dir

_evolution_lock = threading.Lock()


class FeedbackTransactionError(RuntimeError):
    """Base error for feedback transaction failures."""


class FeedbackEvolutionBusyError(FeedbackTransactionError):
    """Raised when another feedback evolution is already running."""


@dataclass
class FileSnapshot:
    path: Path
    existed: bool
    data: bytes | None


@dataclass
class DirectorySnapshot:
    path: Path
    existed: bool
    files: dict[str, bytes]


def _snapshot_file(path: Path) -> FileSnapshot:
    if not path.exists():
        return FileSnapshot(path=path, existed=False, data=None)
    return FileSnapshot(path=path, existed=True, data=path.read_bytes())


def _restore_file(snapshot: FileSnapshot) -> None:
    if snapshot.existed:
        snapshot.path.parent.mkdir(parents=True, exist_ok=True)
        snapshot.path.write_bytes(snapshot.data or b"")
        return
    if snapshot.path.exists():
        snapshot.path.unlink()


def _snapshot_directory(path: Path) -> DirectorySnapshot:
    if not path.exists():
        return DirectorySnapshot(path=path, existed=False, files={})
    files: dict[str, bytes] = {}
    for entry in path.rglob("*"):
        if entry.is_file():
            files[str(entry.relative_to(path))] = entry.read_bytes()
    return DirectorySnapshot(path=path, existed=True, files=files)


def _restore_directory(snapshot: DirectorySnapshot) -> None:
    if snapshot.path.exists():
        shutil.rmtree(snapshot.path)
    if not snapshot.existed:
        return
    snapshot.path.mkdir(parents=True, exist_ok=True)
    for relative_path, data in snapshot.files.items():
        output = snapshot.path / relative_path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)


def _target_agents(feedback_type: str) -> list[str]:
    from pipeline.prompt_evolution import EVOLUTION_TARGETS

    return sorted(
        agent_name
        for agent_name, target_types in EVOLUTION_TARGETS.items()
        if feedback_type in target_types
    )


def submit_feedback(
    *,
    issue_date: date,
    feedback_type: str,
    content: str,
) -> dict:
    from pipeline.feedback_store import save_feedback
    from pipeline.llm.client import get_llm_client
    from pipeline.prompt_evolution import evolve_prompt

    data_dir = get_data_dir()
    target_agents = _target_agents(feedback_type)
    feedback_path = data_dir / "feedback" / f"{issue_date.isoformat()}.json"
    feedback_snapshot = _snapshot_file(feedback_path)
    skills_dir = data_dir.parent / "skills"
    skill_snapshots = {
        agent_name: _snapshot_file(skills_dir / f"{agent_name}.md")
        for agent_name in target_agents
    }
    log_snapshots = {
        agent_name: _snapshot_directory(data_dir / "prompt_evolution_log" / agent_name)
        for agent_name in target_agents
    }

    if target_agents and not _evolution_lock.acquire(blocking=False):
        raise FeedbackEvolutionBusyError("feedback evolution already in progress")

    try:
        save_feedback(str(data_dir), issue_date, feedback_type, content)
        if not target_agents:
            return {"ok": True, "evolved_agents": []}

        config_dir = get_config_dir()
        llm_path = config_dir / "llm.yaml"
        if not llm_path.is_file():
            llm_path = config_dir / "llm.yaml.example"
        llm_client = get_llm_client(llm_path)

        evolved_agents: list[str] = []
        for agent_name in target_agents:
            result = evolve_prompt(
                agent_name=agent_name,
                data_dir=str(data_dir),
                skills_dir=skills_dir,
                llm_client=llm_client,
                anchor_date=date.today(),
                force=True,
            )
            if result is None:
                raise FeedbackTransactionError(f"evolution failed for {agent_name}")
            evolved_agents.append(agent_name)
        return {"ok": True, "evolved_agents": evolved_agents}
    except Exception:
        _restore_file(feedback_snapshot)
        for snapshot in skill_snapshots.values():
            _restore_file(snapshot)
        for snapshot in log_snapshots.values():
            _restore_directory(snapshot)
        raise
    finally:
        if target_agents and _evolution_lock.locked():
            _evolution_lock.release()
