from fastapi import FastAPI

from api.routers import auth, catalogo, autos, ouvidorias, dashboard, admin

app = FastAPI(
    title="ARTESP Ouvidorias API",
    version="1.0",
    description="Backend da aplicação de Ouvidorias ARTESP.",
)

app.include_router(auth.router,       prefix="/auth",       tags=["auth"])
app.include_router(catalogo.router,   prefix="/catalogo",   tags=["catalogo"])
app.include_router(autos.router,      prefix="/autos",      tags=["autos"])
app.include_router(ouvidorias.router, prefix="/ouvidorias", tags=["ouvidorias"])
app.include_router(dashboard.router,  prefix="/dashboard",  tags=["dashboard"])
app.include_router(admin.router,      prefix="/admin",      tags=["admin"])
