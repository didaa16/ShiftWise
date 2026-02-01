"""
ShiftWise - Migration Intelligente de VMs vers OpenShift

Point d'entrée principal de l'application FastAPI.

Ce fichier configure :
- L'application FastAPI
- Les routes API
- Le CORS
- La documentation automatique
- L'initialisation de la base de données
"""

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import auth, users, roles

# Création de l'application FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    **ShiftWise** - Plateforme intelligente de migration de machines virtuelles vers OpenShift.

    ## Fonctionnalités principales

    * **Authentification JWT** - Connexion sécurisée avec tokens
    * **RBAC** - Contrôle d'accès basé sur les rôles
    * **Multi-tenancy** - Isolation complète des données par organisation
    * **Gestion des utilisateurs** - CRUD complet avec permissions
    * **Gestion des rôles** - Rôles système et personnalisés

    ## Authentification

    1. Obtenez un token via `/api/v1/auth/login`
    2. Utilisez le token dans l'en-tête : `Authorization: Bearer <token>`
    3. Renouvelez le token avec `/api/v1/auth/refresh`

    ## Permissions

    Les permissions sont gérées via RBAC :
    - **super_admin** : Accès complet au système
    - **admin** : Gestion complète du tenant
    - **user** : Accès aux ressources assignées
    - **viewer** : Lecture seule

    ## Multi-tenancy

    Chaque utilisateur appartient à un tenant (organisation).
    Les données sont automatiquement isolées par tenant.
    """,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    openapi_url="/openapi.json"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],  # Permet tous les HTTP methods
    allow_headers=["*"],  # Permet tous les headers
)


# Event handlers
@app.on_event("startup")
async def startup_event():
    """
    Exécuté au démarrage de l'application.

    Initialise la base de données et crée les tables si nécessaire.
    """
    print(f"🚀 Démarrage de {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📊 Base de données : {settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}")

    # Initialiser la base de données
    init_db()
    print("✅ Base de données initialisée")

    print(f"📖 Documentation disponible sur : http://localhost:8000/docs")
    print(f"🔐 Mode debug : {settings.DEBUG}")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Exécuté à l'arrêt de l'application.
    """
    print(f"🛑 Arrêt de {settings.APP_NAME}")


# Route racine
@app.get("/", tags=["Health"])
def read_root():
    """
    Route racine de l'API.

    Retourne les informations de base sur l'application.

    **Response :**
    ```json
    {
        "name": "ShiftWise",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }
    ```
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "description": "Migration Intelligente de VMs vers OpenShift"
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
def health_check():
    """
    Endpoint de vérification de santé de l'application.

    Utilisé par les outils de monitoring et les load balancers
    pour vérifier que l'application fonctionne correctement.

    **Response :**
    ```json
    {
        "status": "healthy",
        "app": "ShiftWise",
        "version": "1.0.0"
    }
    ```
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# Inclusion des routers API v1
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"],
)

app.include_router(
    users.router,
    prefix=f"{settings.API_V1_PREFIX}/users",
    tags=["Users"],
)

app.include_router(
    roles.router,
    prefix=f"{settings.API_V1_PREFIX}/roles",
    tags=["Roles"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Gestionnaire d'exceptions global.

    Capture toutes les exceptions non gérées et retourne
    une réponse JSON standardisée.
    """
    if settings.DEBUG:
        # En mode debug, afficher le détail de l'erreur
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "path": str(request.url)
            }
        )
    else:
        # En production, message générique
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Une erreur interne est survenue. Contactez l'administrateur."
            }
        )


# Point d'entrée pour uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,  # Auto-reload en mode debug
        log_level="info"
    )