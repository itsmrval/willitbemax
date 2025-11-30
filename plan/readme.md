# Vue d'ensemble de l'architecture

## Services

### Services
- **content_api**: API REST HTTP publique pour l'utilisateur final
- **data_scheduler**: Service gRPC gérant toutes les opérations MongoDB/Redis
- **scheduler_api**: Service de planification, déclenche les synchronisations
- **fetcher_service**: Service de récupération de données (scraping F1, APIs externes)
- **auth_api**: Authentification et comptes utilisateurs
- **website_front**: Application frontend

## Stack technologique
- **Langage**: Go (content_api, data_scheduler, scheduler_api) + Python (fetcher_service)
- **Base de données**: MongoDB (stockage principal)
- **Cache**: Redis (couche de cache)
- **Communication**: gRPC (interne), HTTP/REST (public)
- **Reverse Proxy**: Traefik (point d'entrée unique HTTP)
- **Scraping**: BeautifulSoup

## Flux de données
```
APIs / Site f1
    ↓ (scraping/HTTP)
fetcher_service
    ↓ gRPC
data_scheduler (Serveur gRPC)
    ↓
MongoDB + Redis
    ↑ gRPC
content_api (Serveur HTTP)
    ↓
Traefik (Port 80)
    ↓
Utilisateurs finaux

scheduler_api → déclenche → fetcher_service (via HTTP/gRPC)
```

## APIs

- **content_api**: http://localhost/content/v1/seasons
- **fetcher_service**: http://localhost/fetcher/v1/fetch/seasons

---

## Structure du projet

### Organisation des dossiers

```
willitbemax/
├── protobuf/                    # Définitions protobufs
│   ├── content.proto            # Messages pour les données
│   └── services.proto           # Définitions des services gRPC
│
├── content_api/                 # Service API content (Go) ✅
│   ├── cmd/
│   │   └── main.go
│   ├── internal/
│   │   ├── config/              # Configuration
│   │   ├── handlers/            # Handlers HTTP
│   │   ├── grpc/                # Client gRPC vers data_scheduler
│   │   ├── middleware/          # Middleware (logging, errors)
│   │   └── models/              # Modèles de données
│   ├── Dockerfile
│   └── go.mod
│
├── data_scheduler/               # Service de gestion DB (Go)
│   ├── cmd/
│   │   └── main.go
│   ├── internal/
│   │   ├── grpc/                # Serveur gRPC
│   │   ├── database/            # MongoDB client
│   │   ├── cache/               # Redis client
│   │   └── models/              # Modèles de données
│   └── go.mod
│
├── scheduler_api/                # Service planificateur (Go)
│   ├── cmd/
│   │   └── main.go
│   ├── internal/
│   │   ├── scheduler/           # Logique cron
│   │   ├── calendar/            # Détection weekend course
│   │   └── client/              # Client HTTP vers fetcher
│   └── go.mod
│
├── fetcher_service/             # Service de récupération (Python)
│   ├── src/
│   │   ├── main.py              # Point d'entrée FastAPI/Flask
│   │   ├── scrapers/
│   │   │   ├── f1_website.py    # Scraper site F1
│   │   │   ├── ergast.py        # Client API Ergast
│   │   │   └── livetiming.py    # Client LiveTiming F1
│   │   ├── grpc_client/         # Client gRPC vers data_scheduler
│   │   └── models/              # Modèles de données
```

### Communication entre services

**gRPC (via protobuf/)**
- **content_api** → **data_scheduler** (lecture/écriture)
- **fetcher_service** → **data_scheduler** (lecture/écriture)

**HTTP**
- **scheduler_api** → **fetcher_service** (trigger)
- Clients externes → **Traefik** → **content_api** (via /content/v1)
- Clients externes → **Traefik** → **fetcher_service** (via /fetcher/v1)