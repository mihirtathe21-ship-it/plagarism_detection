"""
TF-IDF Vectorization and Cosine Similarity Detection
Uses sklearn's TfidfVectorizer for production-grade text similarity.
"""

import math
import re
from typing import List, Dict, Tuple, Optional
from collections import Counter

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from core.text_processor import preprocess, extract_sentences, clean_text


def compute_tfidf_similarity(text1: str, text2: str) -> Dict:
    """
    Compute TF-IDF cosine similarity between two texts.
    Returns similarity score and detailed breakdown.
    """
    if SKLEARN_AVAILABLE:
        return _sklearn_tfidf(text1, text2)
    else:
        return _manual_tfidf(text1, text2)


def _sklearn_tfidf(text1: str, text2: str) -> Dict:
    """sklearn-based TF-IDF similarity."""
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        max_features=10000,
        sublinear_tf=True,
        strip_accents='unicode',
        analyzer='word',
        token_pattern=r'\b[a-zA-Z][a-zA-Z]+\b'
    )
    
    try:
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        # Get top matching terms
        feature_names = vectorizer.get_feature_names_out()
        vec1 = tfidf_matrix[0].toarray()[0]
        vec2 = tfidf_matrix[1].toarray()[0]
        
        # Find terms present in both
        shared_indices = np.where((vec1 > 0) & (vec2 > 0))[0]
        shared_terms = sorted(
            [(feature_names[i], float(min(vec1[i], vec2[i]))) for i in shared_indices],
            key=lambda x: -x[1]
        )[:15]
        
        return {
            "similarity": round(float(similarity), 4),
            "percentage": round(float(similarity) * 100, 2),
            "method": "TF-IDF (sklearn, bigrams)",
            "shared_terms": shared_terms,
            "vocab_size": len(feature_names),
        }
    except Exception as e:
        return {"similarity": 0, "percentage": 0, "error": str(e)}


def _manual_tfidf(text1: str, text2: str) -> Dict:
    """Pure Python TF-IDF fallback."""
    def tf(tokens):
        count = Counter(tokens)
        total = len(tokens)
        return {t: c/total for t, c in count.items()}

    def idf(term, docs):
        n = sum(1 for d in docs if term in d)
        return math.log((len(docs) + 1) / (n + 1)) + 1

    tokens1 = preprocess(text1)
    tokens2 = preprocess(text2)
    docs = [set(tokens1), set(tokens2)]
    vocab = set(tokens1) | set(tokens2)
    
    tf1, tf2 = tf(tokens1), tf(tokens2)
    
    def tfidf_vec(tf_dict):
        return {t: tf_dict.get(t, 0) * idf(t, docs) for t in vocab}

    v1 = tfidf_vec(tf1)
    v2 = tfidf_vec(tf2)
    
    dot = sum(v1[t] * v2[t] for t in vocab)
    norm1 = math.sqrt(sum(x**2 for x in v1.values()))
    norm2 = math.sqrt(sum(x**2 for x in v2.values()))
    
    sim = dot / (norm1 * norm2) if norm1 * norm2 > 0 else 0
    
    shared = [(t, min(v1[t], v2[t])) for t in vocab if v1[t] > 0 and v2[t] > 0]
    shared.sort(key=lambda x: -x[1])
    
    return {
        "similarity": round(sim, 4),
        "percentage": round(sim * 100, 2),
        "method": "TF-IDF (manual)",
        "shared_terms": shared[:15],
        "vocab_size": len(vocab),
    }


def find_matching_sentences(text1: str, text2: str, threshold: float = 0.7) -> List[Dict]:
    """
    Find sentence-level matches between two texts.
    Returns list of matching sentence pairs with similarity scores.
    """
    sents1 = extract_sentences(text1)
    sents2 = extract_sentences(text2)
    
    if not sents1 or not sents2 or not SKLEARN_AVAILABLE:
        return []
    
    vectorizer = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
    try:
        all_sents = sents1 + sents2
        tfidf = vectorizer.fit_transform(all_sents)
        
        sim_matrix = cosine_similarity(
            tfidf[:len(sents1)],
            tfidf[len(sents1):]
        )
        
        matches = []
        for i, row in enumerate(sim_matrix):
            for j, score in enumerate(row):
                if score >= threshold:
                    matches.append({
                        "sentence1": sents1[i],
                        "sentence2": sents2[j],
                        "similarity": round(float(score), 3),
                        "index1": i,
                        "index2": j,
                    })
        
        matches.sort(key=lambda x: -x['similarity'])
        return matches[:20]
    except:
        return []


def compute_ngram_overlap(text1: str, text2: str, n: int = 3) -> Dict:
    """Compute n-gram overlap (Jaccard similarity)."""
    def get_ngrams(text, n):
        words = clean_text(text).split()
        return set(tuple(words[i:i+n]) for i in range(len(words)-n+1))
    
    ng1 = get_ngrams(text1, n)
    ng2 = get_ngrams(text2, n)
    
    if not ng1 or not ng2:
        return {"overlap": 0, "percentage": 0}
    
    intersection = ng1 & ng2
    union = ng1 | ng2
    jaccard = len(intersection) / len(union)
    
    return {
        "overlap": round(jaccard, 4),
        "percentage": round(jaccard * 100, 2),
        "matching_ngrams": len(intersection),
        "total_ngrams": len(union),
        "method": f"{n}-gram Jaccard",
        "sample_matches": [' '.join(ng) for ng in list(intersection)[:5]]
    }
