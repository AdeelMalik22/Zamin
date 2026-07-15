from fastapi import APIRouter

from app.api.v1.endpoints import admin_listings, auth, cities, editor_listings, editors, public


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cities.router)
api_router.include_router(editors.router)
api_router.include_router(admin_listings.router)
api_router.include_router(editor_listings.router)
api_router.include_router(public.router)
