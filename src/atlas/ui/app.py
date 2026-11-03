import json
import os
from pathlib import Path
import streamlit as st
from atlas.adapters.demo import DemoAdapter
from atlas.context.builder import build_context, export_prompt
from atlas.services.workspace import Workspace
from atlas.storage.store import Store


def main():
    st.set_page_config(page_title="Atlas", page_icon="◈", layout="wide")
    store = Store(os.environ.get("ATLAS_HOME", str(Path.home() / "Documents" / "Atlas")))
    workspace = Workspace(store)
    st.title("◈ Atlas")
    st.caption("Project → nguồn → context → kết quả → bước tiếp theo")
    st.info("Bản nền tảng: demo offline hoặc chuyển context thủ công sang AI. Chưa kết nối CLI/API tự động.")
    with st.sidebar:
        st.header("Projects")
        with st.form("create-project"):
            name = st.text_input("Tên project")
            goal = st.text_area("Mục tiêu")
            rules = st.text_area("Quy tắc")
            if st.form_submit_button("Tạo project"):
                try:
                    store.create_project(name, goal, rules)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        projects = store.projects()
        if not projects:
            st.info("Tạo project để bắt đầu.")
            return
        by_id = {p["id"]: p for p in projects}
        pid = st.selectbox("Project đang làm", list(by_id), format_func=lambda key: by_id[key]["name"])
    sources_tab, task_tab, results_tab, memory_tab = st.tabs(["Nguồn", "Nhiệm vụ", "Kết quả", "Quyết định"])
    with sources_tab:
        st.write(by_id[pid]["goal"])
        upload = st.file_uploader("Thêm TXT / Markdown / PDF có text", type=["txt", "md", "pdf"], key=f"upload-{pid}")
        st.caption("Cùng tên file = phiên bản mới của nguồn; cùng nội dung = dùng lại phiên bản cũ.")
        if upload and st.button("Nhập nguồn", key=f"import-{pid}"):
            try:
                _, version_id, warnings = workspace.import_document(pid, upload.name, upload.getvalue())
                st.success(f"Đã lưu phiên bản {version_id[:8]}")
                for warning in warnings:
                    st.warning(warning)
            except Exception as exc:
                st.error(f"Không nhập được tài liệu: {exc}")
        sources = store.sources(pid)
        if sources:
            st.dataframe([dict(Tên=s["title"], Phiên_bản=s["active_version_id"], SHA256=s["sha256"]) for s in sources], hide_index=True)
    with task_tab:
        source_by_id = {s["id"]: s for s in sources}
        selected = st.multiselect("Nguồn dùng cho nhiệm vụ", list(source_by_id),
                                  format_func=lambda key: source_by_id[key]["title"], key=f"sources-{pid}")
        runs = store.runs(pid)
        completed = {r["id"]: r for r in runs if r["state"] == "completed"}
        prior = st.multiselect("Kết quả trước cần bàn giao", list(completed),
                               format_func=lambda key: completed[key]["task"][:80] + " · " + key[:8], key=f"prior-{pid}")
        task = st.text_area("Giao nhiệm vụ", key=f"task-{pid}")
        budget = st.number_input("Giới hạn context (ký tự JSON, không phải token)", 4000, 100000, 24000, 1000)
        packet = None
        if task.strip() and selected:
            try:
                packet = build_context(store, pid, task, selected, prior, int(budget))
            except ValueError as exc:
                st.error(str(exc))
        if packet:
            st.caption(f"Dùng {packet['coverage']['included_chunks']}/{packet['coverage']['total_chunks']} đoạn. Đây là truy xuất, không phải đọc toàn bộ tài liệu.")
            with st.expander("Xem context sẽ gửi", expanded=True):
                st.json(packet)
            st.download_button("Xuất prompt để dùng với AI", export_prompt(packet), "atlas-context.txt", "text/plain")
            st.caption("Tài liệu trong context sẽ được gửi tới AI nếu bạn sao chép hoặc tải lên nhà cung cấp đó.")
            if st.button("Chạy demo offline", key=f"demo-{pid}"):
                workspace.run(pid, packet, DemoAdapter())
                st.success("Đã lưu kết quả demo. Mở tab Kết quả để xem.")
            if st.button("Tạo lượt thủ công từ context này", key=f"manual-{pid}"):
                workspace.manual_request(pid, packet)
                st.success("Đã giữ context bất biến. Dán câu trả lời vào lượt tương ứng trong tab Kết quả.")
    with results_tab:
        runs = store.runs(pid)
        if not runs:
            st.caption("Chưa có kết quả.")
        for run in runs:
            with st.expander(f"{run['state']} · {run['task'][:80]} · {run['id'][:8]}"):
                st.caption(run["adapter"] + " · " + run["created_at"])
                packet = json.loads(run["context_json"])
                st.download_button("Tải context gốc", export_prompt(packet), f"context-{run['id']}.txt", key=f"ctx-{run['id']}")
                st.caption("Context SHA256: " + run["context_hash"])
                if run["state"] == "running" and run["adapter"] == "manual-external-AI":
                    with st.form(f"response-{run['id']}"):
                        response = st.text_area("Dán câu trả lời AI")
                        if st.form_submit_button("Lưu câu trả lời"):
                            try:
                                workspace.manual_result(pid, run["id"], response)
                                st.rerun()
                            except ValueError as exc:
                                st.error(str(exc))
                if run["output"]:
                    st.markdown(run["output"])
                    validation = json.loads(run["validation_json"])
                    if validation["missing"]:
                        st.warning("Kết quả chưa có citation.")
                    if validation["invalid"]:
                        st.warning("Citation không có trong context: " + ", ".join(validation["invalid"]))
                    st.caption("Kiểm tra citation chỉ xác nhận ID; bạn cần đọc nguồn để kiểm chứng kết luận.")
                    st.download_button("Tải kết quả", run["output"], f"result-{run['id']}.md", key=f"out-{run['id']}")
                if run["error"]:
                    st.error(run["error"])
                with st.expander("Đoạn nguồn AI được cung cấp"):
                    for source in packet["sources"]:
                        st.code(source["citation"], language=None)
                        st.caption(f"{source['title']} · trang {source['page']} · dòng {source['line_start']}–{source['line_end']}")
                        st.text(source["text"])
    with memory_tab:
        st.caption("Chỉ nội dung bạn xác nhận ở đây mới trở thành quyết định dùng cho nhiệm vụ sau.")
        with st.form(f"decision-{pid}"):
            text = st.text_area("Quyết định đã kiểm tra")
            if st.form_submit_button("Xác nhận và lưu"):
                try:
                    store.confirm_decision(pid, text)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        for decision in store.decisions(pid):
            st.write(decision["text"])
            st.caption(decision["confirmed_at"])
