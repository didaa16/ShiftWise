"""
Script d'initialisation de ShiftWise

Ce script doit être exécuté une seule fois après la création de la base de données.

Il crée :
1. Les rôles système (super_admin, admin, user, viewer)
2. Le premier superuser (administrateur système)

Usage:
    python init_db.py
"""

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, init_db
from app.core.security import get_password_hash, validate_password_strength
from app.models.user import User
from app.models.role import Role, ROLE_PERMISSIONS
from app.crud import role as crud_role
from app.crud import user as crud_user


def create_system_roles(db: Session):
    """Crée les rôles système"""
    print("📋 Création des rôles système...")

    roles_created = crud_role.create_system_roles(db)

    for role in roles_created:
        print(f"   ✅ Rôle '{role.name}' créé/vérifié")

    print(f"✅ {len(roles_created)} rôles système initialisés\n")
    return roles_created


def create_superuser(db: Session):
    """Crée le premier superuser"""
    print("👤 Création du superuser...")

    # Vérifier si un superuser existe déjà
    existing_superuser = db.query(User).filter(User.is_superuser == True).first()

    if existing_superuser:
        print(f"   ⚠️  Un superuser existe déjà : {existing_superuser.email}")
        return existing_superuser

    # Demander les informations du superuser
    print("\n📝 Veuillez fournir les informations du superuser :\n")

    email = input("   Email : ").strip()
    if not email:
        email = "admin@shiftwise.local"
        print(f"   → Email par défaut : {email}")

    username = input("   Username : ").strip()
    if not username:
        username = "admin"
        print(f"   → Username par défaut : {username}")

    first_name = input("   Prénom : ").strip() or "Super"
    last_name = input("   Nom : ").strip() or "Admin"

    # Demander et valider le mot de passe
    password = None
    while password is None:
        pwd_input = input("   Mot de passe : ").strip()

        if not pwd_input:
            pwd_input = "Admin123!"
            print(f"   → Mot de passe par défaut : {pwd_input}")
            print("   ⚠️  CHANGEZ CE MOT DE PASSE APRÈS LA PREMIÈRE CONNEXION!")

        # Valider la force du mot de passe
        is_valid, error_message = validate_password_strength(pwd_input)
        if is_valid:
            password = pwd_input
        else:
            print(f"   ❌ {error_message}")
            print("   💡 Exigences : au moins 8 caractères, 1 majuscule, 1 minuscule, 1 chiffre")
            if pwd_input == "":  # Si on utilise le défaut et qu'il échoue
                password = "Admin123!"  # Forcer le défaut valide
                break

    tenant_id = input("   Tenant ID : ").strip()
    if not tenant_id:
        tenant_id = "system"
        print(f"   → Tenant par défaut : {tenant_id}")

    # Récupérer le rôle super_admin
    super_admin_role = crud_role.get_role_by_name(db, "super_admin")

    if not super_admin_role:
        print("   ❌ Erreur : Le rôle super_admin n'existe pas. Créez d'abord les rôles système.")
        return None

    try:
        # Créer le superuser
        superuser = User(
            email=email.lower(),
            username=username.lower(),
            first_name=first_name,
            last_name=last_name,
            hashed_password=get_password_hash(password),
            tenant_id=tenant_id.lower(),
            is_active=True,
            is_verified=True,
            is_superuser=True
        )

        # Assigner le rôle super_admin
        superuser.roles = [super_admin_role]

        db.add(superuser)
        db.commit()
        db.refresh(superuser)

        print(f"\n✅ Superuser créé avec succès !")
        print(f"   Email    : {superuser.email}")
        print(f"   Username : {superuser.username}")
        print(f"   Tenant   : {superuser.tenant_id}")
        print(f"   Rôle     : super_admin\n")

        return superuser

    except Exception as e:
        print(f"\n❌ Erreur lors de la création du superuser : {e}")
        db.rollback()
        return None


def main():
    """Fonction principale d'initialisation"""
    print("=" * 60)
    print("🚀 INITIALISATION DE SHIFTWISE")
    print("=" * 60)
    print()

    # Initialiser la base de données
    print("📊 Initialisation de la base de données...")
    try:
        init_db()
        print("✅ Tables créées\n")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base : {e}")
        return

    # Créer une session
    db = SessionLocal()

    try:
        # Créer les rôles système
        create_system_roles(db)

        # Créer le superuser
        superuser = create_superuser(db)

        if superuser:
            print("=" * 60)
            print("✅ INITIALISATION TERMINÉE AVEC SUCCÈS !")
            print("=" * 60)
            print()
            print("Prochaines étapes :")
            print("1. Démarrez l'application : uvicorn app.main:app --reload")
            print("2. Accédez à la documentation : http://localhost:8000/docs")
            print("3. Connectez-vous avec le superuser créé")
            print("4. CHANGEZ le mot de passe par défaut !")
            print()
        else:
            print("\n⚠️  Initialisation incomplète - le superuser n'a pas été créé")

    except Exception as e:
        print(f"\n❌ Erreur lors de l'initialisation : {e}")
        import traceback
        traceback.print_exc()
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    main()