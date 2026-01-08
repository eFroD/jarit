from fastapi import APIRouter, Depends
from jarit.api.v1.endpoints import recipes
from jarit.api.v1.endpoints import integrations
from jarit.api.v1.endpoints import auth, users
from jarit.api.v1.endpoints.users import get_current_user

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router, prefix="/auth", tags=["authentication"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(users.admin_router, prefix="/admin", tags=["admin"])
router.include_router(
    recipes.router,
    prefix="/recipes",
    tags=["recipes"],
    dependencies=[Depends(get_current_user)],
)
router.include_router(
    integrations.router,
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(get_current_user)],
)
