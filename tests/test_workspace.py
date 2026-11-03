import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from atlas.adapters.demo import DemoAdapter
from atlas.context.builder import build_context, citation, validate_citations
from atlas.ingest.documents import extract, text_chunks
from atlas.services.workspace import Workspace
from atlas.storage.store import Store, canonical


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.service = Workspace(self.store)
        self.pid = self.store.create_project("Ôn Hệ điều hành", "Học từ tài liệu", "Trả lời tiếng Việt")
        self.sid, self.vid, _ = self.service.import_document(
            self.pid, "os.md", "Tiến trình có vùng nhớ riêng. Luồng chia sẻ vùng nhớ tiến trình.".encode())

    def packet(self, **kwargs):
        return build_context(self.store, self.pid, "Luồng chia sẻ gì?", [self.sid], **kwargs)

    def test_restart_preserves_original_source_context_output_and_decision(self):
        packet = self.packet()
        run_id = self.service.run(self.pid, packet, DemoAdapter())
        self.store.confirm_decision(self.pid, "Ưu tiên dẫn nguồn")
        reopened = Store(self.temp.name)
        row = reopened.runs(self.pid)[0]
        self.assertEqual(row["id"], run_id)
        self.assertEqual(row["state"], "completed")
        self.assertIn("Luồng chia sẻ", row["output"])
        self.assertEqual(json.loads(row["context_json"]), packet)
        self.assertEqual(row["context_hash"], hashlib.sha256(canonical(packet).encode()).hexdigest())
        self.assertEqual(len(reopened.decisions(self.pid)), 1)
        with reopened.connect() as db:
            self.assertIn("Luồng", db.execute("SELECT original FROM source_versions").fetchone()[0].decode())

    def test_isolation_sources_decisions_and_results(self):
        other = self.store.create_project("Other")
        self.store.confirm_decision(other, "Unrelated")
        with self.assertRaises(ValueError):
            build_context(self.store, other, "test", [self.sid])
        run_id = self.service.run(self.pid, self.packet(), DemoAdapter())
        other_source, _, _ = self.service.import_document(other, "other.md", b"Other")
        with self.assertRaises(ValueError):
            build_context(self.store, other, "test", [other_source], [run_id])
        self.assertEqual(self.packet()["decisions"], [])
        self.assertEqual(self.store.runs(other), [])

    def test_source_versions_and_old_citation_survive_updates(self):
        first = self.packet()
        _, second, _ = self.service.import_document(self.pid, "os.md", b"Changed content")
        self.assertNotEqual(second, self.vid)
        self.assertEqual(first["sources"][0]["version_id"], self.vid)
        self.assertEqual(self.packet()["sources"][0]["version_id"], second)
        self.assertIn("Tiến trình", first["sources"][0]["text"])
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM source_versions").fetchone()[0], 2)

    def test_identical_import_reuses_version(self):
        with self.store.connect() as db:
            original = db.execute("SELECT original FROM source_versions WHERE id=?", (self.vid,)).fetchone()[0]
        _, version, _ = self.service.import_document(self.pid, "os.md", original)
        self.assertEqual(version, self.vid)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0], 1)

    def test_fts_retrieval_prioritizes_relevant_chunk(self):
        sid, _, _ = self.service.import_document(self.pid, "long.md", (("Banana unrelated\n" * 180) + "Quantum kernel semaphore").encode())
        packet = build_context(self.store, self.pid, "semaphore", [sid], max_chars=4000)
        self.assertIn("semaphore", packet["sources"][0]["text"])
        self.assertGreater(packet["coverage"]["omitted_chunks"], 0)

    def test_hard_context_budget_and_no_silent_truncation(self):
        sid, _, _ = self.service.import_document(self.pid, "long.md", ("nội dung dài\n" * 1000).encode())
        packet = build_context(self.store, self.pid, "test", [sid], max_chars=4500)
        self.assertLessEqual(len(canonical(packet)), 4500)
        self.assertGreater(packet["coverage"]["omitted_chunks"], 0)
        with self.assertRaises(ValueError):
            self.packet(max_chars=10)
        with self.assertRaises(ValueError):
            build_context(self.store, self.pid, "x" * 5000, [self.sid], max_chars=4000)

    def test_only_selected_result_is_handed_off_and_not_confirmed(self):
        run_id = self.service.run(self.pid, self.packet(), DemoAdapter())
        self.assertEqual(self.packet()["prior_results"], [])
        next_packet = self.packet(prior_run_ids=[run_id])
        self.assertEqual(next_packet["prior_results"][0]["run_id"], run_id)
        self.assertEqual(next_packet["decisions"], [])
        self.store.confirm_decision(self.pid, "Đã xác nhận")
        self.assertEqual(len(self.packet()["decisions"]), 1)

    def test_failed_adapter_keeps_exact_context_and_previous_result(self):
        self.service.run(self.pid, self.packet(), DemoAdapter())
        class Broken:
            name = "broken"
            def execute(self, packet):
                raise RuntimeError("offline test failure")
        run_id = self.service.run(self.pid, self.packet(), Broken())
        row = next(r for r in self.store.runs(self.pid) if r["id"] == run_id)
        self.assertEqual(row["state"], "failed")
        self.assertIn("offline test failure", row["error"])
        self.assertEqual(json.loads(row["context_json"]), self.packet())
        self.assertEqual(sum(r["state"] == "completed" for r in self.store.runs(self.pid)), 1)

    def test_adapter_cannot_mutate_saved_packet(self):
        packet = self.packet()
        good = packet["sources"][0]["citation"]
        class Mutating:
            name = "mutating-test"
            def execute(self, value):
                value["sources"].clear()
                return good
        self.service.run(self.pid, packet, Mutating())
        row = self.store.runs(self.pid)[0]
        self.assertEqual(json.loads(row["context_json"]), packet)
        self.assertEqual(json.loads(row["validation_json"])["valid"], [good])

    def test_citation_ids_reject_wrong_version_and_flag_missing(self):
        packet = self.packet()
        good = packet["sources"][0]["citation"]
        bad = good.replace(self.vid, "wrong-version")
        validation = validate_citations(good + bad, packet)
        self.assertEqual(validation["valid"], [good])
        self.assertEqual(validation["invalid"], [bad])
        self.assertTrue(validate_citations("No references", packet)["missing"])

    def test_manual_response_binds_original_request_not_current_sources(self):
        packet = self.packet()
        run_id = self.service.manual_request(self.pid, packet)
        self.service.import_document(self.pid, "os.md", b"new version")
        self.service.manual_result(self.pid, run_id, packet["sources"][0]["citation"])
        row = self.store.runs(self.pid)[0]
        self.assertEqual(json.loads(row["context_json"]), packet)
        self.assertEqual(json.loads(row["validation_json"])["invalid"], [])
        with self.assertRaises(ValueError):
            self.service.manual_result(self.pid, run_id, "cannot overwrite")

    def test_empty_response_fails_and_duplicate_finish_is_rejected(self):
        class Empty:
            name = "empty"
            def execute(self, packet):
                return ""
        run_id = self.service.run(self.pid, self.packet(), Empty())
        self.assertEqual(self.store.runs(self.pid)[0]["state"], "failed")
        with self.assertRaises(ValueError):
            self.store.finish_run(run_id, output="overwrite")

    def test_import_rejects_empty_invalid_encoding_and_unsupported_files(self):
        for filename, data in [("empty.md", b" \n"), ("bad.txt", b"\xff"), ("code.zip", b"zip")]:
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                self.service.import_document(self.pid, filename, data)
        self.assertEqual(len(self.store.sources(self.pid)), 1)

    def test_long_lines_preserve_source_line_number(self):
        chunks = text_chunks("x" * 7000)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(c["line_start"] == c["line_end"] == 1 for c in chunks))
        self.assertEqual("".join(c["text"] for c in chunks), "x" * 7000)


if __name__ == "__main__":
    unittest.main()
