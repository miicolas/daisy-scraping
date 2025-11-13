# Daisy - Workshop Scraper & API

Système de scraping et d'API pour collecter et gérer les ateliers créatifs depuis Wecandoo.

## 🚀 Démarrage rapide

```bash
# 1. Cloner et installer
git clone <repository-url>
cd daisy-scraping
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install

# 2. Démarrer les services Docker
docker-compose up -d

# 3. Démarrer l'API (Terminal 1)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 4. Démarrer le worker Celery (Terminal 2)
celery -A api.celery_config worker --loglevel=info

# 5. Lancer un crawl
curl -X POST http://localhost:8000/api/v1/start-crawl/wecandoo
```

## Architecture

Le projet est composé de plusieurs services :

- **API FastAPI** : API REST pour gérer les ateliers (port 8000)
- **Scrapy Spider** : Spider avec support Playwright pour scraper les ateliers
- **Celery Worker** : Gestion des tâches asynchrones de scraping
- **PostgreSQL** : Base de données pour stocker les ateliers (port 5666)
- **Redis** : Message broker pour Celery (port 6381)
- **n8n** : Plateforme d'automatisation (port 5678, optionnel)

## Structure du projet

```
daisy/
├── api/
│   ├── models/
│   │   └── atelier.py           # Modèles SQLModel
│   │   └── crawl_log.py         # Modèles Crawl
│   ├── main.py                  # Application FastAPI
│   ├── tasks.py                 # Tâches Celery
│   └── celery_config.py         # Configuration Celery
├── scrapping/
│   ├── spiders/
│   │   └── wecandoo.py          # Spider Wecandoo
│   ├── items.py                 # Définition des items
│   ├── pipelines.py             # Pipelines de traitement
│   └── settings.py              # Configuration Scrapy
├── docker-compose.yml           # Configuration Docker
├── requirements.txt             # Dépendances Python
└── scrapy.cfg                   # Configuration Scrapy
```

## Prérequis

- Python 3.10+
- Docker & Docker Compose
- pip

## Installation

### 1. Cloner le projet

```bash
git clone <repository-url>
cd daisy
```

### 2. Installer les dépendances Python

```bash
python -m venv .venv
source .venv/bin/activate  # Sur Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Installer les navigateurs Playwright

```bash
playwright install
```

### 4. Démarrer les services Docker

```bash
docker-compose up -d
```

Cela va démarrer :
- PostgreSQL sur le port `5666`
- Redis sur le port `6381`
- n8n sur le port `5678`

## Utilisation

### Démarrer les services (dans l'ordre)

#### 1. Services Docker (PostgreSQL, Redis, n8n)

```bash
docker-compose up -d
```

Vérifier que les services tournent :
```bash
docker ps
```

#### 2. API FastAPI (Terminal 1)

```bash
source .venv/bin/activate  # Activer l'environnement virtuel
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

L'API sera accessible sur http://localhost:8000

Documentation : http://localhost:8000/docs

#### 3. Worker Celery (Terminal 2)

**OBLIGATOIRE pour les crawls asynchrones**

```bash
source .venv/bin/activate  # Activer l'environnement virtuel
celery -A api.celery_config worker --loglevel=info
```

Vous devriez voir :
```
[tasks]
  . api.tasks.run_scrapy_spider

celery@... ready.
```

### Lancer le scraping

#### Option 1 : Via Scrapy directement

```bash
cd scrapping
scrapy crawl wecandoo
```

Options disponibles :
- `max_pages` : Nombre maximum de pages à scraper (défaut: 10)
- `scroll_attempts` : Nombre de scrolls par page (défaut: 5)

```bash
scrapy crawl wecandoo -a max_pages=20 -a scroll_attempts=10
```

#### Option 2 : Via l'API (asynchrone avec Celery)

```bash
curl -X POST http://localhost:8000/api/v1/start-crawl/wecandoo
```

## API Endpoints

### GET /api/v1/ateliers

Récupérer la liste des ateliers

**Query Parameters:**
- `offset` (int, default=0) : Décalage pour la pagination
- `limit` (int, default=100, max=100) : Nombre d'ateliers à retourner
- `category` (string, optionnel) : Filtrer par catégorie

**Exemple:**
```bash
curl "http://localhost:8000/api/v1/ateliers?limit=10&offset=0"
curl "http://localhost:8000/api/v1/ateliers?category=Poterie"
```

### GET /api/v1/ateliers/{atelier_id}

Récupérer un atelier spécifique

**Exemple:**
```bash
curl http://localhost:8000/api/v1/ateliers/1
```

### GET /api/v1/ateliers/urls

Récupérer la liste de toutes les URLs des ateliers (utile pour la déduplication)

**Exemple:**
```bash
curl http://localhost:8000/api/v1/ateliers/urls
```

**Réponse:**
```json
[
  "https://wecandoo.fr/atelier/...",
  "https://wecandoo.fr/atelier/...",
  ...
]
```

### POST /api/v1/ateliers/batch

Créer plusieurs ateliers en batch

