import os

from fastapi import FastAPI

from api.routers import auth, catalogo, autos, ouvidorias, dashboard, admin, dashboard_qualidade_novo, relatorio_base

app = FastAPI(
    title="ARTESP Ouvidorias API",
    version="1.0",
    description="Backend da aplicação de Ouvidorias ARTESP.",
    root_path=os.getenv("ROOT_PATH", ""),
)

app.include_router(auth.router,       prefix="/auth",       tags=["auth"])
app.include_router(catalogo.router,   prefix="/catalogo",   tags=["catalogo"])
app.include_router(autos.router,      prefix="/autos",      tags=["autos"])
app.include_router(ouvidorias.router, prefix="/ouvidorias", tags=["ouvidorias"])
app.include_router(dashboard.router,  prefix="/dashboard",  tags=["dashboard"])
app.include_router(admin.router,      prefix="/admin",      tags=["admin"])
app.include_router(dashboard_qualidade_novo.router, prefix="/dashboard", tags=["dashboard-v2"])
app.include_router(relatorio_base.router, prefix="/relatorio-base", tags=["relatorio-base"])
