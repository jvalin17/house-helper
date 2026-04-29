"""Auth API routes — signup, login, profile."""

from fastapi import APIRouter, HTTPException, Request

from auth.service import AuthService


def create_auth_router(auth_service: AuthService) -> APIRouter:
    router = APIRouter(prefix="/api/auth")

    @router.post("/signup")
    def signup(data: dict):
        try:
            result = auth_service.signup(
                email=data.get("email", ""),
                password=data.get("password", ""),
                name=data.get("name", ""),
            )
            return result
        except ValueError as e:
            raise HTTPException(400, detail=str(e))

    @router.post("/login")
    def login(data: dict):
        try:
            result = auth_service.login(
                email=data.get("email", ""),
                password=data.get("password", ""),
            )
            return result
        except ValueError as e:
            raise HTTPException(401, detail=str(e))

    @router.get("/me")
    def get_profile(request: Request):
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(401, detail="Not authenticated")
        user = auth_service.get_user(user_id)
        if not user:
            raise HTTPException(404, detail="User not found")
        return user

    @router.put("/me")
    def update_profile(request: Request, data: dict):
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            raise HTTPException(401, detail="Not authenticated")
        user = auth_service.update_user(user_id, name=data.get("name"))
        return user

    @router.get("/config")
    def get_config():
        """Public endpoint — tells frontend which auth mode is active."""
        from auth.middleware import get_auth_mode
        return {"auth_mode": get_auth_mode()}

    return router
