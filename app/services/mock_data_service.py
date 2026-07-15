"""Repeatable development data for local demos and manual API testing."""

from dataclasses import asdict, dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import ListingStatus, PropertyType, UserRole
from app.core.security import hash_password
from app.exceptions.custom_exceptions import ConflictError
from app.models.city import City
from app.models.listing import Listing, ListingImage, ListingStatusHistory
from app.models.user import User
from app.repositories.city_repository import CityRepository
from app.repositories.listing_repository import ListingRepository
from app.repositories.user_repository import UserRepository
from app.services.storage_service import LocalListingStorage, PreparedImage
from app.utils.helpers import commit_or_raise, new_uuid, utc_now


MOCK_ADMIN_EMAIL = "mock.admin@example.com"
MOCK_EDITOR_EMAIL_TEMPLATE = "editor{number:02d}@mock.local"
MOCK_CITY_NAME_TEMPLATE = "Mock City {number:02d}"
MOCK_LISTING_TITLE_TEMPLATE = "Mock Listing E{editor:02d}-L{listing:02d}"

# A valid 1x1 transparent PNG, kept tiny so only 20 local mock files are created.
MOCK_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\x60\xf8\x0f\x00"
    b"\x01\x05\x01\x01\x27\x18\xe3f\x00\x00\x00\x00IEND\xaeB`\x82"
)


@dataclass(frozen=True, slots=True)
class MockDataSummary:
    admin_email: str
    editors: int
    cities: int
    listings: int
    approved_listings: int
    pending_listings: int
    listing_images: int
    status_history_records: int
    editors_created_this_run: int
    listings_created_this_run: int
    images_created_this_run: int

    def to_dict(self) -> dict:
        return asdict(self)


