"""Realistic Pakistani development data for local demos and manual testing."""

from dataclasses import asdict, dataclass
from decimal import Decimal

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import ListingStatus, PropertyType, UserRole
from app.core.security import hash_password
from app.exceptions.custom_exceptions import ConflictError
from app.models.associations import editor_cities
from app.models.city import City
from app.models.listing import Listing, ListingImage, ListingStatusHistory
from app.models.user import User
from app.repositories.city_repository import CityRepository
from app.repositories.listing_repository import ListingRepository
from app.repositories.user_repository import UserRepository
from app.services.storage_service import LocalListingStorage, PreparedImage
from app.utils.helpers import commit_or_raise, new_uuid, utc_now


@dataclass(frozen=True, slots=True)
class PakistaniCity:
    name: str
    province_or_region: str
    areas: tuple[str, str]
    base_price: Decimal


PAKISTANI_CITIES: tuple[PakistaniCity, ...] = (
    PakistaniCity("Lahore", "Punjab", ("DHA Phase 6", "Gulberg III"), Decimal("18500000")),
    PakistaniCity("Karachi", "Sindh", ("DHA Phase 8", "Bahria Town Karachi"), Decimal("22000000")),
    PakistaniCity("Islamabad", "Islamabad Capital Territory", ("F-11", "Bahria Enclave"), Decimal("25000000")),
    PakistaniCity("Rawalpindi", "Punjab", ("Bahria Town Phase 7", "Satellite Town"), Decimal("15000000")),
    PakistaniCity("Faisalabad", "Punjab", ("Madina Town", "Canal Road"), Decimal("11500000")),
    PakistaniCity("Multan", "Punjab", ("DHA Multan", "Bosan Road"), Decimal("10500000")),
    PakistaniCity("Peshawar", "Khyber Pakhtunkhwa", ("Hayatabad Phase 3", "University Town"), Decimal("12500000")),
    PakistaniCity("Quetta", "Balochistan", ("Jinnah Town", "Samungli Road"), Decimal("9000000")),
    PakistaniCity("Gujranwala", "Punjab", ("DC Colony", "Wapda Town"), Decimal("8500000")),
    PakistaniCity("Sialkot", "Punjab", ("Cantt", "Model Town"), Decimal("9500000")),
    PakistaniCity("Bahawalpur", "Punjab", ("Model Town A", "Baghdad-ul-Jadeed"), Decimal("7500000")),
    PakistaniCity("Hyderabad", "Sindh", ("Qasimabad", "Latifabad Unit 7"), Decimal("8000000")),
    PakistaniCity("Sukkur", "Sindh", ("Military Road", "Shikarpur Road"), Decimal("7000000")),
    PakistaniCity("Abbottabad", "Khyber Pakhtunkhwa", ("Jinnahabad", "Mandian"), Decimal("9000000")),
    PakistaniCity("Murree", "Punjab", ("Kashmir Point", "Bhurban"), Decimal("18000000")),
    PakistaniCity("Gwadar", "Balochistan", ("New Town", "Marine Drive"), Decimal("6500000")),
    PakistaniCity("Sheikhupura", "Punjab", ("Housing Colony", "Batti Chowk"), Decimal("6000000")),
    PakistaniCity("Jhelum", "Punjab", ("Citi Housing", "Kala Gujran"), Decimal("7000000")),
    PakistaniCity("Sargodha", "Punjab", ("University Road", "Satellite Town"), Decimal("6500000")),
    PakistaniCity("Rahim Yar Khan", "Punjab", ("Model Town", "Abu Dhabi Road"), Decimal("6000000")),
)


@dataclass(frozen=True, slots=True)
class DemoAccount:
    full_name: str
    email: str
    phone_number: str
    password: str


DEMO_ADMIN = DemoAccount(
    full_name="Adeel Admin",
    email="adeel.admin@zamin.demo",
    phone_number="+923001000000",
    password="AdminDemo@2026!",
)

DEMO_EDITORS: tuple[DemoAccount, ...] = (
    DemoAccount("Ali Raza", "ali.raza@zamin.demo", "+923001000001", "AliDemo@2026!"),
    DemoAccount("Ayesha Khan", "ayesha.khan@zamin.demo", "+923001000002", "AyeshaDemo@2026!"),
    DemoAccount("Usman Tariq", "usman.tariq@zamin.demo", "+923001000003", "UsmanDemo@2026!"),
    DemoAccount("Hira Ahmed", "hira.ahmed@zamin.demo", "+923001000004", "HiraDemo@2026!"),
    DemoAccount("Hamza Malik", "hamza.malik@zamin.demo", "+923001000005", "HamzaDemo@2026!"),
    DemoAccount("Mariam Iqbal", "mariam.iqbal@zamin.demo", "+923001000006", "MariamDemo@2026!"),
    DemoAccount("Bilal Hussain", "bilal.hussain@zamin.demo", "+923001000007", "BilalDemo@2026!"),
    DemoAccount("Sana Javed", "sana.javed@zamin.demo", "+923001000008", "SanaDemo@2026!"),
    DemoAccount("Zain Abbas", "zain.abbas@zamin.demo", "+923001000009", "ZainDemo@2026!"),
    DemoAccount("Fatima Noor", "fatima.noor@zamin.demo", "+923001000010", "FatimaDemo@2026!"),
)

