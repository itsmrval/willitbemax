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

### GET /v1/seasons
Retourne toutes les saisons

### GET /v1/seasons/:year/rounds
Retourne tous les rounds pour une saison avec détails 

**Réponse**:
```json
{
    "metadata": {
        "date": 1732834567,
        "cached": false
    },
    "result": {
        "season": 2025,
        "rounds": [
            {
                "round_id": 0,
                "name": "Formula 1 Australian Grand Prix 2025",
                "season": 2025,
                "first_date": 1710403200,
                "end_date": 1710576000,
                "circuit": {
                    "name": "Albert Park Circuit",
                    "lat": "-37.8497",
                    "long": "144.968",
                    "locality": "Melbourne",
                    "country": "Australia",
                    "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
                    "laps": 58
                },
                "sessions": [
                    {
                        "type": "practice_1",
                        "date": 1710403200,
                        "total_laps": 0,
                        "current_laps": 1,
                        "results": [
                            {
                                "position": 1,
                                "driver_number": 4,
                                "driver_name": "Lando Norris",
                                "driver_code": "NOR",
                                "team": "McLaren",
                                "time": "1:15.123",
                                "laps": 25
                            }
                        ]
                    },
                    {
                        "type": "race",
                        "date": 1710576000,
                        "total_laps": 58,
                        "current_laps": 1,
                        "results": [
                            {
                                "position": 1,
                                "driver_number": 4,
                                "driver_name": "Lando Norris",
                                "driver_code": "NOR",
                                "team": "McLaren",
                                "time": "1:42:04.304",
                                "laps": 57
                            },
                            {
                                "position": 2,
                                "driver_number": 81,
                                "driver_name": "Oscar Piastri",
                                "driver_code": "PIA",
                                "team": "McLaren",
                                "time": "1:42:07.555",
                                "laps": 57
                            }
                        ]
                    }
                ]
            }
        ]
    }
}
```

**Notes**:
- `circuit.image_base64`: Image du circuit encodée en base64
- `time`: Temps exact du tour

### GET /v1/seasons/:year/rounds/:round_id
Retourne les détails d'un round spécifique avec toutes les sessions et résultats

**Réponse**:
```json
{
    "metadata": {
        "date": 1732834567,
        "cached": false
    },
    "result": {
        "season": 2025,
        "rounds": [
            {
                "round_id": 0,
                "name": "Formula 1 Australian Grand Prix 2025",
                "season": 2025,
                "first_date": 1710403200,
                "end_date": 1710576000,
                "circuit": {
                    "name": "Albert Park Circuit",
                    "lat": "-37.8497",
                    "long": "144.968",
                    "locality": "Melbourne",
                    "country": "Australia",
                    "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
                    "laps": 58
                },
                "sessions": [
                    {
                        "type": "practice_1",
                        "date": 1710403200,
                        "total_laps": 0,
                        "current_laps": 1,
                        "results": [...]
                    },
                    {
                        "type": "qualifying",
                        "date": 1710489600,
                        "total_laps": 0,
                        "current_laps": 1,
                        "results": [
                            {
                                "position": 1,
                                "driver_number": 4,
                                "driver_name": "Lando Norris",
                                "driver_code": "NOR",
                                "team": "McLaren",
                                "time": "1:15.225",
                                "laps": 0
                            }
                        ]
                    },
                    {
                        "type": "race",
                        "date": 1710576000,
                        "total_laps": 58,
                        "current_laps": 1,
                        "results": [
                            {
                                "position": 1,
                                "driver_number": 4,
                                "driver_name": "Lando Norris",
                                "driver_code": "NOR",
                                "team": "McLaren",
                                "time": "1:42:04.304",
                                "laps": 57
                            },
                            {
                                "position": 2,
                                "driver_number": 81,
                                "driver_name": "Oscar Piastri",
                                "driver_code": "PIA",
                                "team": "McLaren",
                                "time": "1:42:07.555",
                                "laps": 57
                            }
                        ]
                    }
                ]
            }
        ]
    }
}
```

**Types de sessions**:
- `practice_1`, `practice_2`, `practice_3`: Essais libres
- `qualifying`: Qualifications
- `sprint_qualifying`: Qualifications sprint
- `sprint`: Course sprint
- `race`: Course principale

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
                        "driver_standings": [
                            {
                                "position": 1,
                                "driver_number": 4,
                                "driver_name": "Lando Norris",
                                "driver_code": "NOR",
                                "team": "McLaren",
                                "points": 78,
                                "wins": 2
                            }
                        ],
                        "constructor_standings": [
                            {
                                "position": 1,
                                "team": "McLaren",
                                "points": 150,
                                "wins": 3
                            }
                        ],
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
                        "driver_standings": [
                            {
                                "position": 1,
                                "driver_number": 1,
                                "driver_name": "Max Verstappen",
                                "driver_code": "VER",
                                "team": "Red Bull Racing",
                                "points": 437,
                                "wins": 9
                            }
                        ],
                        "constructor_standings": [
                            {
                                "position": 1,
                                "team": "McLaren",
                                "points": 666,
                                "wins": 6
                            }
                        ],
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
