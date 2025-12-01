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

type Circuit struct {
	Name        string `json:"name"`
	Lat         string `json:"lat"`
	Long        string `json:"long"`
	Locality    string `json:"locality"`
	Country     string `json:"country"`
	ImageBase64 string `json:"image_base64"`
	Laps        int32  `json:"laps"`
}

type SessionResult struct {
	Position     int32  `json:"position"`
	DriverNumber int32  `json:"driver_number"`
	DriverName   string `json:"driver_name"`
	DriverCode   string `json:"driver_code"`
	Team         string `json:"team"`
	Time         string `json:"time"`
	Laps         int32  `json:"laps"`
}

type Session struct {
	Type       string          `json:"type"`
	Date       int32           `json:"date"`
	TotalLaps  int32           `json:"total_laps"`
	CurrentLap int32           `json:"current_lap"`
	Results    []SessionResult `json:"results"`
}

type Round struct {
	RoundId   int32     `json:"round_id"`
	Name      string    `json:"name"`
	Season    int32     `json:"season"`
	FirstDate int32     `json:"first_date"`
	EndDate   int32     `json:"end_date"`
	Circuit   Circuit   `json:"circuit"`
	Sessions  []Session `json:"sessions"`
}

type RoundsResponse struct {
	Metadata Metadata `json:"metadata"`
	Result   struct {
		Rounds []Round `json:"rounds"`
	} `json:"result"`
}
