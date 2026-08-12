"""
Text preprocessing pipeline:
- Tokenization, stopword removal, stemming
- Sentence segmentation
- Language detection
"""

import re
import string
from typing import List

# Minimal stopwords (no NLTK dependency for portability)
STOPWORDS = {
    'a','an','the','and','or','but','in','on','at','to','for','of','with',
    'by','from','is','are','was','were','be','been','being','have','has','had',
    'do','does','did','will','would','could','should','may','might','shall',
    'this','that','these','those','it','its','they','them','their','we','our',
    'you','your','he','his','she','her','i','my','me','us','not','no','nor',
    'so','yet','both','either','neither','each','any','all','few','more','most',
    'other','such','than','then','when','where','which','who','whom','how',
    'what','whether','if','as','because','since','while','although','though',
    'however','therefore','thus','hence','also','too','very','just','still'
}


def clean_text(text: str) -> str:
    """Remove special characters, normalize whitespace."""
    text = text.lower()
    text = re.sub(r'https?://\S+|www\.\S+', '', text)       # URLs
    text = re.sub(r'\S+@\S+', '', text)                       # Emails
    text = re.sub(r'\d+', ' ', text)                          # Numbers
    text = re.sub(r'[^\w\s]', ' ', text)                      # Punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def tokenize(text: str) -> List[str]:
    """Simple whitespace tokenizer after cleaning."""
    return clean_text(text).split()


def remove_stopwords(tokens: List[str]) -> List[str]:
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def simple_stem(word: str) -> str:
    """Lightweight suffix-stripping stemmer (Porter-lite)."""
    suffixes = ['ingly', 'ation', 'ness', 'ment', 'ful', 'less',
                'able', 'ible', 'ing', 'ion', 'ed', 'er', 'ly', 'es', 's']
    for suffix in suffixes:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[:-len(suffix)]
    return word


def preprocess(text: str, stem: bool = True) -> List[str]:
    """Full preprocessing pipeline."""
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    if stem:
        tokens = [simple_stem(t) for t in tokens]
    return tokens


def extract_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def get_text_stats(text: str) -> dict:
    """Compute basic text statistics."""
    words = text.split()
    sentences = extract_sentences(text)
    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "char_count": len(text),
        "avg_sentence_length": round(len(words) / max(len(sentences), 1), 1),
        "unique_words": len(set(w.lower() for w in words)),
    }
