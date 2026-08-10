"""Strategy pattern: each scoring rule is its own class implementing a
common interface (`score(destination, context) -> float`). The scorer
that combines them (RecommendationScorer, a Composite) doesn't know or
care how many strategies exist -- add a new one without touching the
others. This replaces the single hard-coded formula the monolith used.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from models import Destination


@dataclass
class ScoringContext:
    preferences: set
    visited_tags: set


class ScoringStrategy(ABC):
    @abstractmethod
    def score(self, destination: Destination, context: ScoringContext) -> float:
        ...


class PreferenceMatchStrategy(ScoringStrategy):
    """Rewards tags that match the user's stated interests most heavily."""

    WEIGHT = 3.0

    def score(self, destination: Destination, context: ScoringContext) -> float:
        return self.WEIGHT * len(destination.tags & context.preferences)


class VisitedSimilarityStrategy(ScoringStrategy):
    """Rewards tags similar to places the user has already itinerary-ed."""

    WEIGHT = 1.5

    def score(self, destination: Destination, context: ScoringContext) -> float:
        return self.WEIGHT * len(destination.tags & context.visited_tags)


class PopularityStrategy(ScoringStrategy):
    WEIGHT = 0.1

    def score(self, destination: Destination, context: ScoringContext) -> float:
        return self.WEIGHT * destination.popularity_score


class RatingStrategy(ScoringStrategy):
    WEIGHT = 0.5

    def score(self, destination: Destination, context: ScoringContext) -> float:
        avg = destination.average_rating()
        return self.WEIGHT * avg if avg else 0.0


class RecommendationScorer:
    """Composite: runs every registered strategy and sums the result.
    Default strategy set mirrors the monolith's original formula;
    pass a custom `strategies` list to experiment with new weightings
    without editing this class."""

    def __init__(self, strategies: list[ScoringStrategy] = None):
        self._strategies = strategies or [
            PreferenceMatchStrategy(),
            VisitedSimilarityStrategy(),
            PopularityStrategy(),
            RatingStrategy(),
        ]

    def score(self, destination: Destination, context: ScoringContext) -> float:
        return sum(strategy.score(destination, context) for strategy in self._strategies)
