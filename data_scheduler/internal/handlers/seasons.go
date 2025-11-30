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

func getInt32(m bson.M, key string) int32 {
	if val, ok := m[key]; ok && val != nil {
		switch v := val.(type) {
		case int32:
			return v
		case int64:
			return int32(v)
		case int:
			return int32(v)
		}
	}
	return 0
}

func getString(m bson.M, key string) string {
	if val, ok := m[key]; ok && val != nil {
		if str, ok := val.(string); ok {
			return str
		}
	}
	return ""
}

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
		var driverStandings []bson.M
		for _, ds := range season.DriverStandings {
			driverStandings = append(driverStandings, bson.M{
				"position":      ds.Position,
				"driver_number": ds.DriverNumber,
				"driver_name":   ds.DriverName,
				"driver_code":   ds.DriverCode,
				"team":          ds.Team,
				"points":        ds.Points,
				"wins":          ds.Wins,
			})
		}

		var constructorStandings []bson.M
		for _, cs := range season.ConstructorStandings {
			constructorStandings = append(constructorStandings, bson.M{
				"position": cs.Position,
				"team":     cs.Team,
				"points":   cs.Points,
				"wins":     cs.Wins,
			})
		}

		operations = append(operations, bson.M{
			"year":                   season.Year,
			"rounds":                 season.Rounds,
			"start_date":             season.StartDate,
			"end_date":               season.EndDate,
			"status":                 season.Status,
			"current_round":          season.CurrentRound,
			"driver_standings":       driverStandings,
			"constructor_standings":  constructorStandings,
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
				Metadata: &pb.Metadata{Date: int32(time.Now().Unix()), Cached: true},
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
			Year:                 getInt32(doc, "year"),
			Rounds:               getInt32(doc, "rounds"),
			StartDate:            getInt32(doc, "start_date"),
			EndDate:              getInt32(doc, "end_date"),
			Status:               getString(doc, "status"),
			CurrentRound:         getInt32(doc, "current_round"),
			TotalDrivers:         getInt32(doc, "total_drivers"),
			TotalTeams:           getInt32(doc, "total_teams"),
			DriverStandings:      []*pb.DriverStanding{},
			ConstructorStandings: []*pb.ConstructorStanding{},
		}

		if driverStandings, ok := doc["driver_standings"].(bson.A); ok {
			for _, ds := range driverStandings {
				if dsMap, ok := ds.(bson.M); ok {
					season.DriverStandings = append(season.DriverStandings, &pb.DriverStanding{
						Position:     getInt32(dsMap, "position"),
						DriverNumber: getInt32(dsMap, "driver_number"),
						DriverName:   getString(dsMap, "driver_name"),
						DriverCode:   getString(dsMap, "driver_code"),
						Team:         getString(dsMap, "team"),
						Points:       getInt32(dsMap, "points"),
						Wins:         getInt32(dsMap, "wins"),
					})
				}
			}
		}

		if constructorStandings, ok := doc["constructor_standings"].(bson.A); ok {
			for _, cs := range constructorStandings {
				if csMap, ok := cs.(bson.M); ok {
					season.ConstructorStandings = append(season.ConstructorStandings, &pb.ConstructorStanding{
						Position: getInt32(csMap, "position"),
						Team:     getString(csMap, "team"),
						Points:   getInt32(csMap, "points"),
						Wins:     getInt32(csMap, "wins"),
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
		Metadata: &pb.Metadata{Date: int32(time.Now().Unix()), Cached: false},
		Data:     data,
	}, nil
}
