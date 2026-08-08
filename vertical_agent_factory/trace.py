import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _timestamp():
    try:
        return datetime.now(timezone.utc).isoformat()
    except AttributeError:  # Python 3.7 compatibility fallback
        return datetime.utcnow().isoformat() + "Z"


class TraceRecorder(object):
    def __init__(self, trace_dir, domain, agent_id):
        self.trace_id = str(uuid.uuid4())
        self.run_id = str(uuid.uuid4())
        self.domain = domain
        self.agent_id = agent_id
        trace_dir = Path(trace_dir)
        trace_dir.mkdir(parents=True, exist_ok=True)
        self.path = trace_dir / "{}.jsonl".format(self.run_id)

    def emit(self, event_type, status="ok", **fields):
        event = {
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "step_id": str(uuid.uuid4()),
            "agent_id": self.agent_id,
            "domain": self.domain,
            "event_type": event_type,
            "status": status,
            "timestamp": _timestamp(),
        }
        event.update(fields)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event