PROPERTY_LABELS = {
    PropertyType.HOUSE: "family home",
    PropertyType.PLOT: "residential plot",
    PropertyType.APARTMENT: "apartment",
    PropertyType.COMMERCIAL: "commercial unit",
    PropertyType.OTHER: "property",
}
TITLE_TEMPLATES = (
    "Spacious {property_label} in {area}, {city}",
    "Well-located {property_label} near {area}, {city}",
    "Ready-to-move {property_label} in {area}, {city}",
    "Prime {property_label} available in {area}, {city}",
)

# A valid 1x1 transparent PNG. Only twenty local demo images are created.
DEMO_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\x60\xf8\x0f\x00"
    b"\x01\x05\x01\x01\x27\x18\xe3f\x00\x00\x00\x00IEND\xaeB`\x82"
)


@dataclass(frozen=True, slots=True)
class DemoDataSummary:
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
    legacy_mock_rows_removed: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DemoSeedResult:
    summary: DemoDataSummary
    credentials: tuple[DemoAccount, ...]


class DemoDataService:
    """Seed idempotent, realistic local data without claiming it is live data."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.cities = CityRepository(db)
        self.listings = ListingRepository(db)
        self.storage = LocalListingStorage()

    def seed(self, *, replace_legacy_mock_data: bool = True) -> DemoSeedResult:
        removed_rows = self._remove_legacy_mock_data() if replace_legacy_mock_data else 0
        admin, admin_credentials = self._get_or_create_admin()
        cities = self._get_or_create_cities()
        self.db.flush()
        editors, editor_credentials, editors_created = self._get_or_create_editors(cities)
        self.db.flush()
        demo_listings, listings_created = self._get_or_create_listings(admin, editors, cities)
        commit_or_raise(self.db, "unable to save realistic demo users, cities, and listings")

        images_created = self._add_demo_images(demo_listings)
        if images_created:
            commit_or_raise(self.db, "unable to save realistic demo listing images")

        listing_ids = [listing.id for listing in demo_listings]
        image_count = self.db.scalar(
            select(func.count(ListingImage.id)).where(ListingImage.listing_id.in_(listing_ids))
        ) or 0
        history_count = self.db.scalar(
            select(func.count(ListingStatusHistory.id)).where(ListingStatusHistory.listing_id.in_(listing_ids))
        ) or 0
        summary = DemoDataSummary(
            admin_email=admin.email,
            editors=len(editors),
            cities=len(cities),
            listings=len(demo_listings),
            approved_listings=sum(item.status == ListingStatus.APPROVED for item in demo_listings),
            pending_listings=sum(item.status == ListingStatus.PENDING for item in demo_listings),
            listing_images=image_count,
            status_history_records=history_count,
            editors_created_this_run=editors_created,
            listings_created_this_run=listings_created,
            images_created_this_run=images_created,
            legacy_mock_rows_removed=removed_rows,
        )
        return DemoSeedResult(summary=summary, credentials=tuple([*admin_credentials, *editor_credentials]))

    def _remove_legacy_mock_data(self) -> int:
        """Remove only records from the prior `Mock …` local seed, never arbitrary data."""
        legacy_listings = self.db.scalars(select(Listing).where(Listing.title.like("Mock Listing %"))).all()
        listing_ids = [listing.id for listing in legacy_listings]
        image_paths = self.db.scalars(
            select(ListingImage.image_path).where(ListingImage.listing_id.in_(listing_ids))
        ).all() if listing_ids else []
        removed = len(legacy_listings)
        if listing_ids:
            self.db.execute(delete(ListingStatusHistory).where(ListingStatusHistory.listing_id.in_(listing_ids)))
            self.db.execute(delete(ListingImage).where(ListingImage.listing_id.in_(listing_ids)))
            self.db.execute(delete(Listing).where(Listing.id.in_(listing_ids)))
            for image_path in image_paths:
                self.storage.delete_image(image_path)

        legacy_users = self.db.scalars(
            select(User).where(or_(User.email.like("%@mock.local"), User.email == "mock.admin@example.com"))
        ).all()
        legacy_user_ids = [user.id for user in legacy_users]
        removed += len(legacy_users)
        if legacy_user_ids:
            self.db.execute(delete(editor_cities).where(editor_cities.c.user_id.in_(legacy_user_ids)))
            self.db.execute(delete(User).where(User.id.in_(legacy_user_ids)))

        legacy_cities = self.db.scalars(select(City).where(City.name.like("Mock City %"))).all()
        removed += len(legacy_cities)
        if legacy_cities:
            self.db.execute(delete(City).where(City.id.in_([city.id for city in legacy_cities])))
        self.db.flush()
        return removed

    def _get_or_create_admin(self) -> tuple[User, tuple[DemoAccount, ...]]:
        admin = self.users.get_by_email(DEMO_ADMIN.email)
        if admin is not None:
            if admin.role != UserRole.ADMIN:
                raise ConflictError(f"{DEMO_ADMIN.email} is already assigned to a non-admin account")
            admin.full_name = DEMO_ADMIN.full_name
            admin.phone_number = DEMO_ADMIN.phone_number
            admin.hashed_password = hash_password(DEMO_ADMIN.password)
            admin.is_active = True
            return admin, (DEMO_ADMIN,)

        existing_admin = self.users.get_admin()
        if existing_admin is not None:
            # Preserve a real admin if the seed is accidentally run in a non-empty local database.
            return existing_admin, ()
        admin = User(
            id=new_uuid(),
            full_name=DEMO_ADMIN.full_name,
            email=DEMO_ADMIN.email,
            phone_number=DEMO_ADMIN.phone_number,
            hashed_password=hash_password(DEMO_ADMIN.password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.db.add(admin)
        return admin, (DEMO_ADMIN,)

    def _get_or_create_cities(self) -> list[City]:
        records: list[City] = []
        for data in PAKISTANI_CITIES:
            city = self.cities.get_by_name(data.name)
            if city is None:
                city = City(name=data.name, province_or_region=data.province_or_region, is_active=True)
                self.db.add(city)
            else:
                city.province_or_region = data.province_or_region
                city.is_active = True
            records.append(city)
        return records

    def _get_or_create_editors(
        self,
        cities: list[City],
    ) -> tuple[list[User], tuple[DemoAccount, ...], int]:
        editors: list[User] = []
        created_count = 0
        credentials: list[DemoAccount] = []
        for number, account in enumerate(DEMO_EDITORS, start=1):
            editor = self.users.get_by_email(account.email)
            if editor is None:
                editor = User(
                    id=new_uuid(),
                    full_name=account.full_name,
                    email=account.email,
                    phone_number=account.phone_number,
                    hashed_password=hash_password(account.password),
                    role=UserRole.EDITOR,
                    is_active=True,
                )
                self.db.add(editor)
                created_count += 1
            elif editor.role != UserRole.EDITOR:
                raise ConflictError(f"{account.email} is already assigned to a non-editor account")
            else:
                editor.full_name = account.full_name
                editor.phone_number = account.phone_number
                editor.hashed_password = hash_password(account.password)
                editor.is_active = True
            editor.assigned_cities = [cities[(number - 1) * 2], cities[(number - 1) * 2 + 1]]
            editors.append(editor)
            credentials.append(account)
        return editors, tuple(credentials), created_count

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
            for listing_number in range(1, 21):
                city_index = (editor_number - 1) * 2 + (listing_number - 1) % 2
                city = cities[city_index]
                city_data = PAKISTANI_CITIES[city_index]
                area = city_data.areas[(listing_number - 1) % 2]
                property_type = property_types[(editor_number + listing_number - 2) % len(property_types)]
                property_label = PROPERTY_LABELS[property_type]
                title = TITLE_TEMPLATES[(listing_number - 1) % len(TITLE_TEMPLATES)].format(
                    property_label=property_label,
                    area=area,
                    city=city.name,
                )
                title = f"{title} #{editor_number:02d}{listing_number:02d}"
                listing = self.listings.get_by_submitter_and_title(editor.id, title)
                if listing is None:
                    is_approved = listing_number <= 10
                    listing = Listing(
                        id=new_uuid(),
                        title=title,
                        description=(
                            f"A well-presented {property_label} in {area}, {city.name}. "
                            "The location offers convenient access to schools, markets, and main roads. "
                            "Contact the listed agent for current availability and a viewing."
                        ),
                        city_id=city.id,
                        address=f"House {listing_number * 10}, {area}, {city.name}",
                        price=city_data.base_price + Decimal(editor_number * 150000 + listing_number * 350000),
                        property_type=property_type,
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
                            reason="Submitted for review",
                        )
                    )
                    if is_approved:
                        self.db.add(
                            ListingStatusHistory(
                                listing_id=listing.id,
                                from_status=ListingStatus.PENDING,
                                to_status=ListingStatus.APPROVED,
                                changed_by_id=admin.id,
                                reason="Approved for public listing",
                            )
                        )
                    created_count += 1
                records.append(listing)
        return records, created_count

    def _add_demo_images(self, listings: list[Listing]) -> int:
        approved = [listing for listing in listings if listing.status == ListingStatus.APPROVED]
        created_count = 0
        stored_images = []
        try:
            for listing in approved[:20]:
                if self.listings.images_for_listing(listing.id):
                    continue
                stored = self.storage.store_images(
                    listing.id,
                    [PreparedImage(content=DEMO_PNG, extension="png")],
                )
                image = stored[0]
                stored_images.append(image)
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
            for image in stored_images:
                image.disk_path.unlink(missing_ok=True)
            raise
        return created_count
