"""Small synthetic retrieval sanity check; not a real-world benchmark."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(os.path.abspath(__file__)).parents[1]))
from backend.retrieval import search

corpus = [
    {'id':'rag', 'text':'RAG önce ilgili kaynakları arar sonra dil modeli cevap üretir.'},
    {'id':'tfidf', 'text':'TF-IDF kelime sıklığı ve nadirliğini kullanır. Türkçe ekler sınırlama yaratır.'},
    {'id':'metrics', 'text':'Recall ilgili kaynakların bulunma oranıdır. MRR ilk doğru sonucun ters sırasıdır.'},
    {'id':'embedding', 'text':'Embedding metni vektöre dönüştürür ve anlamsal benzerlik için kullanılır.'}
]
cases = [
    ('RAG nasıl cevap üretir?', ['rag']),
    ('TF-IDF kelime sıklığı nedir?', ['tfidf']),
    ('Recall ve MRR nasıl ölçülür?', ['metrics']),
    ('Embedding vektöre nasıl dönüştürür?', ['embedding']),
    ('Türkçe ekler sınırlama yaratır mı?', ['tfidf']),
    ('Zürafa teleskop gezegen', [])
]
recalls, reciprocal, abstentions = [], [], []
for question, relevant in cases:
    ids = [c['id'] for c in search(question, corpus, 3)]
    if relevant:
        recalls.append(len(set(ids) & set(relevant)) / len(relevant))
        reciprocal.append(next((1/(i+1) for i, item in enumerate(ids) if item in relevant), 0))
    else:
        abstentions.append(not ids)
report = {'dataset':'6 synthetic smoke cases; not generalizable', 'recall@3':sum(recalls)/len(recalls),
          'mrr@3':sum(reciprocal)/len(reciprocal), 'unanswerable_abstention':sum(abstentions)/len(abstentions)}
print(json.dumps(report, indent=2, ensure_ascii=False))
