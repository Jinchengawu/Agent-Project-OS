"""Runtime adapters kept outside the model-neutral core protocol."""

import hashlib
from importlib import resources
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .records import read_json


ADAPTERS = ("codex", "claude-code", "deepseek-harness")
MANAGED_START = "<!-- AGENT-PROJECT-OS:START -->"
MANAGED_END = "<!-- AGENT-PROJECT-OS:END -->"
DSH_COMMIT = "47f943859bef60e4160492346772ded9b24f765a"
DSH_VERSION = "0.1.0-rc.5"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def skill_text() -> str:
    return resources.files("agent_project_os.templates").joinpath("agent-project-os/SKILL.md").read_text(encoding="utf-8")


def pretty_json(value: Dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def merge_managed_block(existing: str, block: str) -> str:
    managed = "{}\n{}\n{}".format(MANAGED_START, block.rstrip(), MANAGED_END)
    pattern = re.compile(re.escape(MANAGED_START) + r".*?" + re.escape(MANAGED_END), re.DOTALL)
    if pattern.search(existing):
        return pattern.sub(managed, existing)
    if not existing:
        return managed + "\n"
    return existing.rstrip() + "\n\n" + managed + "\n"


def event_bridge_text() -> str:
    return '''#!/usr/bin/env python3
"""Normalize a client hook into an Agent Project OS adapter event."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", required=True)
    parser.add_argument("--normalized-event", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--client-version", required=True)
    parser.add_argument("--model-id")
    parser.add_argument("--provider-hint")
    args = parser.parse_args()
    try:
        raw = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    root = Path.cwd()
    while root.parent != root and not (root / ".agent-project" / "manifest.json").exists():
        root = root.parent
    if not (root / ".agent-project" / "manifest.json").exists():
        return 0
    event_id = "adapter-event-{}".format(uuid.uuid4().hex)
    identity = {"runtime": args.runtime, "client_version": args.client_version}
    if args.model_id:
        identity["model_id"] = args.model_id
    if args.provider_hint:
        identity["provider_hint"] = args.provider_hint
    event = {
        "$schema": "https://agent-project-os.org/schemas/runtime-adapter-event-v1.schema.json",
        "protocol_version": "1.0",
        "adapter_event_id": event_id,
        "adapter": args.adapter,
        "normalized_event": args.normalized_event,
        "session_id": str(raw.get("session_id") or raw.get("sessionId") or "unknown"),
        "runtime_identity": identity,
        "payload": {"source_event": str(raw.get("hook_event_name") or raw.get("type") or "unknown")},
        "occurred_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    destination = root / ".agent-project" / "events" / "{}.json".format(event_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(event, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def claude_settings(existing: Optional[bytes]) -> bytes:
    if existing:
        try:
            value = json.loads(existing.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("existing .claude/settings.json is not valid JSON")
    else:
        value = {}
    if not isinstance(value, dict):
        raise ValueError("existing .claude/settings.json must contain an object")
    hooks = value.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("existing Claude hooks setting must be an object")
    commands = {
        "SessionStart": "python3 .agent-project/adapters/event_bridge.py --adapter claude-code --normalized-event session.started --runtime claude-code --client-version unknown",
        "Stop": "python3 .agent-project/adapters/event_bridge.py --adapter claude-code --normalized-event session.ended --runtime claude-code --client-version unknown",
    }
    for hook_name, command in commands.items():
        entries = hooks.setdefault(hook_name, [])
        if not isinstance(entries, list):
            raise ValueError("Claude hook {} must be an array".format(hook_name))
        managed_entry = {"matcher": "", "hooks": [{"type": "command", "command": command}]}
        filtered = []
        for entry in entries:
            serialized = json.dumps(entry, sort_keys=True) if isinstance(entry, dict) else ""
            if "agent-project-os" not in serialized and "event_bridge.py" not in serialized:
                filtered.append(entry)
        filtered.append(managed_entry)
        hooks[hook_name] = filtered
    return pretty_json(value)


def dsh_plugin_text() -> str:
    return '''import { mkdirSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { randomUUID } from 'node:crypto'

export const name = 'agent-project-os-adapter'

function normalized(type) {
  return {
    'turn/start': 'agent.started',
    'turn/end': 'agent.ended',
    'tool/call': 'tool.started',
    'tool/result': 'tool.ended',
    'session/end-seed': 'session.ended',
  }[type]
}

function writeEvent(config, sessionId, normalizedEvent, sourceEvent, sequence) {
  const projectRoot = resolve(config?.projectRoot || process.cwd())
  const events = join(projectRoot, '.agent-project', 'events')
  mkdirSync(events, { recursive: true })
  const id = `adapter-event-${randomUUID().replaceAll('-', '')}`
  const event = {
    $schema: 'https://agent-project-os.org/schemas/runtime-adapter-event-v1.schema.json',
    protocol_version: '1.0',
    adapter_event_id: id,
    adapter: 'deepseek-harness',
    normalized_event: normalizedEvent,
    session_id: String(sessionId || 'unknown'),
    runtime_identity: {
      runtime: 'deepseek-harness',
      client_version: config?.clientVersion || 'preview-unknown',
    },
    payload: { source_event: String(sourceEvent), ...(sequence === undefined ? {} : { sequence }) },
    occurred_at: new Date().toISOString(),
  }
  writeFileSync(join(events, `${id}.json`), `${JSON.stringify(event, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
}

export function apply(ctx, config) {
  ctx.on('session/created', session => {
    writeEvent(config, session?.id, 'session.started', 'session/created')
  }, { global: true })
  ctx.on('session/event', (session, event) => {
    const mapped = normalized(event?.type)
    if (mapped) writeEvent(config, session?.id, mapped, event?.type, event?.seq)
  }, { global: true })
}
'''


def generated_files(root: Path, adapter: str, user: bool = False) -> Dict[Path, bytes]:
    if adapter not in ADAPTERS:
        raise ValueError("unknown adapter: {}".format(adapter))
    home = Path(os.environ.get("AGENT_PROJECT_OS_USER_HOME", str(Path.home()))).resolve()
    skill = skill_text().encode("utf-8")
    if user:
        if adapter == "codex":
            return {home / ".codex" / "skills" / "agent-project-os" / "SKILL.md": skill}
        if adapter == "claude-code":
            return {home / ".claude" / "skills" / "agent-project-os" / "SKILL.md": skill}
        base = home / ".agent-project-os" / "deepseek-harness" / "agent-project-os-bundle"
    else:
        base = root / ".dsh" / "agent-project-os-bundle"
    if adapter == "codex":
        metadata = {
            "adapter": "codex",
            "adapter_version": "0.1.0a1",
            "status": "supported",
            "instructions": "AGENTS.md",
            "skill_path": ".agents/skills/agent-project-os/SKILL.md",
            "hooks": "optional-not-installed",
        }
        return {
            root / ".agents" / "skills" / "agent-project-os" / "SKILL.md": skill,
            root / ".agent-project" / "adapters" / "codex.json": pretty_json(metadata),
        }
    if adapter == "claude-code":
        claude_path = root / "CLAUDE.md"
        existing_claude = claude_path.read_text(encoding="utf-8") if claude_path.exists() else ""
        block = "@AGENTS.md\n\nShared Agent Project OS rules are imported above. Claude-specific lifecycle events are normalized by project hooks."
        settings_path = root / ".claude" / "settings.json"
        metadata = {
            "adapter": "claude-code",
            "adapter_version": "0.1.0a1",
            "status": "supported",
            "instructions": "CLAUDE.md imports AGENTS.md",
            "skill_path": ".claude/skills/agent-project-os/SKILL.md",
            "hooks": ["SessionStart", "Stop"],
        }
        return {
            claude_path: merge_managed_block(existing_claude, block).encode("utf-8"),
            settings_path: claude_settings(settings_path.read_bytes() if settings_path.exists() else None),
            root / ".claude" / "skills" / "agent-project-os" / "SKILL.md": skill,
            root / ".agent-project" / "adapters" / "event_bridge.py": event_bridge_text().encode("utf-8"),
            root / ".agent-project" / "adapters" / "claude-code.json": pretty_json(metadata),
        }
    package = {
        "name": "agent-project-os-dsh-adapter",
        "version": "0.1.0-alpha.1",
        "private": True,
        "type": "module",
        "main": "index.js",
        "files": ["index.js", "cordis.patch.yml"],
        "dsh": {"bundle": {"patch": "./cordis.patch.yml"}},
    }
    patch = """- insert:
    - id: agent-project-os-adapter
      name: agent-project-os-dsh-adapter
      config:
        projectRoot: !!js process.cwd()
        clientVersion: '{}+{}'
""".format(DSH_VERSION, DSH_COMMIT[:12])
    metadata = {
        "adapter": "deepseek-harness",
        "adapter_version": "0.1.0a1",
        "status": "preview",
        "compatibility": {"upstream_version": DSH_VERSION, "upstream_commit": DSH_COMMIT},
        "bundle_path": ".dsh/agent-project-os-bundle",
        "install_command": "dsh plugin --profile <profile> add ./.dsh/agent-project-os-bundle",
        "verify_command": "dsh --profile <profile> --dump-config",
    }
    readme = """# DeepSeek Harness adapter bundle

Preview adapter pinned to DeepSeek Harness `{version}` at `{commit}`.

Install into an explicit profile:

```sh
dsh plugin --profile <profile> add ./.dsh/agent-project-os-bundle
dsh --profile <profile> --dump-config
```

DeepSeek Harness is in developer preview. Re-render and re-test this adapter when the pinned compatibility point changes; do not change the core Agent Project OS schemas for a client break.
""".format(version=DSH_VERSION, commit=DSH_COMMIT)
    result = {
        base / "package.json": pretty_json(package),
        base / "cordis.patch.yml": patch.encode("utf-8"),
        base / "index.js": dsh_plugin_text().encode("utf-8"),
        base / "README.md": readme.encode("utf-8"),
    }
    if not user:
        result[root / ".agent-project" / "adapters" / "deepseek-harness.json"] = pretty_json(metadata)
    return result


def state_path(root: Path) -> Path:
    return root / ".agent-project" / "adapters" / "install-state.json"


def load_state(root: Path) -> Dict[str, Any]:
    path = state_path(root)
    if not path.exists():
        return {"version": 1, "scopes": {"project": {}, "user": {}}}
    state = read_json(path)
    state.setdefault("scopes", {}).setdefault("project", {})
    state.setdefault("scopes", {}).setdefault("user", {})
    return state


def display_target(root: Path, target: Path, user: bool) -> str:
    if user:
        home = Path(os.environ.get("AGENT_PROJECT_OS_USER_HOME", str(Path.home()))).resolve()
        try:
            return "~/{}".format(target.relative_to(home).as_posix())
        except ValueError:
            return str(target)
    return target.relative_to(root).as_posix()


def backup_target(root: Path, scope: str, adapter: str, target_name: str) -> Path:
    safe = target_name.replace("~/", "user/")
    return root / ".agent-project" / "adapters" / "backups" / scope / adapter / safe


def render_adapters(root: Path, adapters: Iterable[str], user: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    state = load_state(root)
    scope = "user" if user else "project"
    changed: List[str] = []
    for adapter in adapters:
        files = generated_files(root, adapter, user)
        existing_entries = state["scopes"][scope].get(adapter, {}).get("files", [])
        entries_by_target = {entry["target"]: entry for entry in existing_entries}
        next_entries = []
        for target, content in sorted(files.items(), key=lambda item: str(item[0])):
            name = display_target(root, target, user)
            previous = entries_by_target.get(name)
            current = target.read_bytes() if target.exists() else None
            if previous and current is not None and sha256_bytes(current) != previous.get("generated_sha256"):
                if target.name not in {"CLAUDE.md", "settings.json"}:
                    raise ValueError("managed adapter file was modified; refusing to overwrite: {}".format(name))
            entry: Dict[str, Any]
            if previous:
                entry = dict(previous)
            else:
                entry = {"target": name, "created": current is None, "backup": None}
                if current is not None:
                    backup = backup_target(root, scope, adapter, name)
                    entry["backup"] = backup.relative_to(root).as_posix()
                    if not dry_run:
                        backup.parent.mkdir(parents=True, exist_ok=True)
                        backup.write_bytes(current)
            entry["generated_sha256"] = sha256_bytes(content)
            next_entries.append(entry)
            if current != content:
                changed.append(name)
                if not dry_run:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
        if not dry_run:
            state["scopes"][scope][adapter] = {"files": next_entries}
    if not dry_run:
        path = state_path(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pretty_json(state))
    return {"scope": scope, "adapters": list(adapters), "changed": sorted(set(changed))}


def resolve_state_target(root: Path, value: str) -> Path:
    if value.startswith("~/"):
        home = Path(os.environ.get("AGENT_PROJECT_OS_USER_HOME", str(Path.home()))).resolve()
        return home / value[2:]
    return root / value


def uninstall_adapters(root: Path, adapters: Iterable[str], user: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    state = load_state(root)
    scope = "user" if user else "project"
    removed: List[str] = []
    restored: List[str] = []
    skipped: List[str] = []
    for adapter in adapters:
        installation = state["scopes"][scope].get(adapter)
        if not installation:
            continue
        adapter_skipped = []
        for entry in installation.get("files", []):
            target = resolve_state_target(root, entry["target"])
            if target.exists() and sha256_bytes(target.read_bytes()) != entry.get("generated_sha256"):
                skipped.append(entry["target"])
                adapter_skipped.append(entry["target"])
                continue
            backup_value = entry.get("backup")
            if backup_value:
                backup = root / backup_value
                if backup.exists():
                    restored.append(entry["target"])
                    if not dry_run:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(backup.read_bytes())
                        backup.unlink()
            else:
                removed.append(entry["target"])
                if not dry_run and target.exists():
                    target.unlink()
        if not adapter_skipped and not dry_run:
            state["scopes"][scope].pop(adapter, None)
    if not dry_run:
        path = state_path(root)
        if any(state["scopes"][name] for name in ("project", "user")):
            path.write_bytes(pretty_json(state))
        elif path.exists():
            path.unlink()
    return {"scope": scope, "adapters": list(adapters), "removed": sorted(removed), "restored": sorted(restored), "skipped": sorted(skipped)}


def executable_version(name: str) -> Dict[str, Any]:
    path = shutil.which(name)
    if not path:
        return {"installed": False, "path": None, "version": None}
    try:
        result = subprocess.run([path, "--version"], check=False, capture_output=True, text=True, timeout=5)
        version = (result.stdout or result.stderr).strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        version = "unknown"
    return {"installed": True, "path": path, "version": version}


def doctor(root: Path, adapters: Iterable[str], user: bool = False) -> Dict[str, Any]:
    tools = {"codex": "codex", "claude-code": "claude", "deepseek-harness": "dsh"}
    results: Dict[str, Any] = {}
    for adapter in adapters:
        expected = generated_files(root, adapter, user)
        missing = [display_target(root, path, user) for path in expected if not path.exists()]
        results[adapter] = {
            "status": "preview" if adapter == "deepseek-harness" else ("ready" if not missing else "not_rendered"),
            "files_missing": sorted(missing),
            "client": executable_version(tools[adapter]),
        }
        if adapter == "deepseek-harness":
            results[adapter]["pinned_commit"] = DSH_COMMIT
            results[adapter]["pinned_version"] = DSH_VERSION
    return results
