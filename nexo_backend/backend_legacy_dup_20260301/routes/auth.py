from fastapi import APIRouter, Request, Header, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from backend.services.auth_service import AuthService
import os

router = APIRouter(prefix="/auth", tags=["Auth"])

auth_service = AuthService()

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400

def get_current_user(authorization: str = Header(None)):
    """Dependency que valida el token JWT."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Falta token")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Esquema inválido")
    except ValueError:
        raise HTTPException(status_code=401, detail="Token malformado")
    
    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    return payload

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Endpoint de login."""
    token = auth_service.authenticate(req.username, req.password)
    if not token:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    return {
        "access_token": token,
        "expires_in": 86400
    }

@router.post("/register")
def register(req: RegisterRequest):
    """Crear nueva cuenta."""
    result = auth_service.create_user(req.username, req.email, req.password)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Obtener info del usuario actual."""
    return {
        "user_id": current_user.get("sub"),
        "username": current_user.get("username"),
        "exp": current_user.get("exp")
    }

@router.post("/api-key")
def create_api_key(name: str, current_user: dict = Depends(get_current_user)):
    """Generar nueva clave de API."""
    user_id = current_user.get("sub")
    key = auth_service.generate_api_key(user_id, name)
    return {"api_key": key, "name": name}

@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    """Logout (simplemente invalida el token en cliente)."""
    return {"status": "logged out"}