class MockDataService:
    """Seeds a deterministic, idempotent dataset.

    A fresh database receives one admin, twenty cities, ten editors, twenty
    listings per editor (ten approved and ten pending), twenty editor-city
    associations, twenty cover images, and the corresponding audit history.
    Re-running the command fills gaps instead of duplicating rows.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.cities = CityRepository(db)
        self.listings = ListingRepository(db)
        self.storage = LocalListingStorage()

    def seed(self, *, admin_password: str) -> MockDataSummary:
        admin = self._get_or_create_admin(admin_password)
        cities = self._get_or_create_cities()
        self.db.flush()
        editors, editors_created = self._get_or_create_editors(cities)
        self.db.flush()
        mock_listings, listings_created = self._get_or_create_listings(admin, editors, cities)
        commit_or_raise(self.db, "unable to save mock users, cities, and listings")

        images_created = self._add_mock_images(mock_listings)
        if images_created:
            commit_or_raise(self.db, "unable to save mock listing images")

        listing_ids = [listing.id for listing in mock_listings]
        approved_count = sum(listing.status == ListingStatus.APPROVED for listing in mock_listings)
        pending_count = sum(listing.status == ListingStatus.PENDING for listing in mock_listings)
        image_count = self.db.scalar(
            select(func.count(ListingImage.id)).where(ListingImage.listing_id.in_(listing_ids))
        ) or 0
        history_count = self.db.scalar(
            select(func.count(ListingStatusHistory.id)).where(ListingStatusHistory.listing_id.in_(listing_ids))
        ) or 0
        return MockDataSummary(
            admin_email=admin.email,
            editors=len(editors),
            cities=len(cities),
            listings=len(mock_listings),
            approved_listings=approved_count,
            pending_listings=pending_count,
            listing_images=image_count,
            status_history_records=history_count,
            editors_created_this_run=editors_created,
            listings_created_this_run=listings_created,
            images_created_this_run=images_created,
        )

    def _get_or_create_admin(self, password: str) -> User:
        existing_admin = self.users.get_admin()
        if existing_admin is not None:
            return existing_admin
        existing_email = self.users.get_by_email(MOCK_ADMIN_EMAIL)
        if existing_email is not None:
            raise ConflictError("the mock admin email is already assigned to a non-admin account")
        admin = User(
            id=new_uuid(),
            full_name="Mock Platform Admin",
            email=MOCK_ADMIN_EMAIL,
            phone_number="+923000000001",
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.db.add(admin)
        return admin

    def _get_or_create_cities(self) -> list[City]:
        records: list[City] = []
        for number in range(1, 21):
            name = MOCK_CITY_NAME_TEMPLATE.format(number=number)
            city = self.cities.get_by_name(name)
            if city is None:
                city = City(
                    name=name,
                    province_or_region=f"Mock Region {(number - 1) // 5 + 1}",
                    is_active=True,
                )
                self.db.add(city)
            records.append(city)
        return records

    def _get_or_create_editors(self, cities: list[City]) -> tuple[list[User], int]:
        editors: list[User] = []
        created_count = 0
        for number in range(1, 11):
            email = MOCK_EDITOR_EMAIL_TEMPLATE.format(number=number)
            editor = self.users.get_by_email(email)
            if editor is None:
                editor = User(
                    id=new_uuid(),
                    full_name=f"Mock Editor {number:02d}",
                    email=email,
                    phone_number=f"+92300000{number:04d}",
                    hashed_password=hash_password(f"MockEditor{number:02d}!"),
                    role=UserRole.EDITOR,
                    is_active=True,
                )
                self.db.add(editor)
                created_count += 1
            elif editor.role != UserRole.EDITOR:
                raise ConflictError(f"{email} is already assigned to a non-editor account")
            # Two city assignments per editor produces 20 editor-city records.
            editor.assigned_cities = [cities[(number - 1) * 2], cities[(number - 1) * 2 + 1]]
            editors.append(editor)
        return editors, created_count

    def _get_or_create_listings(
        self,
        admin: User,
        editors: list[User],
        cities: list[City],
    ) -> tuple[list[Listing], int]:
        records: list[Listing] = []
        created_count = 0
        property_types = list(PropertyType)
        for editor_number, editor in enumerate(editors, start=1):
            assigned_cities = [cities[(editor_number - 1) * 2], cities[(editor_number - 1) * 2 + 1]]
            for listing_number in range(1, 21):
                title = MOCK_LISTING_TITLE_TEMPLATE.format(editor=editor_number, listing=listing_number)
                listing = self.listings.get_by_submitter_and_title(editor.id, title)
                if listing is None:
                    is_approved = listing_number <= 10
                    city = assigned_cities[(listing_number - 1) % len(assigned_cities)]
                    listing = Listing(
                        id=new_uuid(),
                        title=title,
                        description=(
                            f"Mock property {listing_number:02d} submitted by Mock Editor {editor_number:02d}. "
                            "Generated for development and API testing."
                        ),
                        city_id=city.id,
                        address=f"{listing_number * 10} Demo Street, {city.name}",
                        price=Decimal("1000000.00") + Decimal(editor_number * 100000 + listing_number * 5000),
                        property_type=property_types[(editor_number + listing_number - 2) % len(property_types)],
                        status=ListingStatus.APPROVED if is_approved else ListingStatus.PENDING,
                        submitted_by_id=editor.id,
                        reviewed_by_id=admin.id if is_approved else None,
                        reviewed_at=utc_now() if is_approved else None,
                    )
                    self.db.add(listing)
                    self.db.add(
                        ListingStatusHistory(
                            listing_id=listing.id,
                            from_status=None,
                            to_status=ListingStatus.PENDING,
                            changed_by_id=editor.id,
                            reason="Mock listing submitted for review",
                        )
                    )
                    if is_approved:
                        self.db.add(
                            ListingStatusHistory(
                                listing_id=listing.id,
                                from_status=ListingStatus.PENDING,
                                to_status=ListingStatus.APPROVED,
                                changed_by_id=admin.id,
                                reason="Mock listing approved",
                            )
                        )
                    created_count += 1
                records.append(listing)
        return records, created_count

    def _add_mock_images(self, listings: list[Listing]) -> int:
        approved = [listing for listing in listings if listing.status == ListingStatus.APPROVED]
        created_count = 0
        for listing in approved[:20]:
            if self.listings.images_for_listing(listing.id):
                continue
            stored = self.storage.store_images(
                listing.id,
                [PreparedImage(content=MOCK_PNG, extension="png")],
            )
            try:
                image = stored[0]
                self.db.add(
                    ListingImage(
                        id=image.image_id,
                        listing_id=listing.id,
                        image_path=image.image_url,
                        is_cover=True,
                    )
                )
                created_count += 1
            except Exception:
                for item in stored:
                    item.disk_path.unlink(missing_ok=True)
                raise
        return created_count
