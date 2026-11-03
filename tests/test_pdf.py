from io import BytesIO
import tempfile
import unittest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from atlas.context.builder import build_context
from atlas.ingest.documents import extract
from atlas.services.workspace import Workspace
from atlas.storage.store import Store


def pdf_bytes(text=True, blank=False, encrypted=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    if text:
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 20 250 Td (Kernel schedules processes.) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
    if blank:
        writer.add_blank_page(width=300, height=300)
    if encrypted:
        writer.encrypt('password')
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class PDFTests(unittest.TestCase):
    def test_pdf_preserves_page_and_records_extraction_gaps_in_packet(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            pid = store.create_project('PDF')
            sid, _, warnings = Workspace(store).import_document(pid, 'book.pdf', pdf_bytes(blank=True))
            self.assertIn('Page 2', warnings[0])
            packet = build_context(Store(folder), pid, 'Kernel', [sid])
            self.assertEqual(packet['sources'][0]['page'], 1)
            self.assertIn('Kernel', packet['sources'][0]['text'])
            self.assertIn('Page 2', packet['coverage']['extraction_warnings'][0]['warnings'][0])

    def test_scan_and_encrypted_pdf_are_rejected(self):
        for data in [pdf_bytes(text=False), pdf_bytes(encrypted=True)]:
            with self.assertRaises(ValueError):
                extract('test.pdf', data)
