import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def normalize_query(query: str) -> str:
    """Normaliza espaços da pergunta ou palavra-chave."""
    return re.sub(r"\s+", " ", query).strip()


def flatten_chunks(documents: list[dict]) -> list[dict]:
    """Transforma documentos em uma lista única de trechos pesquisáveis."""
    flattened = []

    for document in documents:
        for chunk_index, chunk in enumerate(document.get("chunks", [])):
            flattened.append(
                {
                    "file_name": document.get("file_name", "arquivo desconhecido"),
                    "chunk_index": chunk_index,
                    "chunk": chunk,
                }
            )

    return flattened


def search_relevant_chunks(query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
    """
    Busca os trechos mais relevantes usando TF-IDF e similaridade de cosseno.

    Esse método é totalmente local e não usa internet nem APIs externas.
    """
    query = normalize_query(query)
    chunks = flatten_chunks(documents)

    if not query or not chunks:
        return []

    corpus = [item["chunk"] for item in chunks]

    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            ngram_range=(1, 2),
            max_features=50000,
        )
        matrix = vectorizer.fit_transform(corpus + [query])
    except ValueError:
        return []

    chunk_vectors = matrix[:-1]
    query_vector = matrix[-1]
    scores = cosine_similarity(query_vector, chunk_vectors).flatten()

    ranked_indexes = scores.argsort()[::-1]
    results = []

    for index in ranked_indexes:
        score = float(scores[index])
        if score <= 0:
            continue

        item = chunks[index].copy()
        item["score"] = score
        results.append(item)

        if len(results) >= top_k:
            break

    return results
