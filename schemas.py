from typing import Optional
from pydantic import BaseModel, EmailStr

# ---------- PRODUCTOS ----------

class ProductoBase(BaseModel):
    nombre: str
    descripcion: str | None = None
    precio: float
    stock: int
    imagen_url: str | None = None
    categoria: str | None = None


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(ProductoBase):
    # si quisieras hacer PATCH podrías poner los campos como Optional
    pass


class ProductoOut(ProductoBase):
    id: int

    class Config:
        from_attributes = True


# ---------- AUTH ----------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------- USUARIOS ----------

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
