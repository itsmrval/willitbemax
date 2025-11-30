package models

type Metadata struct {
	Date   int32 `json:"date"`
	Cached bool  `json:"cached"`
}

type ErrorResponse struct {
	Error   string `json:"error"`
	Message string `json:"message,omitempty"`
	Code    int    `json:"code"`
}

type SeasonDriverStanding struct {
	Position     int32  `json:"position"`
	DriverNumber int32  `json:"driver_number"`
	DriverName   string `json:"driver_name"`
	DriverCode   string `json:"driver_code"`
	Team         string `json:"team"`
	Points       int32  `json:"points"`
	Wins         int32  `json:"wins"`
}

type SeasonConstructorStanding struct {
	Position int32  `json:"position"`
	Team     string `json:"team"`
	Points   int32  `json:"points"`
	Wins     int32  `json:"wins"`
}

type Season struct {
	Year                  int32                       `json:"year"`
	Rounds                int32                       `json:"rounds"`
	StartDate             int32                       `json:"start_date"`
	EndDate               int32                       `json:"end_date"`
	Status                string                      `json:"status"`
	CurrentRound          int32                       `json:"current_round"`
	DriverStandings       []SeasonDriverStanding      `json:"driver_standings"`
	ConstructorStandings  []SeasonConstructorStanding `json:"constructor_standings"`
	TotalDrivers          int32                       `json:"total_drivers"`
	TotalTeams            int32                       `json:"total_teams"`
}

type SeasonsResponse struct {
	Metadata Metadata `json:"metadata"`
	Result   struct {
		Seasons []Season `json:"seasons"`
	} `json:"result"`
}
