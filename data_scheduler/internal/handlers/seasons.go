package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/willitbemax/data_scheduler/internal/cache"
	"github.com/willitbemax/data_scheduler/internal/database"
	pb "github.com/willitbemax/protobuf/gen/go"
	"go.mongodb.org/mongo-driver/bson"
)

type SeasonsHandler struct {
	db    *database.MongoDB
	cache *cache.RedisClient
}

func NewSeasonsHandler(db *database.MongoDB, cache *cache.RedisClient) *SeasonsHandler {
	return &SeasonsHandler{db: db, cache: cache}
}

func (h *SeasonsHandler) WriteSeasons(ctx context.Context, data *pb.SeasonsData) (*pb.WriteResponse, error) {
	collection := h.db.Seasons()

	var operations []interface{}
	for _, season := range data.Seasons {
		operations = append(operations, bson.M{
			"year":                   season.Year,
			"rounds":                 season.Rounds,
			"start_date":             season.StartDate,
			"end_date":               season.EndDate,
			"status":                 season.Status,
			"current_round":          season.CurrentRound,
			"driver_standings":       season.DriverStandings,
			"constructor_standings":  season.ConstructorStandings,
			"total_drivers":          season.TotalDrivers,
			"total_teams":            season.TotalTeams,
		})
	}

	if len(operations) > 0 {
		_, err := collection.InsertMany(ctx, operations)
		if err != nil {
			return &pb.WriteResponse{Success: false, Message: err.Error()}, err
		}
	}

	h.cache.Del(ctx, "seasons:all")

	return &pb.WriteResponse{
		Success:         true,
		Message:         "Seasons written",
		RecordsAffected: int32(len(operations)),
	}, nil
}

func (h *SeasonsHandler) GetSeasons(ctx context.Context, filter *pb.SeasonsFilter) (*pb.SeasonsResponse, error) {
	cacheKey := "seasons:all"
	if filter.Year != nil {
		cacheKey = fmt.Sprintf("seasons:%d", *filter.Year)
	}

	cached, err := h.cache.Get(ctx, cacheKey)
	if err == nil {
		var data pb.SeasonsData
		if json.Unmarshal([]byte(cached), &data) == nil {
			return &pb.SeasonsResponse{
				Metadata: &pb.Metadata{Date: time.Now().Unix(), Cached: true},
				Data:     &data,
			}, nil
		}
	}

	collection := h.db.Seasons()
	query := bson.M{}
	if filter.Year != nil {
		query["year"] = *filter.Year
	}
	if filter.Status != nil {
		query["status"] = *filter.Status
	}

	cursor, err := collection.Find(ctx, query)
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var seasons []*pb.Season
	for cursor.Next(ctx) {
		var doc bson.M
		if err := cursor.Decode(&doc); err != nil {
			continue
		}

		season := &pb.Season{
			Year:         int32(doc["year"].(int64)),
			Rounds:       int32(doc["rounds"].(int64)),
			StartDate:    doc["start_date"].(int64),
			EndDate:      doc["end_date"].(int64),
			Status:       doc["status"].(string),
			CurrentRound: int32(doc["current_round"].(int64)),
			TotalDrivers: int32(doc["total_drivers"].(int64)),
			TotalTeams:   int32(doc["total_teams"].(int64)),
		}

		if driverStandings, ok := doc["driver_standings"].(bson.A); ok {
			for _, ds := range driverStandings {
				if dsMap, ok := ds.(bson.M); ok {
					season.DriverStandings = append(season.DriverStandings, &pb.DriverStanding{
						Position:     int32(dsMap["position"].(int64)),
						DriverNumber: int32(dsMap["driver_number"].(int64)),
						DriverName:   dsMap["driver_name"].(string),
						DriverCode:   dsMap["driver_code"].(string),
						Team:         dsMap["team"].(string),
						Points:       int32(dsMap["points"].(int64)),
						Wins:         int32(dsMap["wins"].(int64)),
					})
				}
			}
		}

		if constructorStandings, ok := doc["constructor_standings"].(bson.A); ok {
			for _, cs := range constructorStandings {
				if csMap, ok := cs.(bson.M); ok {
					season.ConstructorStandings = append(season.ConstructorStandings, &pb.ConstructorStanding{
						Position: int32(csMap["position"].(int64)),
						Team:     csMap["team"].(string),
						Points:   int32(csMap["points"].(int64)),
						Wins:     int32(csMap["wins"].(int64)),
					})
				}
			}
		}

		seasons = append(seasons, season)
	}

	data := &pb.SeasonsData{Seasons: seasons}

	jsonData, _ := json.Marshal(data)
	h.cache.Set(ctx, cacheKey, jsonData, time.Hour)

	return &pb.SeasonsResponse{
		Metadata: &pb.Metadata{Date: time.Now().Unix(), Cached: false},
		Data:     data,
	}, nil
}
