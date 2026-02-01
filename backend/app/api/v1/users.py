"""
ShiftWise User Management Routes

Routes pour la gestion CRUD des utilisateurs :
- Création d'utilisateurs
- Listing avec pagination et filtres
- Mise à jour
- Suppression
- Gestion des rôles

Toutes les routes respectent le RBAC et le multi-tenancy.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserRead,
    UserReadWithRoles,
    UserList
)
from app.schemas.auth import MessageResponse
from app.crud import user as crud_user
from app.crud import role as crud_role
from app.api.deps import (
    get_current_user,
    get_current_superuser,
    check_permission,
    get_current_user_tenant
)
from app.models.user import User
import math

router = APIRouter()


@router.post("", response_model=UserReadWithRoles, status_code=status.HTTP_201_CREATED)
def create_user(
        user_data: UserCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permission("users", "create"))
):
    """
    Crée un nouvel utilisateur.

    **Permissions requises :** `users:create`

    **Multi-tenancy :**
    - Les admins ne peuvent créer que des utilisateurs dans leur propre tenant
    - Les superusers peuvent créer des utilisateurs dans n'importe quel tenant

    **Validations :**
    - Email unique
    - Username unique
    - Mot de passe fort (8+ chars, maj, min, chiffre, spécial)
    - Rôles doivent exister

    **Example :**
    ```json
    POST /api/v1/users
    {
        "email": "new.user@nextstep.tn",
        "username": "newuser",
        "password": "SecurePass123!",
        "first_name": "New",
        "last_name": "User",
        "tenant_id": "nextstep",
        "role_ids": [2, 3]
    }
    ```
    """
    # Vérification multi-tenancy
    if not current_user.is_superuser:
        if user_data.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez créer des utilisateurs que dans votre propre tenant"
            )

    # Créer l'utilisateur
    try:
        new_user = crud_user.create_user(db, user_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return new_user


@router.get("", response_model=UserList)
def list_users(
        skip: int = Query(0, ge=0, description="Nombre d'éléments à sauter"),
        limit: int = Query(100, ge=1, le=1000, description="Nombre d'éléments à retourner"),
        search: Optional[str] = Query(None, description="Rechercher dans email, username, nom"),
        is_active: Optional[bool] = Query(None, description="Filtrer par statut actif"),
        is_superuser: Optional[bool] = Query(None, description="Filtrer par superuser"),
        tenant_id: Optional[str] = Query(None, description="Filtrer par tenant (superuser uniquement)"),
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permission("users", "read"))
):
    """
    Liste les utilisateurs avec pagination et filtres.

    **Permissions requises :** `users:read`

    **Multi-tenancy :**
    - Les admins voient uniquement les utilisateurs de leur tenant
    - Les superusers peuvent voir tous les tenants (avec filtre optionnel)

    **Pagination :**
    - `skip` : Décalage (par défaut 0)
    - `limit` : Nombre max d'éléments (par défaut 100, max 1000)

    **Filtres :**
    - `search` : Recherche dans email, username, first_name, last_name
    - `is_active` : true/false
    - `is_superuser` : true/false
    - `tenant_id` : Filtrer par tenant (superuser uniquement)

    **Example :**
    ```
    GET /api/v1/users?skip=0&limit=10&search=ahmed&is_active=true
    ```

    **Response :**
    ```json
    {
        "items": [...],
        "total": 50,
        "page": 1,
        "page_size": 10,
        "pages": 5
    }
    ```
    """
    # Multi-tenancy : forcer le tenant pour les non-superusers
    filter_tenant_id = tenant_id
    if not current_user.is_superuser:
        filter_tenant_id = current_user.tenant_id

    # Récupérer les utilisateurs
    users = crud_user.get_users(
        db,
        skip=skip,
        limit=limit,
        tenant_id=filter_tenant_id,
        is_active=is_active,
        is_superuser=is_superuser,
        search=search
    )

    # Compter le total
    total = crud_user.get_users_count(
        db,
        tenant_id=filter_tenant_id,
        is_active=is_active,
        is_superuser=is_superuser,
        search=search
    )

    # Calculer la pagination
    page = (skip // limit) + 1
    pages = math.ceil(total / limit) if limit > 0 else 0

    return UserList(
        items=[UserRead.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=limit,
        pages=pages
    )


@router.get("/{user_id}", response_model=UserReadWithRoles)
def get_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permission("users", "read"))
):
    """
    Récupère un utilisateur par son ID.

    **Permissions requises :** `users:read`

    **Multi-tenancy :**
    - Les admins ne peuvent voir que les utilisateurs de leur tenant
    - Les superusers peuvent voir tous les utilisateurs

    **Example :**
    ```
    GET /api/v1/users/1
    ```
    """
    user = crud_user.get_user(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    # Vérification multi-tenancy
    if not current_user.is_superuser:
        if user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à cet utilisateur"
            )

    return user


@router.put("/{user_id}", response_model=UserReadWithRoles)
def update_user(
        user_id: int,
        user_update: UserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permission("users", "update"))
):
    """
    Met à jour un utilisateur.

    **Permissions requises :** `users:update`

    **Multi-tenancy :**
    - Les admins ne peuvent modifier que les utilisateurs de leur tenant
    - Les superusers peuvent modifier tous les utilisateurs
    - Un utilisateur peut toujours se modifier lui-même

    **Champs modifiables :**
    - email, username, first_name, last_name
    - password (hashé automatiquement)
    - is_active
    - role_ids (nécessite permission users:update)

    **Example :**
    ```json
    PUT /api/v1/users/1
    {
        "first_name": "Ahmed Habib",
        "is_active": true
    }
    ```
    """
    user = crud_user.get_user(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    # Vérification multi-tenancy
    # Un utilisateur peut se modifier lui-même
    # Sinon, vérification du tenant
    if user_id != current_user.id and not current_user.is_superuser:
        if user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à cet utilisateur"
            )

    # Mettre à jour
    try:
        updated_user = crud_user.update_user(db, user_id, user_update)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return updated_user


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permission("users", "delete"))
):
    """
    Supprime un utilisateur.

    **Permissions requises :** `users:delete`

    **Multi-tenancy :**
    - Les admins ne peuvent supprimer que les utilisateurs de leur tenant
    - Les superusers peuvent supprimer tous les utilisateurs

    **Protections :**
    - Impossible de se supprimer soi-même

    **Example :**
    ```
    DELETE /api/v1/users/5
    ```
    """
    # Impossible de se supprimer soi-même
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer votre propre compte"
        )

    user = crud_user.get_user(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    # Vérification multi-tenancy
    if not current_user.is_superuser:
        if user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à cet utilisateur"
            )

    # Supprimer
    crud_user.delete_user(db, user_id)

    return MessageResponse(
        message=f"Utilisateur {user.email} supprimé avec succès",
        success=True
    )


@router.post("/{user_id}/roles/{role_id}", response_model=UserReadWithRoles)
def add_role_to_user(
        user_id: int,
        role_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permission("users", "update"))
):
    """
    Ajoute un rôle à un utilisateur.

    **Permissions requises :** `users:update`

    **Multi-tenancy :**
    - Les admins ne peuvent modifier que les utilisateurs de leur tenant
    - Les superusers peuvent modifier tous les utilisateurs

    **Example :**
    ```
    POST /api/v1/users/1/roles/2
    ```
    """
    user = crud_user.get_user(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    # Vérification multi-tenancy
    if not current_user.is_superuser:
        if user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à cet utilisateur"
            )

    # Vérifier que le rôle existe
    role = crud_role.get_role(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rôle non trouvé"
        )

    # Ajouter le rôle
    updated_user = crud_user.add_role_to_user(db, user_id, role_id)

    return updated_user


@router.delete("/{user_id}/roles/{role_id}", response_model=UserReadWithRoles)
def remove_role_from_user(
        user_id: int,
        role_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permission("users", "update"))
):
    """
    Retire un rôle d'un utilisateur.

    **Permissions requises :** `users:update`

    **Multi-tenancy :**
    - Les admins ne peuvent modifier que les utilisateurs de leur tenant
    - Les superusers peuvent modifier tous les utilisateurs

    **Example :**
    ```
    DELETE /api/v1/users/1/roles/2
    ```
    """
    user = crud_user.get_user(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    # Vérification multi-tenancy
    if not current_user.is_superuser:
        if user.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à cet utilisateur"
            )

    # Retirer le rôle
    updated_user = crud_user.remove_role_from_user(db, user_id, role_id)

    return updated_user


@router.get("/tenant/{tenant_id}/count")
def count_users_by_tenant(
        tenant_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(check_permission("users", "read"))
):
    """
    Compte le nombre d'utilisateurs dans un tenant.

    **Permissions requises :** `users:read`

    **Multi-tenancy :**
    - Les admins peuvent seulement compter dans leur propre tenant
    - Les superusers peuvent compter dans n'importe quel tenant

    **Example :**
    ```
    GET /api/v1/users/tenant/nextstep/count
    ```

    **Response :**
    ```json
    {
        "tenant_id": "nextstep",
        "total_users": 25,
        "active_users": 23,
        "inactive_users": 2
    }
    ```
    """
    # Vérification multi-tenancy
    if not current_user.is_superuser:
        if tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à ce tenant"
            )

    # Compter
    total = crud_user.get_users_count(db, tenant_id=tenant_id)
    active = crud_user.get_users_count(db, tenant_id=tenant_id, is_active=True)
    inactive = crud_user.get_users_count(db, tenant_id=tenant_id, is_active=False)

    return {
        "tenant_id": tenant_id,
        "total_users": total,
        "active_users": active,
        "inactive_users": inactive
    }