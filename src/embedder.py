from functools import cache

import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import EMBEDDING_MODEL


@cache
def get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)


def encode(texts: str | list[str]) -> np.ndarray:
    model = get_model()
    return model.encode(texts, normalize_embeddings=True)
