import logging
from typing import List, Optional
import numpy as np
from textblob import TextBlob
from app.services.agent.schemas import AgentEvaluationResult, BiasMetrics, PersonaResponse

logger = logging.getLogger(__name__)

# Reference anchors for semantic vector projection
# Used to calculate the empirical bias distance between Optimistic and Pessimistic viewpoints
OPTIMISTIC_ANCHORS = [
    "The results demonstrate exceptional growth, outstanding momentum, and immense upside potential.",
    "Performance metrics are surging with reliable indicators of continuous expansion and profitability.",
    "This represents a remarkable opportunity with high upside and highly favorable tailwinds.",
    "Market trends and forecasts are overwhelmingly positive and robust.",
    "Clear positive trajectory indicates scalable future gains and high asset value."
]

PESSIMISTIC_ANCHORS = [
    "The findings reveal severe liabilities, mounting costs, and critical downside risks.",
    "Operating margins are shrinking rapidly with clear evidence of structural vulnerability.",
    "This represents a hazardous situation with heightened probability of catastrophic failure.",
    "Unfavorable market volatility threatens solvency and long-term viability.",
    "Fundamental metrics highlight systemic fragility, declining returns, and high downside exposure."
]

class BiasEvaluator:
    """
    Quantifies subjective bias and empirical neutrality of persona analyses.
    Uses SentenceTransformer embeddings to calculate cosine similarity against
    canonical Optimistic and Pessimistic anchor vectors.
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self._model = None
        self.anchor_pos: Optional[np.ndarray] = None
        self.anchor_neg: Optional[np.ndarray] = None

    def _ensure_initialized(self):
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            self._model = SentenceTransformer(self.model_name)
            
            pos_matrix = self._model.encode(OPTIMISTIC_ANCHORS)
            neg_matrix = self._model.encode(PESSIMISTIC_ANCHORS)

            pos_mean = np.mean(pos_matrix, axis=0)
            neg_mean = np.mean(neg_matrix, axis=0)

            self.anchor_pos = pos_mean.reshape(1, -1)
            self.anchor_neg = neg_mean.reshape(1, -1)
            self._cosine_similarity = cosine_similarity
        except Exception as e:
            logger.warning(f"SentenceTransformer initialization skipped/failed: {e}. Falling back to TextBlob polarity.")
            self._model = False

    def _calculate_single_score(self, text: str) -> BiasMetrics:
        self._ensure_initialized()
        polarity = float(TextBlob(text).sentiment.polarity)

        if self._model and self.anchor_pos is not None and self.anchor_neg is not None:
            try:
                vec = self._model.encode([text])
                sim_pos = float(self._cosine_similarity(vec, self.anchor_pos)[0][0])
                sim_neg = float(self._cosine_similarity(vec, self.anchor_neg)[0][0])
                bias_score = float(sim_pos - sim_neg)
                neutrality_index = float(max(0.0, min(1.0, 1.0 - abs(bias_score))))
                return BiasMetrics(
                    bias_score=bias_score,
                    neutrality_index=neutrality_index,
                    polarity=polarity
                )
            except Exception as e:
                logger.warning(f"Embedding scoring failed: {e}. Using sentiment fallback.")

        # Fallback using TextBlob polarity
        bias_score = polarity
        neutrality_index = max(0.0, min(1.0, 1.0 - abs(polarity)))
        return BiasMetrics(
            bias_score=bias_score,
            neutrality_index=neutrality_index,
            polarity=polarity
        )

    def evaluate_batch(self, agent_responses: List[PersonaResponse]) -> List[AgentEvaluationResult]:
        evaluated_results: List[AgentEvaluationResult] = []

        for response in agent_responses:
            content_obj = response.get('content')
            if hasattr(content_obj, 'summary'):
                text_to_analyze = content_obj.summary
            elif isinstance(content_obj, dict):
                text_to_analyze = content_obj.get('summary', str(content_obj))
            else:
                text_to_analyze = str(content_obj)
            
            metrics = self._calculate_single_score(text_to_analyze)
            
            evaluated_results.append(AgentEvaluationResult(
                role=response['role'],
                icon=response['icon'],
                persona=response['persona'],
                content=text_to_analyze,
                metrics=metrics
            ))
        
        return evaluated_results
