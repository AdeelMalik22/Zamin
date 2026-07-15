import re
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import ListingStatus, SearchMode
from app.exceptions.custom_exceptions import ValidationAppError
from app.models.city import City
from app.models.listing import Listing
from app.repositories.listing_repository import LISTING_LOAD_OPTIONS
from app.utils.helpers import escape_like, validate_regex_pattern


def normalized_search_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def fuzzy_score(query: str, listing: Listing) -> float:
    normalized_query = normalized_search_text(query)
    if len(normalized_query) < 3:
        return 0.0
    target = normalized_search_text(f"{listing.title} {listing.address}")
    if not target:
        return 0.0
    if normalized_query in target:
        return 1.0
    query_tokens = normalized_query.split()
    target_tokens = target.split()
    token_scores = [
        max(SequenceMatcher(None, query_token, target_token).ratio() for target_token in target_tokens)
        for query_token in query_tokens
    ]
    return max(sum(token_scores) / len(token_scores), SequenceMatcher(None, normalized_query, target).ratio())


class SearchService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(
        self,
        *,
        city: str | None,
        city_id: int | None,
        query: str | None,
        search_mode: SearchMode,
        page: int,
        page_size: int,
    ) -> tuple[int, list[Listing]]:
        if search_mode == SearchMode.FUZZY and query and len(normalized_search_text(query)) < 3:
            raise ValidationAppError("fuzzy search needs at least 3 characters")

        filters: list[Any] = [Listing.status == ListingStatus.APPROVED]
        joins_city = city is not None
        if city is not None:
            filters.append(func.lower(City.name) == city.casefold())
        if city_id is not None:
            filters.append(Listing.city_id == city_id)
        if query and search_mode == SearchMode.CONTAINS:
            needle = f"%{escape_like(query.casefold())}%"
            filters.append(
                or_(
                    func.lower(Listing.title).like(needle, escape="\\"),
                    func.lower(Listing.address).like(needle, escape="\\"),
                )
            )
        elif query and search_mode == SearchMode.REGEX:
            validate_regex_pattern(query)
            filters.append(or_(Listing.title.op("REGEXP")(query), Listing.address.op("REGEXP")(query)))

        statement = select(Listing)
        count_statement = select(func.count(Listing.id))
        if joins_city:
            statement = statement.join(Listing.city)
            count_statement = count_statement.join(Listing.city)
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)

        if search_mode == SearchMode.FUZZY and query:
            candidates = (
                self.db.execute(
                    statement.options(*LISTING_LOAD_OPTIONS)
                    .order_by(Listing.created_at.desc())
                    .limit(settings.max_fuzzy_candidates)
                )
                .unique()
                .scalars()
                .all()
            )
            matches = [(fuzzy_score(query, listing), listing) for listing in candidates]
            matches = [(score, listing) for score, listing in matches if score >= 0.60]
            matches.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
            total = len(matches)
            return total, [listing for _, listing in matches[(page - 1) * page_size : page * page_size]]

        total = self.db.scalar(count_statement) or 0
        listings = (
            self.db.execute(
                statement.options(*LISTING_LOAD_OPTIONS)
                .order_by(Listing.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .unique()
            .scalars()
            .all()
        )
        return total, listings
