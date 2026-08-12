"""
Advanced Semantic Similarity using Sentence-BERT / SentenceTransformers.
Falls back to TF-IDF cosine if transformers unavailable.
"""

import re
import hashlib
from typing import Any, Dict, List, Optional

# Lazy-load heavy models
_model: Any = None
_model_name: Optional[str] = None
_embedding_cache: Dict[str, Any] = {}   # text_hash -> embedding vector
_CACHE_MAX = 200

PREFERRED_MODELS = [
    'all-MiniLM-L6-v2',         # fast, ~80MB — default, good speed/accuracy tradeoff
    'paraphrase-MiniLM-L3-v2',  # tiny, ~60MB, fallback if MiniLM-L6 fails to load
    'all-mpnet-base-v2',        # most accurate but slow, ~420MB — last resort
]

TRANSFORMERS_AVAILABLE = False
SentenceTransformer = None

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    np = None


def _get_model(model_name: Optional[str] = None) -> Optional[Any]:
    """Lazy-load and cache the sentence transformer model, with fallback chain."""
    global _model, _model_name

    if not TRANSFORMERS_AVAILABLE or SentenceTransformer is None:
        return None

    target = model_name or PREFERRED_MODELS[0]

    if _model is not None and _model_name == target:
        return _model

    try:
        _model = SentenceTransformer(target)
        _model_name = target
        return _model
    except Exception:
        for m in PREFERRED_MODELS:
            if m == target:
                continue
            try:
                _model = SentenceTransformer(m)
                _model_name = m
                return _model
            except Exception:
                continue

    _model = None
    _model_name = None
    return None


def _hash_text(text: str) -> str:
    return hashlib.md5(text.encode('utf-8', errors='replace')).hexdigest()


def _chunk_text(text: str, max_words: int = 120) -> List[str]:
    """
    Split long text into overlapping paragraph-ish chunks so a single
    matching paragraph inside a long page isn't averaged away.
    """
    paragraphs = [p.strip() for p in re.split(r'\n{2,}|(?<=[.!?])\s{2,}', text) if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks = []
    for p in paragraphs:
        words = p.split()
        if len(words) <= max_words:
            chunks.append(p)
        else:
            step = max_words - 20
            for i in range(0, len(words), step):
                chunk = ' '.join(words[i:i + max_words])
                if chunk:
                    chunks.append(chunk)
    return chunks or [text]


def _encode_cached(model: Any, text: str, use_cache: bool = True) -> Any:
    """Encode a single text (or list of chunks) with an embedding cache."""
    key = _hash_text(text)
    if use_cache and key in _embedding_cache:
        return _embedding_cache[key]

    emb = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)

    if use_cache:
        if len(_embedding_cache) >= _CACHE_MAX:
            _embedding_cache.pop(next(iter(_embedding_cache)))
        _embedding_cache[key] = emb

    return emb


def compute_semantic_similarity(text1: str, text2: str, model_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Compute semantic similarity using sentence embeddings.
    text2 (typically the fetched source page) is chunked so a match in one
    paragraph of a long page isn't diluted by the rest of the page.
    """
    model = _get_model(model_name)

    if model is None or not TRANSFORMERS_AVAILABLE:
        return _fallback_semantic(text1, text2)

    try:
        emb1 = _encode_cached(model, text1)

        chunks2 = _chunk_text(text2, max_words=120)
        emb2_chunks = model.encode(chunks2, convert_to_numpy=True, normalize_embeddings=True)

        sims = emb2_chunks @ emb1
        best_idx = int(sims.argmax())
        sim = float(sims[best_idx])
        sim = max(0.0, min(1.0, sim))

        return {
            "similarity": round(sim, 4),
            "percentage": round(sim * 100, 2),
            "method": f"SentenceBERT ({_model_name}, best-chunk)",
            "model": _model_name,
            "available": True,
            "interpretation": _interpret_score(sim),
            "best_matching_chunk": chunks2[best_idx][:300],
        }
    except Exception as e:
        return {"similarity": 0, "percentage": 0, "error": str(e), "available": False}


def compute_semantic_similarity_sentences(
    text1: str,
    text2: str,
    top_k: int = 5,
    threshold: float = 0.60,
) -> List[Dict]:
    """
    Find semantically similar sentence pairs across two documents.
    """
    from core.text_processor import extract_sentences

    model = _get_model()
    if model is None or not TRANSFORMERS_AVAILABLE:
        return []

    try:
        sents1 = extract_sentences(text1)
        sents2 = extract_sentences(text2)

        if not sents1 or not sents2:
            return []

        emb1 = model.encode(sents1, convert_to_numpy=True, normalize_embeddings=True)
        emb2 = model.encode(sents2, convert_to_numpy=True, normalize_embeddings=True)

        sim_matrix = emb1 @ emb2.T

        matches = []
        for i in range(len(sents1)):
            best_j = int(sim_matrix[i].argmax())
            score = float(sim_matrix[i][best_j])
            if score >= threshold:
                matches.append({
                    "sentence1": sents1[i],
                    "sentence2": sents2[best_j],
                    "semantic_similarity": round(score, 3),
                    "index1": i,
                    "index2": best_j,
                })

        matches.sort(key=lambda x: -x['semantic_similarity'])
        return matches[:top_k]
    except Exception:
        return []


def compute_combined_similarity(text1: str, text2: str) -> Dict:
    """
    Blended score combining semantic (meaning) + lexical (exact wording)
    signals.
    """
    from core.similarity_engine import compute_tfidf_similarity, compute_ngram_overlap

    semantic = compute_semantic_similarity(text1, text2)
    tfidf = compute_tfidf_similarity(text1, text2)
    ngram = compute_ngram_overlap(text1, text2, n=3)

    sem_score = semantic.get("similarity", 0)
    tfidf_score = tfidf.get("similarity", 0)
    ngram_score = ngram.get("overlap", 0)

    combined = round(sem_score * 55 + ngram_score * 30 + tfidf_score * 15, 2)

    return {
        "combined_score": combined,
        "semantic": semantic,
        "tfidf": tfidf,
        "ngram": ngram,
        "interpretation": _interpret_score(combined / 100),
    }


def _fallback_semantic(text1: str, text2: str) -> Dict:
    """Fallback when transformers not available - use word overlap."""
    from core.similarity_engine import compute_tfidf_similarity
    result = compute_tfidf_similarity(text1, text2)
    result["method"] = "TF-IDF (semantic model unavailable)"
    result["available"] = False
    result["interpretation"] = _interpret_score(result.get("similarity", 0))
    return result


def _interpret_score(score: float) -> str:
    if score >= 0.90: return "Nearly identical"
    if score >= 0.75: return "Highly similar — likely plagiarism"
    if score >= 0.60: return "Moderately similar — review recommended"
    if score >= 0.40: return "Some overlap — possibly coincidental"
    if score >= 0.20: return "Low similarity — minor overlap"
    return "Distinct content"


def get_model_status() -> Dict:
    return {
        "transformers_available": TRANSFORMERS_AVAILABLE,
        "model_loaded": _model is not None,
        "model_name": _model_name,
        "preferred_models": PREFERRED_MODELS,
        "cache_size": len(_embedding_cache),
    }
