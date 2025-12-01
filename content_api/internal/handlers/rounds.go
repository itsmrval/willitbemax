package handlers

import (
	"context"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/willitbemax/content_api/internal/grpc"
	"github.com/willitbemax/content_api/internal/models"
	pb "github.com/willitbemax/protobuf/gen/go"
)

type RoundsHandler struct {
	grpcClient *grpc.Client
}

func NewRoundsHandler(grpcClient *grpc.Client) *RoundsHandler {
	return &RoundsHandler{grpcClient: grpcClient}
}

func (h *RoundsHandler) GetRounds(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	seasonStr := c.Param("year")
	season, err := strconv.Atoi(seasonStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "invalid_season",
			Message: "Season must be a valid year",
			Code:    http.StatusBadRequest,
		})
		return
	}

	var roundId *int32
	if roundStr := c.Query("round"); roundStr != "" {
		rid, _ := strconv.Atoi(roundStr)
		rid32 := int32(rid)
		roundId = &rid32
	}

	resp, err := h.grpcClient.GetRounds(ctx, &pb.RoundsFilter{
		Season:  int32(season),
		RoundId: roundId,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "grpc_error",
			Message: "Failed to fetch rounds from data scheduler",
			Code:    http.StatusInternalServerError,
		})
		return
	}

	rounds := make([]models.Round, 0, len(resp.Data.Rounds))
	for _, r := range resp.Data.Rounds {
		sessions := make([]models.Session, 0, len(r.Sessions))
		for _, s := range r.Sessions {
			results := make([]models.SessionResult, 0, len(s.Results))
			for _, sr := range s.Results {
				results = append(results, models.SessionResult{
					Position:     sr.Position,
					DriverNumber: sr.DriverNumber,
					DriverName:   sr.DriverName,
					DriverCode:   sr.DriverCode,
					Team:         sr.Team,
					Time:         sr.Time,
					Laps:         sr.Laps,
				})
			}

			sessions = append(sessions, models.Session{
				Type:       s.Type,
				Date:       s.Date,
				TotalLaps:  s.TotalLaps,
				CurrentLap: s.CurrentLap,
				Results:    results,
			})
		}

		rounds = append(rounds, models.Round{
			RoundId:   r.RoundId,
			Name:      r.Name,
			Season:    r.Season,
			FirstDate: r.FirstDate,
			EndDate:   r.EndDate,
			Circuit: models.Circuit{
				Name:        r.Circuit.Name,
				Lat:         r.Circuit.Lat,
				Long:        r.Circuit.Long,
				Locality:    r.Circuit.Locality,
				Country:     r.Circuit.Country,
				ImageBase64: r.Circuit.ImageBase64,
				Laps:        r.Circuit.Laps,
			},
			Sessions: sessions,
		})
	}

	response := models.RoundsResponse{
		Metadata: models.Metadata{
			Date:   resp.Metadata.Date,
			Cached: resp.Metadata.Cached,
		},
	}
	response.Result.Rounds = rounds

	c.JSON(http.StatusOK, response)
}

func (h *RoundsHandler) GetRound(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	seasonStr := c.Param("year")
	roundIdStr := c.Param("round_id")

	season, err := strconv.Atoi(seasonStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "invalid_season",
			Message: "Season must be a valid year",
			Code:    http.StatusBadRequest,
		})
		return
	}

	roundId, err := strconv.Atoi(roundIdStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "invalid_round",
			Message: "Round ID must be a valid integer",
			Code:    http.StatusBadRequest,
		})
		return
	}

	rid32 := int32(roundId)
	resp, err := h.grpcClient.GetRounds(ctx, &pb.RoundsFilter{
		Season:  int32(season),
		RoundId: &rid32,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "grpc_error",
			Message: "Failed to fetch round from data scheduler",
			Code:    http.StatusInternalServerError,
		})
		return
	}

	rounds := make([]models.Round, 0, len(resp.Data.Rounds))
	for _, r := range resp.Data.Rounds {
		sessions := make([]models.Session, 0, len(r.Sessions))
		for _, s := range r.Sessions {
			results := make([]models.SessionResult, 0, len(s.Results))
			for _, sr := range s.Results {
				results = append(results, models.SessionResult{
					Position:     sr.Position,
					DriverNumber: sr.DriverNumber,
					DriverName:   sr.DriverName,
					DriverCode:   sr.DriverCode,
					Team:         sr.Team,
					Time:         sr.Time,
					Laps:         sr.Laps,
				})
			}

			sessions = append(sessions, models.Session{
				Type:       s.Type,
				Date:       s.Date,
				TotalLaps:  s.TotalLaps,
				CurrentLap: s.CurrentLap,
				Results:    results,
			})
		}

		rounds = append(rounds, models.Round{
			RoundId:   r.RoundId,
			Name:      r.Name,
			Season:    r.Season,
			FirstDate: r.FirstDate,
			EndDate:   r.EndDate,
			Circuit: models.Circuit{
				Name:        r.Circuit.Name,
				Lat:         r.Circuit.Lat,
				Long:        r.Circuit.Long,
				Locality:    r.Circuit.Locality,
				Country:     r.Circuit.Country,
				ImageBase64: r.Circuit.ImageBase64,
				Laps:        r.Circuit.Laps,
			},
			Sessions: sessions,
		})
	}

	response := models.RoundsResponse{
		Metadata: models.Metadata{
			Date:   resp.Metadata.Date,
			Cached: resp.Metadata.Cached,
		},
	}
	response.Result.Rounds = rounds

	c.JSON(http.StatusOK, response)
}
