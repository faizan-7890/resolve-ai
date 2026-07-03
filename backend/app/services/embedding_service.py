import math
import random
import hashlib
import logging
from openai import OpenAI
from app.core.config import settings

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

def get_embeddings(text: str, dimensions: int = 128) -> list[float]:
    """
    Generates embeddings for the provided text.
    Attempts to use NVIDIA NIM if credentials are present, falling back to local deterministic embedding.
    """
    if not settings.NVIDIA_NIM_API_KEY:
        logger.info("NVIDIA_NIM_API_KEY not configured. Using local deterministic embeddings.")
        return generate_local_deterministic_embedding(text, dimensions)
        
    try:
        # Initialize OpenAI client with NVIDIA NIM base url
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
            # Truncate and re-normalize
            truncated = raw_vector[:dimensions]
            magnitude = math.sqrt(sum(x * x for x in truncated))
            if magnitude > 0:
                truncated = [x / magnitude for x in truncated]
            return truncated
        else:
            # Pad with zeros and re-normalize
            padded = raw_vector + [0.0] * (dimensions - len(raw_vector))
            magnitude = math.sqrt(sum(x * x for x in padded))
            if magnitude > 0:
                padded = [x / magnitude for x in padded]
            return padded
            
    except Exception as e:
        logger.warning(f"Error calling NVIDIA NIM embedding API: {e}. Falling back to local deterministic embeddings.")
        return generate_local_deterministic_embedding(text, dimensions)
