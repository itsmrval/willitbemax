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

	yearStr := c.Param("year")
	year, err := strconv.Atoi(yearStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "invalid_year",
			Message: "Year must be a valid integer",
			Code:    http.StatusBadRequest,
		})
		return
	}

	resp, err := h.grpcClient.GetRounds(ctx, &pb.RoundsFilter{
		Season: int32(year),
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
			for _, res := range s.Results {
				results = append(results, models.SessionResult{
					Position:     res.Position,
					DriverNumber: res.DriverNumber,
					DriverName:   res.DriverName,
					Team:         res.Team,
					Time:         res.Time,
					Laps:         res.Laps,
				})
			}

			sessions = append(sessions, models.Session{
				Type:        s.Type,
				Date:        s.Date,
				TotalLaps:   s.TotalLaps,
				CurrentLaps: s.CurrentLaps,
				Results:     results,
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
	response.Result.Season = int32(year)
	response.Result.Rounds = rounds

	c.JSON(http.StatusOK, response)
}

func (h *RoundsHandler) GetRoundDetails(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	yearStr := c.Param("year")
	roundIDStr := c.Param("round_id")

	year, err := strconv.Atoi(yearStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "invalid_year",
			Message: "Year must be a valid integer",
			Code:    http.StatusBadRequest,
		})
		return
	}

	roundID, err := strconv.Atoi(roundIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, models.ErrorResponse{
			Error:   "invalid_round_id",
			Message: "Round ID must be a valid integer",
			Code:    http.StatusBadRequest,
		})
		return
	}

	roundIDInt32 := int32(roundID)
	resp, err := h.grpcClient.GetRounds(ctx, &pb.RoundsFilter{
		Season:  int32(year),
		RoundId: &roundIDInt32,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "grpc_error",
			Message: "Failed to fetch round details from data scheduler",
			Code:    http.StatusInternalServerError,
		})
		return
	}

	if len(resp.Data.Rounds) == 0 {
		c.JSON(http.StatusNotFound, models.ErrorResponse{
			Error:   "not_found",
			Message: "Round not found",
			Code:    http.StatusNotFound,
		})
		return
	}

	r := resp.Data.Rounds[0]

	sessions := make([]models.Session, 0, len(r.Sessions))
	for _, s := range r.Sessions {
		results := make([]models.SessionResult, 0, len(s.Results))
		for _, res := range s.Results {
			results = append(results, models.SessionResult{
				Position:     res.Position,
				DriverNumber: res.DriverNumber,
				DriverName:   res.DriverName,
				Team:         res.Team,
				Time:         res.Time,
				Laps:         res.Laps,
			})
		}

		sessions = append(sessions, models.Session{
			Type:        s.Type,
			Date:        s.Date,
			TotalLaps:   s.TotalLaps,
			CurrentLaps: s.CurrentLaps,
			Results:     results,
		})
	}

	round := models.Round{
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
	}

	response := models.RoundsResponse{
		Metadata: models.Metadata{
			Date:   resp.Metadata.Date,
			Cached: resp.Metadata.Cached,
		},
	}
	response.Result.Season = int32(year)
	response.Result.Rounds = []models.Round{round}

	c.JSON(http.StatusOK, response)
}

