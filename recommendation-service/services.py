from __future__ import annotations

from base import ServiceError
from models import Review
from repository import DestinationRepository
from clients import UserServiceClient, ItineraryServiceClient
from strategies import RecommendationScorer, ScoringContext


class DestinationService:
    def __init__(self, repository: DestinationRepository):
        self._repo = repository

    def search(self, query: str, category: str) -> list:
        return [d.to_summary_dict() for d in self._repo.search(query, category)]

    def get_detail(self, destination_id: str) -> dict:
        destination = self._require(destination_id)
        return destination.to_detail_dict()

    def _require(self, destination_id: str):
        destination = self._repo.find_by_id(destination_id)
        if not destination:
            raise ServiceError("Destination not found", 404)
        return destination


class ReviewService:
    def __init__(self, repository: DestinationRepository):
        self._repo = repository

    def add_review(self, destination_id: str, user_id: str, user_name: str, rating, comment: str) -> dict:
        if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
            raise ServiceError("rating must be a number between 1 and 5", 400)
        destination = self._repo.find_by_id(destination_id)
        if not destination:
            raise ServiceError("Destination not found", 404)

        review = Review(user_id=user_id, user_name=user_name, rating=rating, comment=(comment or "").strip())
        destination.add_review(review)
        self._repo.save_review(destination)
        return {"review": review.to_dict(), "avg_rating": destination.average_rating()}


class RecommendationService:
    """Orchestrates the cross-service call pattern: pulls the user's
    preferences from User Service and their visited tags from
    Itinerary Service, then asks the RecommendationScorer to rank
    every destination this service owns."""

    def __init__(
        self,
        repository: DestinationRepository,
        user_client: UserServiceClient,
        itinerary_client: ItineraryServiceClient,
        scorer: RecommendationScorer = None,
    ):
        self._repo = repository
        self._user_client = user_client
        self._itinerary_client = itinerary_client
        self._scorer = scorer or RecommendationScorer()

    def recommend_for(self, user_id: str, limit: int = 10) -> list:
        preferences = self._user_client.get_preferences(user_id)
        visited_ids = self._itinerary_client.get_visited_destination_ids(user_id)

        destinations = self._repo.all()
        visited_tags = set()
        for d in destinations:
            if d.id in visited_ids:
                visited_tags |= d.tags

        context = ScoringContext(preferences=preferences, visited_tags=visited_tags)
        scored = [(self._scorer.score(d, context), d) for d in destinations]
        scored.sort(key=lambda pair: pair[0], reverse=True)

        return [d.to_summary_dict(match_score=score) for score, d in scored[:limit]]
