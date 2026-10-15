"""
Configuration d'Apache Superset pour Lumina Énergie.
"""

# Clé secrète (obligatoire). En production : une longue valeur aléatoire gardée secrète.
SECRET_KEY = "cle-secrete-de-demo-lumina-superset-a-changer-en-production"

# Base interne de Superset (utilisateurs, graphiques...). Les DONNÉES, elles,
# restent dans l'entrepôt PostgreSQL.
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"

# Interface en français
BABEL_DEFAULT_LOCALE = "fr"
LANGUAGES = {
    "fr": {"flag": "fr", "name": "Français"},
    "en": {"flag": "us", "name": "English"},
}

# Permet de créer des rôles et des utilisateurs par l'API (utilisé par provisionner.py)
FAB_ADD_SECURITY_API = True

# Fonctionnalités utiles
FEATURE_FLAGS = {
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
}

# Site de démonstration en local (http) : on désactive les protections HTTPS
TALISMAN_ENABLED = False
WTF_CSRF_ENABLED = True
SESSION_COOKIE_SECURE = False

# Format des nombres : espace pour les milliers, virgule pour les décimales
D3_FORMAT = {"decimal": ",", "thousands": " ", "grouping": [3], "currency": ["", " FCFA"]}
