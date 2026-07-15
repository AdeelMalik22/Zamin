from app.core.constants import ListingStatus, SearchMode, UserRole
from app.core.security import hash_password
from app.models.user import User
from app.schemas.city import CityCreate
from app.schemas.listing import ListingCreate, ListingUpdate, RejectListing
from app.schemas.user import EditorCreate
from app.services.city_service import CityService
from app.services.listing_service import ListingService
from app.services.search_service import SearchService
from app.services.user_service import UserService
from app.utils.helpers import commit_or_raise, new_uuid


def test_rejected_listing_is_resubmitted_then_becomes_public(db):
    admin = User(
        id=new_uuid(),
        full_name="Platform Admin",
        email="admin@example.com",
        phone_number="+923001234567",
        hashed_password=hash_password("StrongPass123!"),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    commit_or_raise(db, "unable to create admin")
    city = CityService(db).create(CityCreate(name="Lahore", province_or_region="Punjab"))
    editor, _ = UserService(db).create_editor(
        EditorCreate(
            full_name="Ayesha Agent",
            email="ayesha@example.com",
            phone_number="+923111234567",
            assigned_city_ids=[city.id],
            password="EditorPass123!",
        )
    )
    service = ListingService(db)
    listing = service.create_for_editor(
        ListingCreate(
            title="House in Gulberg",
            description="Family home",
            city_id=city.id,
            address="Main Boulevard, Gulberg, Lahore",
            property_type="house",
        ),
        editor,
    )
    assert listing.status == ListingStatus.PENDING

    service.reject(listing.id, RejectListing(reason="Please improve the photos").reason, admin)
    listing = service.update_for_editor(listing.id, ListingUpdate(address="Gulberg III, Lahore"), editor)
    assert listing.status == ListingStatus.PENDING

    service.approve(listing.id, admin)
    total, public_listings = SearchService(db).search(
        city="Lahore",
        city_id=None,
        query="Gulberg",
        search_mode=SearchMode.CONTAINS,
        page=1,
        page_size=20,
    )
    assert total == 1
    assert public_listings[0].id == listing.id
