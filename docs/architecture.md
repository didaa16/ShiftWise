# Architecture ShiftWise

## Vue d'ensemble

ShiftWise est une plateforme de migration intelligente de machines virtuelles vers OpenShift Virtualization.

## Architecture Backend

### Stack Technique
- **Framework:** FastAPI
- **Base de données:** PostgreSQL
- **ORM:** SQLAlchemy
- **Authentification:** JWT (JSON Web Tokens)
- **Validation:** Pydantic

### Structure des modules
\\\
backend/
├── app/
│   ├── api/          # Routes API
│   ├── core/         # Configuration et sécurité
│   ├── crud/         # Opérations CRUD
│   ├── models/       # Modèles SQLAlchemy
│   └── schemas/      # Schémas Pydantic
\\\

## Architecture Frontend

(À définir)

## Base de données

### Tables principales
- **users**: Utilisateurs de la plateforme
- **roles**: Rôles RBAC
- **user_roles**: Association Many-to-Many

## Sécurité

- Authentification JWT avec refresh tokens
- RBAC (Role-Based Access Control)
- Multi-tenancy pour isolation des données
- Hashing des mots de passe avec bcrypt

## Prochaines étapes

1. Intégration avec hyperviseurs (vSphere, KVM, Hyper-V)
2. Module d'analyse IA
3. Orchestration des migrations
4. Dashboard de monitoring
