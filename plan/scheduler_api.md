# scheduler_api

**Type**: Service de planification
**Langage**: Go
**Port**: 8081 (HTTP)
**Objectif**: Planifier les opérations de synchronisation des données

## Responsabilités
- Planifier la mise à jour des données
- Déclencher fetcher_service
- Détecter les weekends de course pour ajuster les fréquences
- Gérer les planifications multiples (saisons, rounds, résultats, classements)
- Exposer une API pour les déclenchements manuels ou vérifications de statut
- Logger l'historique des synchronisations

## Endpoints API

### Planificateur interne
- S'exécute à intervalles configurables (weekend de course vs hors-saison)
- Déclenche automatiquement les opérations de synchronisation

### Endpoints HTTP

#### POST /trigger/seasons
Déclencher manuellement la synchronisation des saisons

**Réponse**:
```json
{
    "success": true,
    "message": "Season sync triggered",
    "fetcher_called": true,
    "timestamp": 1732834567
}
```

#### POST /trigger/rounds?season=2025
Déclencher la synchronisation des rounds pour une saison spécifique

**Réponse**:
```json
{
    "success": true,
    "message": "Rounds sync triggered for season 2025",
    "fetcher_called": true,
    "timestamp": 1732834567
}
```

#### POST /trigger/results?season=2025&round=0
Déclencher la synchronisation des résultats pour un round spécifique

**Réponse**:
```json
{
    "success": true,
    "message": "Results sync triggered for round 0",
    "fetcher_called": true,
    "timestamp": 1732834567
}
```

#### POST /trigger/standings?season=2025
Déclencher la synchronisation des classements

**Réponse**:
```json
{
    "success": true,
    "message": "Standings sync triggered",
    "fetcher_called": true,
    "timestamp": 1732834567
}
```

#### GET /status
Obtenir le statut du planificateur et les derniers temps de synchronisation

**Réponse**:
```json
{
    "status": "running",
    "is_race_weekend": true,
    "last_syncs": {
        "seasons": 1732830000,
        "rounds": 1732834567,
        "results": 1732834560,
        "standings": 1732834200
    },
    "next_syncs": {
        "seasons": 1732851600,
        "rounds": 1732834597,
        "results": 1732834590,
        "standings": 1732834500
    },
    "current_intervals": {
        "rounds": "30s",
        "results": "30s",
        "standings": "5m"
    }
}
```

#### GET /health
Endpoint de vérification de santé

**Réponse**:
```json
{
    "status": "healthy",
    "uptime_seconds": 86400,
    "fetcher_service_connected": true,
    "scheduler_running": true
}
```

## Planification des synchronisations

### Intervalles dynamiques
- **Saisons**: Toutes les 6 heures
- **Rounds**: Toutes les 30 secondes (weekend de course) / 30 minutes (hors-saison)
- **Résultats**: Toutes les 30 secondes (pendant les sessions en direct) / en pause sinon
- **Classements**: Toutes les 5 minutes (weekend de course) / 1 heure (hors-saison)

### Détection du weekend de course
- Vérifie le calendrier des courses pour déterminer si c'est un weekend de course
- Ajuste automatiquement la fréquence de synchronisation

## Flux
1. Le cron interne déclenche la synchronisation à l'intervalle planifié
2. Déterminer quelles données récupérer (basé sur la planification)
3. Appeler fetcher_service via HTTP (POST /fetch/...)
4. fetcher_service récupère et enregistre les données
5. Attendre la confirmation de fetcher_service
6. Mettre à jour le timestamp de la dernière synchronisation
7. Logger le succès/échec
8. Attendre

## Intégrations
- **fetcher_service**: Appelle les endpoints de récupération et lit le calendrier pour détecter les weekends de course

## Configuration
- Intervalles de synchronisation (configurables via variables d'environnement)
- Port HTTP du fetcher_service
- Calendrier des courses pour détection des weekends
