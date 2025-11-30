# Protobuf Definitions

**Objectif**: Définir les messages et services gRPC pour la communication inter-services

## Structure des fichiers

```
protobuf/
├── content.proto       # Messages de données (Season, Round, Driver, etc.)
└── services.proto      # Définitions des services gRPC (DataSchedulerService)
```

---

## content.proto

### Messages principaux

#### Season
```protobuf
message DriverStanding {
  int32 position = 1;
  int32 driver_number = 2;
  string driver_name = 3;
  string driver_code = 4;      // ex: "VER", "NOR"
  string team = 5;
  int32 points = 6;
  int32 wins = 7;
}

message ConstructorStanding {
  int32 position = 1;
  string team = 2;
  int32 points = 3;
  int32 wins = 4;
}

message Season {
  int32 year = 1;
  int32 rounds = 2;
  int64 start_date = 3;        // Unix timestamp
  int64 end_date = 4;          // Unix timestamp
  string status = 5;           // "in_progress", "completed", "upcoming"
  int32 current_round = 6;
  repeated DriverStanding driver_standings = 7;
  repeated ConstructorStanding constructor_standings = 8;
  int32 total_drivers = 9;
  int32 total_teams = 10;
}
```

#### Round (Grand Prix)
```protobuf
message Round {
  int32 season = 1;
  int32 round_id = 2;
  string name = 3;             // ex: "Formula 1 Louis Vuitton Australian Grand Prix 2025"
  int64 first_date = 4;        // Unix timestamp (début du weekend)
  int64 end_date = 5;          // Unix timestamp (fin du weekend)
  Circuit circuit = 6;
  repeated Session sessions = 7;
}

message Circuit {
  string name = 1;             // ex: "Albert Park Grand Prix Circuit"
  string lat = 2;              // Latitude (string pour précision)
  string long = 3;             // Longitude (string pour précision)
  string locality = 4;         // ex: "Melbourne"
  string country = 5;          // ex: "Australia"
}
```

#### Session
```protobuf
message Session {
  string type = 1;             // "test", "race", "sprint_race", "practice_1",
                               // "practice_2", "practice_3", "qualifying_1",
                               // "qualifying_2", "qualifying_3", "sprint_qualifying_1",
                               // "sprint_qualifying_2", "sprint_qualifying_3"
  int64 date = 2;              // Unix timestamp
  optional int32 total_laps = 3;     // Nombre de tours prévus (null pour qualif/practice)
  optional int32 completed_laps = 4; // Nombre de tours complétés (< total si en cours par ex)
  repeated Result results = 5;       // Array de tous les résultats (P1, P2, P3, ...)
}

message Result {
  int32 position = 1;          // Position finale (1, 2, 3, ...)
  int32 driver_number = 2;     // Numéro du pilote
  string driver_name = 3;      // Nom complet du pilote
  string team = 4;             // Nom de l'équipe
  int32 laps = 5;              // Nombre de tours complétés
  string time = 6;             // "1:42:04.304", "+3.251" ou "DNF", "DNS", "DSQ"
  int32 points = 7;            // Points marqués (25, 18, 15, ...)
}
```


#### Metadata
```protobuf
message Metadata {
  int64 date = 1;              // Unix timestamp (dernière mise à jour)
  bool cached = 2;             // true si servi depuis Redis
}
```

### Messages de collections

```protobuf
message SeasonsData {
  repeated Season seasons = 1;
}

message RoundsData {
  repeated Round rounds = 1;
}

message ResultsData {
  int32 season = 1;
  int32 round_id = 2;
  string session_type = 3;
  repeated Result results = 4;
}
```

---

## services.proto

### DataSchedulerService

Service gRPC central pour toutes les opérations de base de données (MongoDB + Redis).

