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

#### DriverStanding
```protobuf
message DriverStanding {
  int32 position = 1;
  int32 driver_number = 2;
  string driver_name = 3;
  string driver_code = 4;
  string team = 5;
  int32 points = 6;
  int32 wins = 7;
}
```

#### ConstructorStanding
```protobuf
message ConstructorStanding {
  int32 position = 1;
  string team = 2;
  int32 points = 3;
  int32 wins = 4;
}
```

#### Season
```protobuf
message Season {
  int32 year = 1;
  int32 rounds = 2;
  int32 start_date = 3;
  int32 end_date = 4;
  string status = 5;                                    // "completed", "in_progress", "upcoming"
  int32 current_round = 6;
  repeated DriverStanding driver_standings = 7;
  repeated ConstructorStanding constructor_standings = 8;
  int32 total_drivers = 9;
  int32 total_teams = 10;
}
```

#### SeasonsData
```protobuf
message SeasonsData {
  repeated Season seasons = 1;
}
```

### Rounds (Courses)

#### Circuit
```protobuf
message Circuit {
  string name = 1;
  string lat = 2;
  string long = 3;
  string locality = 4;
  string country = 5;
  string image_base64 = 6;    // Image du circuit encodée en base64
  int32 laps = 7;              // Nombre de tours du circuit
}
```

#### SessionResult
```protobuf
message SessionResult {
  int32 position = 1;
  int32 driver_number = 2;
  string driver_name = 3;
  string driver_code = 4;      // Code pilote (VER, NOR, etc.)
  string team = 5;
  string time = 6;             // Temps absolu
  int32 laps = 7;              // Tours complétés
}
```

#### Session
```protobuf
message Session {
  string type = 1;                           // practice_1, practice_2, practice_3, qualifying, sprint_qualifying, sprint, race
  int32 date = 2;                            // Timestamp Unix de la session
  int32 total_laps = 3;                      // Tours prévus (0 pour qualifying)
  int32 current_laps = 4;                    // Tours actuels
  repeated SessionResult results = 5;
}
```

#### Round
```protobuf
message Round {
  int32 round_id = 1;
  string name = 2;
  int32 season = 3;
  Circuit circuit = 4;
  int32 first_date = 5;        // Date de début du weekend
  int32 end_date = 6;          // Date de fin du weekend
  repeated Session sessions = 7;
}
```

#### RoundsData
```protobuf
message RoundsData {
  repeated Round rounds = 1;
}
```

## Filtres et Réponses

### Seasons

#### SeasonsFilter
```protobuf
message SeasonsFilter {
  optional int32 year = 1;
  optional string status = 2;
}
```

#### SeasonsResponse
```protobuf
message SeasonsResponse {
  Metadata metadata = 1;
  SeasonsData data = 2;
}
```

### Rounds

#### RoundsFilter
```protobuf
message RoundsFilter {
  int32 season = 1;              // Obligatoire
  optional int32 round_id = 2;   // Optionnel: filtre sur un round spécifique
}
```

#### RoundsResponse
```protobuf
message RoundsResponse {
  Metadata metadata = 1;
  RoundsData data = 2;
}
```

### WriteResponse
```protobuf
message WriteResponse {
  bool success = 1;
  string message = 2;
  int32 records_affected = 3;
}
```

## Service gRPC: DataSchedulerService

```protobuf
service DataSchedulerService {
  // Seasons
  rpc WriteSeasons(SeasonsData) returns (WriteResponse);
  rpc GetSeasons(SeasonsFilter) returns (SeasonsResponse);
  
  // Rounds
  rpc WriteRounds(RoundsData) returns (WriteResponse);
  rpc GetRounds(RoundsFilter) returns (RoundsResponse);
}
```

