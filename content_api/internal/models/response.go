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

type Circuit struct {
	Name     string `json:"name"`
	Lat      string `json:"lat"`
	Long     string `json:"long"`
	Locality string `json:"locality"`
	Country  string `json:"country"`
}

type SessionResult struct {
	Position     int32  `json:"position"`
	DriverNumber int32  `json:"driver_number"`
	DriverName   string `json:"driver_name"`
	Team         string `json:"team"`
	Laps         int32  `json:"laps"`
	Time         string `json:"time"`
	Points       int32  `json:"points"`
}

type Session struct {
	Type          string          `json:"type"`
	Date          int64           `json:"date"`
	TotalLaps     *int32          `json:"total_laps"`
	CompletedLaps *int32          `json:"completed_laps"`
	Results       []SessionResult `json:"results"`
}

type Round struct {
	RoundID   int32   `json:"round_id"`
	Name      string  `json:"name"`
	FirstDate int64   `json:"first_date"`
	EndDate   int64   `json:"end_date"`
	Circuit   Circuit `json:"circuit"`
}

type RoundDetails struct {
	Season    int32     `json:"season"`
	RoundID   int32     `json:"round_id"`
	Circuit   Circuit   `json:"circuit"`
	Name      string    `json:"name"`
	FirstDate int64     `json:"first_date"`
	EndDate   int64     `json:"end_date"`
	Sessions  []Session `json:"sessions"`
}

type RoundsResponse struct {
	Metadata Metadata `json:"metadata"`
	Result   struct {
		Season int32   `json:"season"`
		Rounds []Round `json:"rounds"`
	} `json:"result"`
}

type RoundDetailsResponse struct {
	Metadata Metadata     `json:"metadata"`
	Result   RoundDetails `json:"result"`
}

type DriverStanding struct {
	Position       int32  `json:"position"`
	Number         int32  `json:"number"`
	Name           string `json:"name"`
	Nationality    string `json:"nationality"`
	Team           string `json:"team"`
	Points         int32  `json:"points"`
	Wins           int32  `json:"wins"`
	Podiums        int32  `json:"podiums"`
	PolePositions  int32  `json:"pole_positions"`
	FastestLaps    int32  `json:"fastest_laps"`
	DNFCount       int32  `json:"dnf_count"`
	RacesCompleted int32  `json:"races_completed"`
}

type DriverStandingsResponse struct {
	Metadata Metadata `json:"metadata"`
	Result   struct {
		Season    int32            `json:"season"`
		LastRound int32            `json:"last_round"`
		Standings []DriverStanding `json:"standings"`
	} `json:"result"`
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
