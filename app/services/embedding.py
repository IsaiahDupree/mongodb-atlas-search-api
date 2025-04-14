import os
import numpy as np
import random

# Only import heavy ML dependencies if not in test mode
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() in ("true", "1", "yes")

if not TEST_MODE:
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        # Check if CUDA is available for GPU acceleration
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        print("WARNING: sentence-transformers not available, falling back to test mode")
        TEST_MODE = True

class EmbeddingService:
    """
    Service for generating embeddings using the sentence-transformers library.
    Uses the paraphrase-multilingual-MiniLM-L12-v2 model which is good for Norwegian and Swedish.
    """
    _instance = None
    
    def __new__(cls):
        """Singleton pattern to ensure we only load the model once"""
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            
            if TEST_MODE or getattr(cls, '_test_mode', False):
                print("Initializing embedding service in TEST MODE (using random vectors)")
                cls._instance.model = None
            else:
                print(f"Initializing embedding model on {device}...")
                try:
                    # Load the multilingual model specified in requirements
                    cls._instance.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', device=device)
                    print("Model loaded successfully")
                except Exception as e:
                    print(f"Failed to load embedding model: {e}")
                    print("Falling back to TEST MODE")
                    cls._instance.model = None
                    # Mark as test mode, but don't try to modify global
                    cls._test_mode = True
                    
        return cls._instance
    
    def generate_embedding(self, text: str) -> list:
        """
        Generate embedding vector for the provided text.
        Returns the embedding as a list (for MongoDB storage compatibility).
        """
        # Default embedding size for the MiniLM-L12-v2 model
        embedding_size = 384
        
        if not text:
            return [0.0] * embedding_size  # Return zero vector for empty text
            
        if TEST_MODE or getattr(EmbeddingService, '_test_mode', False):
            # In test mode, generate a deterministic random embedding based on the text
            # This ensures the same text always gets the same embedding
            random.seed(hash(text) % 10000)
            embedding = [random.uniform(-1, 1) for _ in range(embedding_size)]
            return embedding
            
        # Generate embedding using the actual model
        embedding = self.model.encode(text)
        
        # Convert to list for JSON serialization
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
            
        return embedding
    
    def batch_encode(self, texts: list) -> list:
        """
        Generate embeddings for multiple texts at once (more efficient).
        """
        if not texts:
            return []
            
        # Filter out empty texts
        valid_texts = [t for t in texts if t]
        
        if TEST_MODE or getattr(EmbeddingService, '_test_mode', False):
            # In test mode, generate embeddings one by one
            return [self.generate_embedding(text) for text in valid_texts]
            
        # Generate embeddings for valid texts using the actual model
        embeddings = self.model.encode(valid_texts)
        
        # Convert to list for JSON serialization
        if isinstance(embeddings, np.ndarray):
            embeddings = embeddings.tolist()
            
        return embeddings

# Singleton instance
embedding_service = EmbeddingService()
