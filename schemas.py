from typing import Optional
from pydantic import BaseModel, EmailStr

# ==========================================
#                PRODUCTOS
# ==========================================

class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    stock: int
    imagen_url: Optional[str] = None
    categoria: Optional[str] = None


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(ProductoBase):
    # Si quisieras PATCH, podrías hacer todos los campos Optional,
    # pero para este proyecto lo dejamos así.
    pass


class ProductoOut(ProductoBase):
    id: int

    class Config:
        from_attributes = True  # para que funcione con ORM de SQLAlchemy


# ==========================================
#                AUTH
# ==========================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    token: str   # lo que devuelve tu endpoint /api/auth/login


# ==========================================
#                USUARIOS
# ==========================================

class UsuarioBase(BaseModel):
    nombre: str
    email: EmailStr
    rol: str  # "admin" o "cliente"


class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol: Optional[str] = "cliente"   # por defecto cliente


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    rol: Optional[str] = None         # "admin" / "cliente"
    password: Optional[str] = None    # para cambiar contraseña


class UsuarioOut(UsuarioBase):
    id: int

    class Config:
        from_attributes = True
