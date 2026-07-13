import math
import random
import hashlib
import json
import logging
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError, APIError
from app.core.config import settings
from app.core.exceptions import EmbeddingServiceError

logger = logging.getLogger(__name__)

def generate_local_deterministic_embedding(text: str, dimensions: int = 128) -> list[float]:
    """
    Generates a deterministic, L2-normalized 128-dimensional vector for a given text.
    Used as a fallback and for zero-dependency local runs.
    """
    if not text:
        return [0.0] * dimensions
    
    # Generate a deterministic seed from the text
    hasher = hashlib.sha256(text.encode("utf-8"))
    seed = int(hasher.hexdigest(), 16) % (2**32)
    
    rng = random.Random(seed)
    # Generate Gaussian distribution values
    vector = [rng.gauss(0.0, 1.0) for _ in range(dimensions)]
    
    # L2 normalize the vector
    magnitude = math.sqrt(sum(x * x for x in vector))
    if magnitude > 0:
        vector = [x / magnitude for x in vector]
        
    return vector

def _get_raw_embedding(text: str, dimensions: int = 128) -> list[float]:
    """Internal: get a raw float list embedding."""
    if not settings.NVIDIA_NIM_API_KEY:
        logger.info("NVIDIA_NIM_API_KEY not configured. Using local deterministic embeddings.")
        return generate_local_deterministic_embedding(text, dimensions)
        
    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.NVIDIA_NIM_API_KEY
        )
        
        response = client.embeddings.create(
            input=[text],
            model=settings.NIM_EMBEDDING_MODEL
        )
        
        raw_vector = response.data[0].embedding
        
        # Adjust dimensions to match target (128)
        if len(raw_vector) == dimensions:
            return raw_vector
        elif len(raw_vector) > dimensions:
            truncated = raw_vector[:dimensions]
            magnitude = math.sqrt(sum(x * x for x in truncated))
            if magnitude > 0:
                truncated = [x / magnitude for x in truncated]
            return truncated
        else:
            padded = raw_vector + [0.0] * (dimensions - len(raw_vector))
            magnitude = math.sqrt(sum(x * x for x in padded))
            if magnitude > 0:
                padded = [x / magnitude for x in padded]
            return padded
            
    except (APIConnectionError, APITimeoutError) as e:
        logger.warning(f"Embedding service connection error: {e}. Falling back to local embeddings.")
        return generate_local_deterministic_embedding(text, dimensions)
    except RateLimitError as e:
        logger.warning(f"Embedding service rate limited: {e}. Falling back to local embeddings.")
        return generate_local_deterministic_embedding(text, dimensions)
    except APIError as e:
        logger.error(f"Embedding service API error: {e}")
        raise EmbeddingServiceError(f"Failed to generate embeddings: {str(e)}")


def get_embeddings(text: str, dimensions: int = 128) -> str:
    """
    Generates embeddings for the provided text and returns them as a JSON string.
    Stored as Text in the database — no pgvector extension required.
    
    Returns:
        JSON string like "[0.12, -0.34, ...]"
    """
    vector = _get_raw_embedding(text, dimensions)
    return json.dumps(vector)


def get_embedding_vector(text: str, dimensions: int = 128) -> list[float]:
    """
    Returns the raw float list embedding for a given text.
    Used for in-Python similarity computations.
    """
    return _get_raw_embedding(text, dimensions)


def decode_embedding(embedding_str: str) -> list[float]:
    """
    Decodes a stored JSON embedding string back to a float list.
    
    Args:
        embedding_str: JSON string from the database Text column
    
    Returns:
        List of floats, or empty list if invalid
    """
    if not embedding_str:
        return []
    try:
        return json.loads(embedding_str)
    except (json.JSONDecodeError, TypeError):
        return []


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Computes cosine similarity between two float vectors.
    Returns a value between -1.0 (opposite) and 1.0 (identical).
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
