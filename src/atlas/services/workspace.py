"""UI-facing operations: preserve the exact preview packet and retain failed runs."""
import json
from atlas.context.builder import validate_citations
from atlas.ingest.documents import extract
from atlas.storage.store import canonical


class Workspace:
    def __init__(self, store):
        self.store = store

    def import_document(self, project_id, filename, data):
        chunks, warnings = extract(filename, data)
        source_id, version_id = self.store.import_source(
            project_id, filename, "document", data, chunks, warnings)
        return source_id, version_id, warnings

    def run(self, project_id, packet, adapter):
        # Roundtrip prevents an adapter mutating the persisted request or validation evidence.
        snapshot = json.loads(canonical(packet))
        run_id = self.store.start_run(project_id, snapshot, adapter.name)
        try:
            output = adapter.execute(json.loads(canonical(snapshot)))
            if not isinstance(output, str) or not output.strip():
                raise ValueError("Adapter returned empty or non-text output")
            validation = validate_citations(output, snapshot)
            self.store.finish_run(run_id, output=output, validation=validation)
        except Exception as exc:
            self.store.finish_run(run_id, error=f"{type(exc).__name__}: {exc}")
        return run_id

    def manual_request(self, project_id, packet):
        return self.store.start_run(project_id, json.loads(canonical(packet)), "manual-external-AI")

    def manual_result(self, project_id, run_id, output):
        rows = {r["id"]: r for r in self.store.runs(project_id)}
        if run_id not in rows or rows[run_id]["adapter"] != "manual-external-AI":
            raise ValueError("Manual request does not belong to this project")
        if not output.strip():
            raise ValueError("Paste a nonempty response")
        packet = json.loads(rows[run_id]["context_json"])
        self.store.finish_run(run_id, output=output, validation=validate_citations(output, packet))
