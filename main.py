from typing import Optional

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from passlib.context import CryptContext

import models
import schemas
from database import SessionLocal, engine

# Crear las tablas en la BD (productos + usuarios)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Tienda Hot Wheels",
    description="API REST para la tienda de autos a escala Hot Wheels Store.",
    version="1.0.0",
)

# --- Configuración JWT ---
SECRET_KEY = "super_clave_ultra_secreta"  # cambia esto si quieres
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()

# Usamos pbkdf2_sha256 (evita el problema de bcrypt en Windows)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def crear_token(datos: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    datos_a_codificar = datos.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    datos_a_codificar.update({"exp": expire})
    token = jwt.encode(datos_a_codificar, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verificar_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # payload tiene "sub" (email) y "role"
        return payload
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado",
        )


# CORS: permite que el frontend (React/Vite) llame a esta API
origins = [
    "http://localhost:5173",  # Vite en local
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependencia para obtener la sesión de BD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- USUARIOS ----------

@app.post("/api/usuarios", response_model=schemas.UsuarioOut)
def crear_usuario(data: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # ¿existe ya un usuario con ese email?
    existente = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == data.email)
        .first()
    )
    if existente:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    rol_str = data.rol or "cliente"
    if rol_str not in ("admin", "cliente"):
        raise HTTPException(
            status_code=400,
            detail="Rol inválido (usa 'admin' o 'cliente')",
        )

    usuario = models.Usuario(
        nombre=data.nombre,
        email=data.email,
        password_hash=hash_password(data.password),
        rol=rol_str,
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


# LISTAR TODOS LOS USUARIOS (solo admin) - opcional filtro ?rol=admin|cliente
@app.get("/api/usuarios", response_model=list[schemas.UsuarioOut])
def listar_usuarios(
    rol: Optional[str] = None,
    db: Session = Depends(get_db),
    user=Depends(verificar_token),
):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin puede listar usuarios")

    query = db.query(models.Usuario)

    if rol in ("admin", "cliente"):
        query = query.filter(models.Usuario.rol == rol)

    usuarios = query.all()
    return usuarios


# LISTAR SOLO ADMINS (atajo)
@app.get("/api/usuarios/admins", response_model=list[schemas.UsuarioOut])
def listar_admins(
    db: Session = Depends(get_db),
    user=Depends(verificar_token),
):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin puede listar admins")

    admins = (
        db.query(models.Usuario)
        .filter(models.Usuario.rol == "admin")
        .all()
    )
    return admins


# ACTUALIZAR USUARIO (solo admin)
@app.put("/api/usuarios/{usuario_id}", response_model=schemas.UsuarioOut)
def actualizar_usuario(
    usuario_id: int,
    data: schemas.UsuarioUpdate,
    db: Session = Depends(get_db),
    user=Depends(verificar_token),
):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin puede actualizar usuarios")

    usuario = db.query(models.Usuario).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Campos básicos
    if data.nombre is not None:
        usuario.nombre = data.nombre

    if data.email is not None:
        # Podrías validar que no exista otro usuario con el mismo email
        usuario.email = data.email

    if data.rol is not None:
        if data.rol not in ("admin", "cliente"):
            raise HTTPException(status_code=400, detail="Rol inválido")
        usuario.rol = data.rol

    if data.password:
        usuario.password_hash = hash_password(data.password)

    db.commit()
    db.refresh(usuario)
    return usuario


# ELIMINAR USUARIO (solo admin)
@app.delete("/api/usuarios/{usuario_id}", status_code=204)
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    user=Depends(verificar_token),
):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin puede eliminar usuarios")

    usuario = db.query(models.Usuario).get(usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.delete(usuario)
    db.commit()
    return


# ---------- AUTH ----------

@app.post("/api/auth/login")
def login(data: schemas.LoginRequest, db: Session = Depends(get_db)):
    usuario = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == data.email)
        .first()
    )

    if not usuario or not verify_password(data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = crear_token(
        {"sub": usuario.email, "role": usuario.rol}  # rol es string
    )

    return {"token": token}


# --------- ENDPOINTS CRUD PRODUCTOS --------- #

# GET /api/productos - listar todos (PÚBLICO)
@app.get("/api/productos", response_model=list[schemas.ProductoOut])
def listar_productos(
    db: Session = Depends(get_db),
):
    productos = db.query(models.Producto).all()
    return productos


# GET /api/productos/{id} - obtener uno (PÚBLICO)
@app.get("/api/productos/{producto_id}", response_model=schemas.ProductoOut)
def obtener_producto(
    producto_id: int,
    db: Session = Depends(get_db),
):
    producto = db.query(models.Producto).get(producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


# POST /api/productos - crear (PROTEGIDO, idealmente solo admin)
@app.post("/api/productos", response_model=schemas.ProductoOut, status_code=201)
def crear_producto(
    data: schemas.ProductoCreate,
    db: Session = Depends(get_db),
    user=Depends(verificar_token),   # exige JWT
):
    # if user.get("role") != "admin":
    #     raise HTTPException(status_code=403, detail="Solo admin puede crear productos")

    producto = models.Producto(**data.dict())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


# PUT /api/productos/{producto_id} - actualizar (PROTEGIDO)
@app.put("/api/productos/{producto_id}", response_model=schemas.ProductoOut)
def actualizar_producto(
    producto_id: int,
    data: schemas.ProductoUpdate,
    db: Session = Depends(get_db),
    user=Depends(verificar_token),   # exige JWT
):
    # if user.get("role") != "admin":
    #     raise HTTPException(status_code=403, detail="Solo admin puede actualizar productos")

    producto = db.query(models.Producto).get(producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    for key, value in data.dict().items():
        setattr(producto, key, value)

    db.commit()
    db.refresh(producto)
    return producto


# DELETE /api/productos/{producto_id} - eliminar (PROTEGIDO)
@app.delete("/api/productos/{producto_id}", status_code=204)
def eliminar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    user=Depends(verificar_token),   # exige JWT
):
    # if user.get("role") != "admin":
    #     raise HTTPException(status_code=403, detail="Solo admin puede eliminar productos")

    producto = db.query(models.Producto).get(producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    db.delete(producto)
    db.commit()
    return
