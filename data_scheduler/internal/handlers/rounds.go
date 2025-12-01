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
	"go.mongodb.org/mongo-driver/mongo/options"
)

type RoundsHandler struct {
	db    *database.MongoDB
	cache *cache.RedisClient
}

func NewRoundsHandler(db *database.MongoDB, cache *cache.RedisClient) *RoundsHandler {
	return &RoundsHandler{db: db, cache: cache}
}

func (h *RoundsHandler) WriteRounds(ctx context.Context, data *pb.RoundsData) (*pb.WriteResponse, error) {
	collection := h.db.Rounds()

	for _, round := range data.Rounds {
		var sessions []bson.M
		for _, session := range round.Sessions {
			var results []bson.M
			for _, result := range session.Results {
				results = append(results, bson.M{
					"position":      result.Position,
					"driver_number": result.DriverNumber,
					"driver_name":   result.DriverName,
					"team":          result.Team,
					"time":          result.Time,
					"laps":          result.Laps,
				})
			}

			sessions = append(sessions, bson.M{
				"type":         session.Type,
				"date":         session.Date,
				"total_laps":   session.TotalLaps,
				"current_laps": session.CurrentLaps,
				"results":      results,
			})
		}

		circuit := bson.M{
			"name":          round.Circuit.Name,
			"lat":           round.Circuit.Lat,
			"long":          round.Circuit.Long,
			"locality":      round.Circuit.Locality,
			"country":       round.Circuit.Country,
			"image_base64":  round.Circuit.ImageBase64,
			"laps":          round.Circuit.Laps,
		}

		roundDoc := bson.M{
			"round_id":   round.RoundId,
			"name":       round.Name,
			"season":     round.Season,
			"circuit":    circuit,
			"first_date": round.FirstDate,
			"end_date":   round.EndDate,
			"sessions":   sessions,
		}

		filter := bson.M{"season": round.Season, "round_id": round.RoundId}
		update := bson.M{"$set": roundDoc}
		opts := options.Update().SetUpsert(true)

		_, err := collection.UpdateOne(ctx, filter, update, opts)
		if err != nil {
			return &pb.WriteResponse{Success: false, Message: err.Error()}, err
		}

		h.cache.Del(ctx, fmt.Sprintf("rounds:%d", round.Season))
		h.cache.Del(ctx, fmt.Sprintf("rounds:%d:%d", round.Season, round.RoundId))
	}

	return &pb.WriteResponse{
		Success:         true,
		Message:         "Rounds written",
		RecordsAffected: int32(len(data.Rounds)),
	}, nil
}

func (h *RoundsHandler) GetRounds(ctx context.Context, filter *pb.RoundsFilter) (*pb.RoundsResponse, error) {
	cacheKey := fmt.Sprintf("rounds:%d", filter.Season)
	if filter.RoundId != nil {
		cacheKey = fmt.Sprintf("rounds:%d:%d", filter.Season, *filter.RoundId)
	}

	cached, err := h.cache.Get(ctx, cacheKey)
	if err == nil {
		var data pb.RoundsData
		if json.Unmarshal([]byte(cached), &data) == nil {
			return &pb.RoundsResponse{
				Metadata: &pb.Metadata{Date: int32(time.Now().Unix()), Cached: true},
				Data:     &data,
			}, nil
		}
	}

	collection := h.db.Rounds()
	query := bson.M{"season": filter.Season}
	if filter.RoundId != nil {
		query["round_id"] = *filter.RoundId
	}

	cursor, err := collection.Find(ctx, query)
	if err != nil {
		return nil, err
	}
	defer cursor.Close(ctx)

	var rounds []*pb.Round
	for cursor.Next(ctx) {
		var doc bson.M
		if err := cursor.Decode(&doc); err != nil {
			continue
		}

		round := &pb.Round{
			RoundId:   getInt32(doc, "round_id"),
			Name:      getString(doc, "name"),
			Season:    getInt32(doc, "season"),
			FirstDate: getInt32(doc, "first_date"),
			EndDate:   getInt32(doc, "end_date"),
			Circuit:   &pb.Circuit{},
			Sessions:  []*pb.Session{},
		}

		if circuitMap, ok := doc["circuit"].(bson.M); ok {
			round.Circuit = &pb.Circuit{
				Name:        getString(circuitMap, "name"),
				Lat:         getString(circuitMap, "lat"),
				Long:        getString(circuitMap, "long"),
				Locality:    getString(circuitMap, "locality"),
				Country:     getString(circuitMap, "country"),
				ImageBase64: getString(circuitMap, "image_base64"),
				Laps:        getInt32(circuitMap, "laps"),
			}
		}

		if sessionsArray, ok := doc["sessions"].(bson.A); ok {
			for _, sess := range sessionsArray {
				if sessionMap, ok := sess.(bson.M); ok {
					session := &pb.Session{
						Type:        getString(sessionMap, "type"),
						Date:        getInt32(sessionMap, "date"),
						TotalLaps:   getInt32(sessionMap, "total_laps"),
						CurrentLaps: getInt32(sessionMap, "current_laps"),
						Results:     []*pb.SessionResult{},
					}

					if resultsArray, ok := sessionMap["results"].(bson.A); ok {
						for _, res := range resultsArray {
							if resultMap, ok := res.(bson.M); ok {
								result := &pb.SessionResult{
									Position:     getInt32(resultMap, "position"),
									DriverNumber: getInt32(resultMap, "driver_number"),
									DriverName:   getString(resultMap, "driver_name"),
									Team:         getString(resultMap, "team"),
									Time:         getString(resultMap, "time"),
									Laps:         getInt32(resultMap, "laps"),
								}
								session.Results = append(session.Results, result)
							}
						}
					}

					round.Sessions = append(round.Sessions, session)
				}
			}
		}

		rounds = append(rounds, round)
	}

	data := &pb.RoundsData{Rounds: rounds}

	jsonData, _ := json.Marshal(data)
	h.cache.Set(ctx, cacheKey, jsonData, 30*time.Minute)

	return &pb.RoundsResponse{
		Metadata: &pb.Metadata{Date: int32(time.Now().Unix()), Cached: false},
		Data:     data,
	}, nil
}

