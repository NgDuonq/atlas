"""Deterministic plumbing check. This adapter does not call an AI."""
class DemoAdapter:
    name = "demo-offline (not an AI)"

    def execute(self, packet):
        source = packet["sources"][0]
        return ("DEMO OFFLINE — đây là trích đoạn để kiểm tra luồng lưu dữ liệu, không phải lời giải AI.\n\n"
                + source["text"] + "\n\n" + source["citation"])
