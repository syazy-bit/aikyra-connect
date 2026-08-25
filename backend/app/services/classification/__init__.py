"""Deterministic problem-analysis building blocks.

The rule classifier is the honest baseline for Problem DNA generation.
A future LLM-backed classifier will implement the same classify() contract
and be selected behind the service boundary — never inside routes or
repositories.
"""

from app.services.classification.rule_classifier import RuleBasedClassifier
from app.services.classification.schemas import ClassificationResult

__all__ = ["ClassificationResult", "RuleBasedClassifier"]
