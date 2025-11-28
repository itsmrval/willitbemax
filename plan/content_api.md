# content_api

**Type**: Service API REST HTTP
**Port**: 8080
**Langage**: Go
**Objectif**: API publique pour la consommation de données F1

## Responsabilités
- Servir les endpoints HTTP publics
- Appeler data_scheduler via gRPC pour récupérer les données
- Transformer les réponses gRPC en JSON
- Retourner un format de réponse cohérent avec métadonnées

## Technologie
- **Protocole**: HTTP/REST (public)
- **Interne**: Client gRPC (appelle data_scheduler)
- **Format de réponse**: JSON

## Endpoints

### GET /v1/seasons/:year/rounds
Retourne tous les rounds pour une saison

**Réponse**:
```json
{
    "metadata": {
        "date": "date unix",
        "cached": true/false
    },
    "result": {
            "season": 2025,
            "round_id": 0,
            "name": "Formula 1 Louis Vuitton Australian Grand Prix 2025",
            "first_date": "unix date",
            "end_date": "unix date"
            "circuit": {
                "name": "Albert Park Grand Prix Circuit",
                "lat": "-37.8497",
                "long": "144.968",
                "locality": "Melbourne",
                "country": "Australia"
            }
        }
        
    }
    
```

### GET /v1/seasons/:year/rounds/:round_id
Retourne les détails d'un round spécifique avec les sessions

**Réponse**:
```json
{
            metadata: {
                "date": "date unix" // date de mise à jour des données
                "cached": true/false // a la réponse de l'api
            },
            "result": {
                "season": 2025,
                "round_id": 0,
                "circuit": {
                    "name": "Albert Park Grand Prix Circuit",
                    "lat": "-37.8497",
                    "long": "144.968",
                    "locality": "Melbourne",
                    "country": "Australia"
                }
                "name": "Formula 1 Louis Vuitton Australian Grand Prix 2025",
                "first_date": "date",
                "end_date": "date",
                "sessions": [
                    {
                        "race": {
                            "type": "test", // ["test", "race", "sprint_race",
                                                "practice_1", "practice_2", "practice_3", 
                                                "qualyfing_1", "qualyfing_2, "qualyfing_3",
                                                "sprint_qualyfing_1", "sprint_qualyfing_2, "sprint_qualyfing_3"] // unique
                            "date": "unix date",
                            "result": {
                                "position": 1, // unique
                                "driver_number": 4,
                                "driver_name": "Lando Norris",
                                "team": "McLaren",
                                "laps": 57,
                                "time": "1:42:04.304" // can also be DNF / DNS so string
                                "points": 25
                            }
                        },
                    }
                ]
            }
        }

```

### GET /v1/seasons/:year/drivers
Retourne le classement des pilotes pour une saison

**Réponse**:
```json
{
            metadata: {
                "date": "date unix" // date de mise à jour des données
                "cached": true/false // a la réponse de l'api
            },
            result: {
                "season": 2025,
                "last_round": 3,
                "standings": [
                    {
                        "position": 1,
                        "number": 4,
                        "name": "Lando Norris",
                        "nationality": "British",
                        "team": "McLaren",
                        "points": 78,
                        "wins": 2,
                        "podiums": 3,
                        "pole_positions": 2,
                        "fastest_laps": 1,
                        "dnf_count": 0,
                        "races_completed": 3
                    }
                ]
            }
        }

```

### GET /v1/seasons
Retourne toutes les saisons

**Réponse**:
```json
{
            metadata: {
                "date": "date unix" // date de mise à jour des données
                "cached": true/false // a la réponse de l'api
            },
            result: {
                "seasons": [
                    {
                        "year": 2025,
                        "rounds": 24,
                        "start_date": 1710403200,
                        "end_date": 1733587200,
                        "status": "in_progress",
                        "current_round": 3,
                        "world_champion": null,
                        "constructors_champion": null,
                        "total_drivers": 20,
                        "total_teams": 10,
                    },
                    {
                        "year": 2024,
                        "rounds": 24,
                        "start_date": 1677715200,
                        "end_date": 1701648000,
                        "status": "completed",
                        "current_round": 24,
                        "world_champion": {
                            "driver_number": 1,
                            "driver_name": "Max Verstappen",
                            "driver_code": "VER",
                            "team": "Red Bull Racing",
                            "points": 437
                        },
                        "constructors_champion": {
                            "team": "McLaren",
                            "points": 666
                        },
                        "total_drivers": 22,
                        "total_teams": 10,
                    }
                ]
            }
        }
```

## Métadonnées de réponse
Tous les endpoints retournent des métadonnées cohérentes:
- `date`: Timestamp Unix de la dernière mise à jour des données
- `cached`: Booléen indiquant si la réponse a été servie depuis le cache
