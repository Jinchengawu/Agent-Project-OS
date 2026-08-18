#!/usr/bin/env python3
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
    destination.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
