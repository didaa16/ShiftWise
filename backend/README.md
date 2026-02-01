# ShiftWise Backend

Backend FastAPI avec authentification JWT, RBAC et multi-tenancy.

## Stack Technique
- FastAPI
- PostgreSQL
- SQLAlchemy
- JWT

## Installation

### Prérequis
- Python 3.9+
- PostgreSQL 13+

### Setup
```bash
# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installer dépendances
pip install -r requirements.txt

# Configurer .env
cp .env.example .env
# Éditer .env avec vos valeurs

# Initialiser DB
python init_db.py

# Lancer
uvicorn app.main:app --reload
```

## API Documentation
http://localhost:8000/docs