**Body:**
```json
[
  {
    "title": "Atelier Poterie",
    "url": "https://wecandoo.fr/atelier/...",
    "category": "Poterie",
    "price": 75.0,
    "duration": "3h",
    "location": "Paris 11e"
  }
]
```

### POST /api/v1/start-crawl/{spider_name}

Démarrer un crawl asynchrone via Celery

**Paramètres:**
- `spider_name` : Nom du spider (actuellement: `wecandoo`)

**Exemple:**
```bash
curl -X POST http://localhost:8000/api/v1/start-crawl/wecandoo
```

**Réponse:**
```json
{
  "task_id": "abc123...",
  "status": "started",
  "message": "crawl wecandoo démarré avec succès"
}
```

### GET /api/v1/start-crawl/status/{task_id}

Vérifier le statut d'un crawl en cours

**Exemple:**
```bash
# Récupérer le task_id de la réponse du POST /start-crawl
curl http://localhost:8000/api/v1/start-crawl/status/abc123...
```

**Réponse:**
```json
{
  "task_id": "abc123...",
  "celery_state": "SUCCESS",
  "status": "SUCCESS",
  "items_scraped": 680,
  "error_message": null,
  "created_at": "2025-11-13T19:21:10.727735",
  "completed_at": "2025-11-13T19:23:45.123456"
}
```

**Statuts possibles:**
- `PENDING` : Tâche en attente
- `STARTED` : Tâche démarrée
- `PROGRESS` : En cours d'exécution
- `SUCCESS` : Terminé avec succès
- `FAILED` : Échec

### DELETE /api/v1/ateliers-all/

Supprimer tous les ateliers de la base de données

**Exemple:**
```bash
curl -X DELETE http://localhost:8000/api/v1/ateliers-all/
```

## Configuration

### Base de données

Par défaut, l'API se connecte à PostgreSQL :
- Host: `localhost`
- Port: `5666`
- Database: `db`
- User: `postgres`
- Password: `postgres`

Pour modifier la configuration, éditez [api/main.py:22](api/main.py#L22)

### Celery & Redis

Configuration dans [api/celery_config.py](api/celery_config.py) :
- Broker: `redis://localhost:6381/0`
- Backend: `redis://localhost:6381/0`

### Scrapy

Configuration dans [scrapping/settings.py](scrapping/settings.py) :
- Respect du `robots.txt` : Activé
- Délai entre requêtes : 3 secondes (avec randomisation)
- AutoThrottle : Activé (ajuste automatiquement entre 3 et 10 secondes)
- Timeout : 30 minutes
- Concurrence par domaine : 1
- Resources bloquées : images, stylesheets, fonts, media

## Modèle de données

### Atelier

```python
{
  "id": int,
  "title": str,              # Titre de l'atelier
  "url": str,                # URL de l'atelier
  "category": str | None,    # Catégorie (ex: "Poterie", "Couture")
  "price": float | None,     # Prix en euros
  "duration": str | None,    # Durée (ex: "3h", "2h30")
  "location": str | None     # Localisation (ex: "Paris 11e")
}
```

## Pipeline de traitement

Le scraping suit ce flux :

1. **Spider Wecandoo** → Extrait les données brutes
2. **AtelierPipeline** → Nettoie et normalise les données
3. **DatabasePipeline** → Vérifie les doublons et envoie par batch à l'API
4. **API** → Stocke dans PostgreSQL

## Documentation interactive

Une fois l'API démarrée, accédez à la documentation Swagger :
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Accès aux services

- **API** : http://localhost:8000
- **PostgreSQL** : `localhost:5666`
- **Redis** : `localhost:6381`
- **n8n** : http://localhost:5678

## Connexion à PostgreSQL

```bash
psql -h localhost -p 5666 -U postgres -d db
```

Password: `postgres`

## 🔧 Troubleshooting

### Le crawl reste en "PENDING" indéfiniment

**Cause:** Le worker Celery n'est pas démarré.

**Solution:**
```bash
# Vérifier si le worker tourne
ps aux | grep "celery.*worker" | grep -v grep

# S'il ne tourne pas, le démarrer
source .venv/bin/activate
celery -A api.celery_config worker --loglevel=info
```

### 429 Rate Limit / Timeout sur le scraping

**Cause:** Trop de requêtes trop rapidement vers le site cible.

**Solution:** Les délais sont configurés dans [scrapping/settings.py](scrapping/settings.py):
- `DOWNLOAD_DELAY = 3`
- `RANDOMIZE_DOWNLOAD_DELAY = True`
- `AUTOTHROTTLE_ENABLED = True`

### Duplicate Nodename Warning (Celery)

**Cause:** Plusieurs workers Celery tournent avec le même nom.

**Solution:**
```bash
# Tuer tous les workers
pkill -f "celery.*worker"

# Relancer un seul worker
celery -A api.celery_config worker --loglevel=info
```

## Notes

- Le worker Celery doit être **toujours actif** pour traiter les crawls asynchrones
- Les crawls peuvent prendre 1-2 minutes selon le nombre de pages
- Le délai entre requêtes évite le rate limiting (429 errors)
- Les données sont automatiquement dédupliquées par URL
