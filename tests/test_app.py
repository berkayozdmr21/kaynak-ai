import io
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from pathlib import Path

scratch = tempfile.TemporaryDirectory()
os.environ['DATA_DIR'] = scratch.name
os.environ.pop('OPENAI_API_KEY', None)
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from backend.main import app
from backend.retrieval import search, split_text, tokens


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        for doc in self.client.get('/api/documents').json():
            self.client.delete('/api/documents/' + doc['id'])

    def test_demo_search_and_filter(self):
        doc = self.client.post('/api/demo').json()
        response = self.client.post('/api/ask', json={'question': 'TF-IDF kelimelerin sıklığını nasıl kullanır?', 'document_ids': [doc['id']]}).json()
        self.assertEqual(response['sources'][0]['page'], 2)
        self.assertEqual(response['mode'], 'extractive')
        self.assertIn('[1]', response['answer'])
        empty = self.client.post('/api/ask', json={'question':'TF-IDF nedir?', 'document_ids':[]}).json()
        self.assertEqual(empty['sources'], [])
        self.assertEqual(self.client.post('/api/demo').json()['id'], doc['id'])

    def test_unknown_question_and_validation(self):
        self.client.post('/api/demo')
        result = self.client.post('/api/ask', json={'question':'Zürafa gezegen teleskop'}).json()
        self.assertEqual(result['sources'], [])
        self.assertEqual(self.client.post('/api/ask', json={'question':'x'}).status_code, 422)

    def test_upload_rejects_bad_and_blank_pdf(self):
        self.assertEqual(self.client.post('/api/documents', files={'file':('bad.pdf', b'bad', 'application/pdf')}).status_code, 415)
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100)
        buffer = io.BytesIO(); writer.write(buffer)
        self.assertEqual(self.client.post('/api/documents', files={'file':('blank.pdf', buffer.getvalue(), 'application/pdf')}).status_code, 422)

    def test_real_pdf_upload_source_and_delete(self):
        # Handcrafted valid text PDF, with correct xref offsets; no extra test dependency.
        objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                   b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
        stream = b'BT /F1 12 Tf 50 700 Td (Machine learning predicts patterns from training data.) Tj ET'
        objects.append(b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream')
        pdf = b'%PDF-1.4\n'; offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(pdf)); pdf += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
        xref = len(pdf); pdf += b'xref\n0 6\n0000000000 65535 f \n'
        for offset in offsets[1:]: pdf += f'{offset:010d} 00000 n \n'.encode()
        pdf += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
        response = self.client.post('/api/documents', files={'file':('paper.pdf', pdf, 'application/pdf')})
        self.assertEqual(response.status_code, 201, response.text)
        doc_id = response.json()['id']
        result = self.client.post('/api/ask', json={'question':'Machine learning training data'}).json()
        self.assertEqual(result['sources'][0]['page'], 1)
        self.assertEqual(result['sources'][0]['document_id'], doc_id)
        self.assertEqual(self.client.get(f'/api/documents/{doc_id}/file').status_code, 200)
        self.assertEqual(self.client.delete('/api/documents/' + doc_id).status_code, 204)
        self.assertEqual(self.client.get(f'/api/documents/{doc_id}/file').status_code, 404)
        self.assertEqual(self.client.get('/api/documents').json(), [])

    def test_frontend_and_health(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertFalse(self.client.get('/api/health').json()['generation_enabled'])

    def test_generation_and_invalid_citation_fallback(self):
        self.client.post('/api/demo')
        response = http_response('RAG ilgili kaynakları arar [1].')
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = response
        with patch.dict(os.environ, {'OPENAI_API_KEY':'fake-test-key'}), patch('backend.main.httpx.AsyncClient', return_value=client):
            result = self.client.post('/api/ask', json={'question':'RAG nasıl çalışır?'}).json()
            self.assertEqual(result['mode'], 'generated')
            response.json.return_value = {'choices':[{'message':{'content':'Yanlış atıf [99]'}}]}
            fallback = self.client.post('/api/ask', json={'question':'RAG nasıl çalışır?'}).json()
            self.assertEqual(fallback['mode'], 'extractive')
            self.assertIsNotNone(fallback['warning'])

    def test_generation_provider_failure_fallback(self):
        self.client.post('/api/demo')
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.side_effect = RuntimeError('provider unavailable')
        with patch.dict(os.environ, {'OPENAI_API_KEY':'fake-test-key'}), patch('backend.main.httpx.AsyncClient', return_value=client):
            result = self.client.post('/api/ask', json={'question':'RAG nasıl çalışır?'}).json()
            self.assertEqual(result['mode'], 'extractive')
            self.assertIsNotNone(result['warning'])

    def test_tokenization_and_overlap(self):
        self.assertEqual(tokens('İSTANBUL IŞIK'), ['istanbul', 'ışık'])
        pieces = list(split_text(' '.join(str(i) for i in range(350))))
        self.assertEqual(pieces[0].split()[-35:], pieces[1].split()[:35])
        self.assertEqual(search('unknown', [{'text':'different words'}]), [])


def http_response(answer):
    from unittest.mock import Mock
    response = Mock()
    response.json.return_value = {'choices':[{'message':{'content':answer}}]}
    return response


if __name__ == '__main__':
    unittest.main()
