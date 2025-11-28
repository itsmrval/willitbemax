# fetcher_service

**Type**: Service de récupération de données
**Langage**: Python
**Port**: 8082 (HTTP) ou 50053 (gRPC)
**Objectif**: Récupérer et transformer les données F1 depuis multiples sources

## Responsabilités
- Scraper le site officiel F1 (formula1.com)
- Récupérer les données depuis les APIs
- Transformer les données vers le format interne
- Appeler data_scheduler via gRPC pour persister les données
- Gérer les erreurs

## Sources de données

### 1. Site officiel F1 (Scraping)
- **URL**: https://www.formula1.com
- **Données**: ?

### 2. API LiveTiming Formula 1
- **Type**: API temps réel
- **Données**: ?

### 3. API Ergast
- **URL**: http://ergast.com/mrd/
- **Données**: ?
- **Attention**: Limites API ratelimit

## Endpoints HTTP/gRPC

### POST /fetch/seasons
Récupérer et synchroniser les données de saisons

**Réponse**:
```json
{
    "success": true,
    "source": "ergast",
    "fetched_count": 2,
    "synced": true,
    "timestamp": 1732834567
}
```

### POST /fetch/rounds?season=2025
Récupérer les rounds pour une saison

**Réponse**:
```json
{
    "success": true,
    "source": "ergast",
    "fetched_count": 24,
    "synced": true,
    "timestamp": 1732834567
}
```

### POST /fetch/livetiming?session=race
Récupérer le timing en direct d'une session

**Réponse**:
```json
{
    "success": true,
    "source": "f1-livetiming",
    "fetched_count": 20,
    "synced": true,
    "live": true,
    "timestamp": 1732834567
}
```

### POST /fetch/standings?season=2025
Récupérer les classements

**Réponse**:
```json
{
    "success": true,
    "source": "ergast",
    "fetched_count": 20,
    "synced": true,
    "timestamp": 1732834567
}
```

### GET /status
Obtenir le statut du fetcher

**Réponse**:
```json
{
    "status": "ready",
    "sources": {
        "ergast": "reachable",
        "f1_website": "reachable",
        "livetiming": "connected"
    },
    "last_fetch": {
        "seasons": 1732830000,
        "rounds": 1732834567,
        "livetiming": 1732834590
    },
    "data_scheduler_connected": true
}
```

## Flux de récupération

1. Recevoir déclenchement depuis scheduler_api
2. Déterminer la source appropriée
3. Récupérer les données brutes
4. Parser et valider les données
5. Transformer au format interne (modèles Go)
6. Appeler data_scheduler gRPC pour persister
7. Retourner résultat de succès/échec


## Configuration

- API keys si nécessaire
- Timeouts
- Adresse gRPC du data_scheduler
