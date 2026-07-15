from app.api.dependencies import get_current_editor_or_admin
from app.api.v1.endpoints.editor_listings import (
    create_listing as create_editor_listing,
    get_listing as get_editor_listing,
    list_listings as list_editor_listings,
    update_listing as update_editor_listing,
)
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


def test_admin_can_manage_editor_listing_routes(db):
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

    assert get_current_editor_or_admin(admin) is admin

    admin_listing = create_editor_listing(
        ListingCreate(
            title="Admin Listed Apartment",
            description="A ready-to-move family apartment in Gulberg.",
            city_id=city.id,
            address="MM Alam Road, Gulberg III, Lahore",
            property_type="apartment",
        ),
        db=db,
        actor=admin,
    )
    assert admin_listing["status"] == ListingStatus.APPROVED

    listed = list_editor_listings(status_filter=None, page=1, page_size=20, db=db, actor=admin)
    assert listed["total"] == 2
    assert {item["id"] for item in listed["items"]} == {listing.id, admin_listing["id"]}

    fetched = get_editor_listing(listing.id, db=db, actor=admin)
    assert fetched["submitted_by"]["id"] == editor.id

    updated = update_editor_listing(
        listing.id,
        ListingUpdate(title="Updated House in Gulberg", address="Gulberg III, Lahore"),
        db=db,
        actor=admin,
    )

    assert updated["submitted_by"]["id"] == editor.id
    assert updated["title"] == "Updated House in Gulberg"
    assert updated["address"] == "Gulberg III, Lahore"