```protobuf
service DataSchedulerService {
  // ============ Opérations d'écriture ============

  // Écrire/mettre à jour les données de saisons
  rpc WriteSeasons(SeasonsData) returns (WriteResponse);

  // Écrire/mettre à jour les données de rounds
  rpc WriteRounds(RoundsData) returns (WriteResponse);

  // Écrire/mettre à jour les résultats d'une session
  rpc WriteResults(ResultsData) returns (WriteResponse);

  // Écrire/mettre à jour les classements pilotes
  rpc WriteStandings(StandingsData) returns (WriteResponse);

  // ============ Opérations de lecture ============

  // Récupérer les saisons (avec filtres optionnels)
  rpc GetSeasons(SeasonsFilter) returns (SeasonsResponse);

  // Récupérer les rounds d'une saison
  rpc GetRounds(RoundsFilter) returns (RoundsResponse);

  // Récupérer les résultats d'une session
  rpc GetResults(ResultsFilter) returns (ResultsResponse);

  // Récupérer les classements pilotes
  rpc GetStandings(StandingsFilter) returns (StandingsResponse);
}
```

### Messages de requête (Filters)

```protobuf
message SeasonsFilter {
  optional int32 year = 1;     // Si vide, retourne toutes les saisons
  optional string status = 2;  // Filtrer par status
}

message RoundsFilter {
  int32 season = 1;            // Obligatoire
  optional int32 round_id = 2; // Si fourni, retourne un round spécifique
}

message ResultsFilter {
  int32 season = 1;
  int32 round_id = 2;
  optional string session_type = 3; // Si vide, retourne toutes les sessions
}

message StandingsFilter {
  int32 season = 1;
  optional int32 after_round = 2;   // Classement après un round spécifique
}
```

### Messages de réponse

```protobuf
message WriteResponse {
  bool success = 1;
  string message = 2;          // Message d'erreur ou de succès
  int32 records_affected = 3;  // Nombre d'enregistrements modifiés
}

message SeasonsResponse {
  Metadata metadata = 1;
  SeasonsData data = 2;
}

message RoundsResponse {
  Metadata metadata = 1;
  RoundsData data = 2;
}

message ResultsResponse {
  Metadata metadata = 1;
  ResultsData data = 2;
}

message StandingsResponse {
  Metadata metadata = 1;
  StandingsData data = 2;
}
```

---

## Utilisation des protobufs

### 1. Génération du code

**Pour Go (content_api, data_scheduler, scheduler_api)**:
```bash
protoc --go_out=. --go-grpc_out=. protobuf/*.proto
```

**Pour Python (fetcher_service)**:
```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. protobuf/*.proto
```

### 2. Clients gRPC

#### content_api → data_scheduler
```go
// Exemple d'appel depuis content_api
client := pb.NewDataSchedulerServiceClient(conn)
response, err := client.GetRounds(ctx, &pb.RoundsFilter{
    Season: 2025,
})
```

#### fetcher_service → data_scheduler
```python
# Exemple d'appel depuis fetcher_service (Python)
stub = DataSchedulerServiceStub(channel)
response = stub.WriteRounds(rounds_data)
```

---

## Flux de données

```
fetcher_service (Python)
    ↓ WriteSeasons/WriteRounds/WriteResults/WriteStandings
data_scheduler (gRPC Server)
    ↓ Persist to MongoDB + Cache to Redis
    ↑ GetSeasons/GetRounds/GetResults/GetStandings
content_api (gRPC Client)
    ↓ Transform to JSON
Utilisateurs finaux (HTTP/REST)
```

---

## Notes importantes

1. **Types de dates**: Tous les timestamps sont en Unix time (int64) pour faciliter la sérialisation
2. **Champs optionnels**: Les filtres utilisent `optional` pour permettre des requêtes flexibles
3. **Cache metadata**: Chaque réponse inclut des métadonnées indiquant si les données viennent du cache Redis
4. **String vs int**: Les positions GPS (lat/long) sont en string pour préserver la précision
5. **Time format**: Les temps de course sont en string car peuvent contenir "DNF", "DNS", "DSQ"
