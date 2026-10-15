"""Deterministic TF-IDF retrieval baseline with Turkish-aware tokenization."""
import math
import re
from collections import Counter


def tokens(text):
    return re.findall(r"[a-zçğıöşü0-9]+", text.replace('İ', 'i').replace('I', 'ı').lower())


def split_text(text, size=170, overlap=35):
    words = text.split()
    for start in range(0, len(words), size - overlap):
        part = words[start:start + size]
        if part:
            yield ' '.join(part)
        if start + size >= len(words):
            break


def search(question, chunks, limit=5):
    """Cosine similarity; no model downloads or external calls required."""
    if not chunks or not tokens(question):
        return []
    counts = [Counter(tokens(c['text'])) for c in chunks]
    df = Counter(t for count in counts for t in count)
    idf = {t: math.log((1 + len(chunks)) / (1 + n)) + 1 for t, n in df.items()}
    def vector(count):
        return {t: (1 + math.log(n)) * idf[t] for t, n in count.items() if t in idf}
    query = vector(Counter(tokens(question)))
    qnorm = math.sqrt(sum(v*v for v in query.values()))
    if not qnorm:
        return []
    results = []
    for chunk, count in zip(chunks, counts):
        vec = vector(count)
        norm = math.sqrt(sum(v*v for v in vec.values()))
        score = sum(v * vec.get(t, 0) for t, v in query.items()) / (qnorm * norm) if norm else 0
        if score >= 0.08:
            results.append({**chunk, 'score': round(score, 4)})
    return sorted(results, key=lambda c: c['score'], reverse=True)[:limit]
