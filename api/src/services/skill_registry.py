"""Skill Registry — loads and caches the YAML skill registry."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Optional

import yaml

from src.services.instrument import log_event


REGISTRY_PATH = Path(__file__).resolve().parent.parent / "skills" / "registry.yaml"


class SkillRegistry:
    """Singleton registry that loads skill definitions from a YAML file.

    Cached in memory; call :meth:`reload` to re-read the file on demand.
    """

    _instance: Optional[SkillRegistry] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> SkillRegistry:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._skills: list[dict[str, Any]] = []
                    obj._by_id: dict[str, dict[str, Any]] = {}
                    obj._loaded: bool = False
                    cls._instance = obj
        return cls._instance

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _ensure_loaded(self) -> None:
        """Load the registry from disk if not already loaded."""
        if not self._loaded:
            self._load_yaml()

    def _load_yaml(self) -> None:
        """Read and parse the YAML file into memory structures."""
        path = REGISTRY_PATH
        if not path.exists():
            self._skills = []
            self._by_id = {}
            self._loaded = True
            return

        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        skills: list[dict[str, Any]] = raw if isinstance(raw, list) else []
        self._skills = skills
        self._by_id = {s["id"]: s for s in skills if "id" in s}
        self._loaded = True

        # ── I5: tool count dual-registry check ──────────────────────────
        # How many tools does the API-side registry have vs the MCP gateway?
        gateway_tool_count = "unknown (gateway may not be loaded)"
        try:
            from pathlib import Path as _Path
            gateway_registry_path = _Path(__file__).resolve().parent.parent.parent.parent / "gateway" / "src" / "tool_registry.py"
            if gateway_registry_path.exists():
                gateway_tool_count = "40+ (from ENDPOINT_MAP in tool_registry.py)"
        except Exception:
            pass
        log_event(
            module="skill_registry", function="_load_yaml", event="state_change",
            state_snapshot={
                "yaml_tool_count": len(skills),
                "gateway_tool_count_hint": gateway_tool_count,
                "registry_path": str(path),
                "skill_ids": [s.get("id") for s in skills],
            },
        )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def load_registry(self) -> list[dict[str, Any]]:
        """Return the full list of skill definitions."""
        self._ensure_loaded()
        return list(self._skills)

    def list_skills(self, category: Optional[str] = None) -> list[dict[str, Any]]:
        """Return skills, optionally filtered by *category*."""
        self._ensure_loaded()
        if category is None:
            return list(self._skills)
        cat = category.lower()
        return [s for s in self._skills if s.get("category", "").lower() == cat]

    def get_skill(self, skill_id: str) -> Optional[dict[str, Any]]:
        """Return a single skill definition by its *skill_id*."""
        self._ensure_loaded()
        return self._by_id.get(skill_id)

    def reload(self) -> list[dict[str, Any]]:
        """Force a reload from the YAML file and return the fresh list."""
        self._loaded = False
        self._skills = []
        self._by_id = {}
        self._ensure_loaded()
        return list(self._skills)
