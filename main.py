from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import models
import schemas
from database import SessionLocal, engine

# Crear las tablas en la BD
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS: permite que el frontend (React/Vite) llame a esta API
origins = [
    "http://localhost:5173",  # Vite en local
    # aquí después puedes sumar la URL de producción si la tienes
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


# --------- ENDPOINTS CRUD --------- #

# GET /api/productos - listar todos
@app.get("/api/productos", response_model=list[schemas.ProductoOut])
def listar_productos(db: Session = Depends(get_db)):
    productos = db.query(models.Producto).all()
    return productos


# GET /api/productos/{id} - obtener uno
@app.get("/api/productos/{producto_id}", response_model=schemas.ProductoOut)
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).get(producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


# POST /api/productos - crear
@app.post("/api/productos", response_model=schemas.ProductoOut, status_code=201)
def crear_producto(data: schemas.ProductoCreate, db: Session = Depends(get_db)):
    producto = models.Producto(**data.dict())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


# PUT /api/productos/{producto_id} - actualizar
@app.put("/api/productos/{producto_id}", response_model=schemas.ProductoOut)
def actualizar_producto(
    producto_id: int,
    data: schemas.ProductoUpdate,
    db: Session = Depends(get_db),
):
    producto = db.query(models.Producto).get(producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    for key, value in data.dict().items():
        setattr(producto, key, value)

    db.commit()
    db.refresh(producto)
    return producto


# DELETE /api/productos/{producto_id} - eliminar
@app.delete("/api/productos/{producto_id}", status_code=204)
def eliminar_producto(producto_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).get(producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    db.delete(producto)
    db.commit()
    return
