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

type SeasonsHandler struct {
	grpcClient *grpc.Client
}

func NewSeasonsHandler(grpcClient *grpc.Client) *SeasonsHandler {
	return &SeasonsHandler{grpcClient: grpcClient}
}

func (h *SeasonsHandler) GetSeasons(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	filter := &pb.SeasonsFilter{}

	if yearStr := c.Query("year"); yearStr != "" {
		if year, err := strconv.ParseInt(yearStr, 10, 32); err == nil {
			yearInt32 := int32(year)
			filter.Year = &yearInt32
		}
	}

	if status := c.Query("status"); status != "" {
		filter.Status = &status
	}

	resp, err := h.grpcClient.GetSeasons(ctx, filter)
	if err != nil {
		c.JSON(http.StatusInternalServerError, models.ErrorResponse{
			Error:   "grpc_error",
			Message: "Failed to fetch seasons from data scheduler",
			Code:    http.StatusInternalServerError,
		})
		return
	}

	seasons := make([]models.Season, 0, len(resp.Data.Seasons))
	for _, s := range resp.Data.Seasons {
		driverStandings := make([]models.SeasonDriverStanding, 0, len(s.DriverStandings))
		for _, ds := range s.DriverStandings {
			driverStandings = append(driverStandings, models.SeasonDriverStanding{
				Position:     ds.Position,
				DriverNumber: ds.DriverNumber,
				DriverName:   ds.DriverName,
				DriverCode:   ds.DriverCode,
				Team:         ds.Team,
				Points:       ds.Points,
				Wins:         ds.Wins,
			})
		}

		constructorStandings := make([]models.SeasonConstructorStanding, 0, len(s.ConstructorStandings))
		for _, cs := range s.ConstructorStandings {
			constructorStandings = append(constructorStandings, models.SeasonConstructorStanding{
				Position: cs.Position,
				Team:     cs.Team,
				Points:   cs.Points,
				Wins:     cs.Wins,
			})
		}

		seasons = append(seasons, models.Season{
			Year:                 s.Year,
			Rounds:               s.Rounds,
			StartDate:            s.StartDate,
			EndDate:              s.EndDate,
			Status:               s.Status,
			CurrentRound:         s.CurrentRound,
			DriverStandings:      driverStandings,
			ConstructorStandings: constructorStandings,
			TotalDrivers:         s.TotalDrivers,
			TotalTeams:           s.TotalTeams,
		})
	}

	response := models.SeasonsResponse{
		Metadata: models.Metadata{
			Date:   resp.Metadata.Date,
			Cached: resp.Metadata.Cached,
		},
	}
	response.Result.Seasons = seasons

	c.JSON(http.StatusOK, response)
}
