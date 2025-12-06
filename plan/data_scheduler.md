# data_scheduler

**Type**: Service gRPC
**Port**: 50051
**Langage**: Go
**Objectif**: Service central pour toutes les opérations de base de données

## Responsabilités
- Gérer toutes les lectures/écritures MongoDB
- Gérer le cache Redis (lecture/écriture/invalidation)
- Validation et transformation des données
- Source unique de vérité pour la persistance des données

## Méthodes gRPC

### Opérations d'écriture
- `WriteSeasons(SeasonsData) → WriteResponse`
- `WriteRounds(RoundsData) → WriteResponse`
- `WriteResults(ResultsData) → WriteResponse`
- `WriteStandings(StandingsData) → WriteResponse`

### Opérations de lecture
- `GetSeasons(SeasonsFilter) → SeasonsResponse`
- `GetRounds(RoundsFilter) → RoundsResponse`
- `GetResults(ResultsFilter) → ResultsResponse`
- `GetStandings(StandingsFilter) → StandingsResponse`

**Format de réponse**:
```json
{
  "metadata": {
    "date": 1732834567,
    "cached": true
  },
  "data": { /* resource-specific data */ }
}
```

## Clients
- **content_api**: Appelle les méthodes de lecture pour servir les requêtes HTTP
- **scheduler_api**: Appelle les méthodes d'écriture après récupération des APIs externes

## Stockage de données
- **MongoDB**: Stockage principal (collections seasons, rounds, results, standings)
- **Redis**: Couche de cache (TTL: 30s - 1h selon le type de données)

## Stratégie de cache
- Vérifier Redis lors de la lecture et retourner si en cache
- Requêter MongoDB en cas de cache manquant et mettre en cache le résultat puis retourner
- Invalider le cache lors des opérations d'écriture:
  - `WriteSeasons`: invalide `seasons:all` et `seasons:{year}` pour chaque saison écrite
  - `WriteRounds`: invalide les clés de cache correspondantes
