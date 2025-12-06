package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"time"

	"github.com/willitbemax/data_scheduler/internal/cache"
	"github.com/willitbemax/data_scheduler/internal/database"
	pb "github.com/willitbemax/protobuf/gen/go"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"
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

	var operations []mongo.WriteModel
	for _, round := range data.Rounds {
		var sessionTypes []string
		for _, s := range round.Sessions {
			sessionTypes = append(sessionTypes, s.Type)
		}
		log.Printf("WriteRounds: Round %d has %d sessions: %v", round.RoundId, len(round.Sessions), sessionTypes)
		var circuitBson bson.M
		if round.Circuit != nil {
			circuitBson = bson.M{
				"name":         round.Circuit.Name,
				"laps":         round.Circuit.Laps,
				"image_base64": round.Circuit.ImageBase64,
			}
		}

		var sessionsBson []bson.M
		for _, session := range round.Sessions {
			var resultsBson []bson.M
			for _, result := range session.Results {
				resultsBson = append(resultsBson, bson.M{
					"position":      result.Position,
					"driver_number": result.DriverNumber,
					"driver_name":   result.DriverName,
					"driver_code":   result.DriverCode,
					"team":          result.Team,
					"time":          result.Time,
					"laps":          result.Laps,
				})
			}

			sessionsBson = append(sessionsBson, bson.M{
				"type":        session.Type,
				"date":        session.Date,
				"total_laps":  session.TotalLaps,
				"current_lap": session.CurrentLap,
				"results":     resultsBson,
				"is_live":     session.IsLive,
				"status":      session.Status,
			})
		}

		filter := bson.M{"season": round.Season, "round_id": round.RoundId}
		update := bson.M{
			"$set": bson.M{
				"round_id":   round.RoundId,
				"name":       round.Name,
				"season":     round.Season,
				"circuit":    circuitBson,
				"first_date": round.FirstDate,
				"end_date":   round.EndDate,
				"sessions":   sessionsBson,
			},
		}

		log.Printf("WriteRounds: Storing %d sessions for round %d", len(sessionsBson), round.RoundId)

		operations = append(operations, mongo.NewUpdateOneModel().
			SetFilter(filter).
			SetUpdate(update).
			SetUpsert(true))
	}

	if len(operations) > 0 {
		_, err := collection.BulkWrite(ctx, operations)
		if err != nil {
			return &pb.WriteResponse{Success: false, Message: err.Error()}, err
		}
	}

	if len(data.Rounds) > 0 {
		season := data.Rounds[0].Season
		h.cache.Del(ctx, fmt.Sprintf("rounds:%d", season))
	}

	return &pb.WriteResponse{
		Success:         true,
		Message:         "Rounds written",
		RecordsAffected: int32(len(operations)),
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
			Sessions:  []*pb.Session{},
		}

		if circuitDoc, ok := doc["circuit"].(bson.M); ok {
			round.Circuit = &pb.Circuit{
				Name:        getString(circuitDoc, "name"),
				Laps:        getInt32(circuitDoc, "laps"),
				ImageBase64: getString(circuitDoc, "image_base64"),
			}
		}

		if sessions, ok := doc["sessions"].(bson.A); ok {
			log.Printf("GetRounds: Round %d has %d sessions in database", round.RoundId, len(sessions))
			for _, s := range sessions {
				if sessionMap, ok := s.(bson.M); ok {
					session := &pb.Session{
						Type:       getString(sessionMap, "type"),
						Date:       getInt32(sessionMap, "date"),
						TotalLaps:  getInt32(sessionMap, "total_laps"),
						CurrentLap: getInt32(sessionMap, "current_lap"),
						Results:    []*pb.SessionResult{},
						IsLive:     getBool(sessionMap, "is_live"),
						Status:     getString(sessionMap, "status"),
					}

					if results, ok := sessionMap["results"].(bson.A); ok {
						for _, r := range results {
							if resultMap, ok := r.(bson.M); ok {
								session.Results = append(session.Results, &pb.SessionResult{
									Position:     getInt32(resultMap, "position"),
									DriverNumber: getInt32(resultMap, "driver_number"),
									DriverName:   getString(resultMap, "driver_name"),
									DriverCode:   getString(resultMap, "driver_code"),
									Team:         getString(resultMap, "team"),
									Time:         getString(resultMap, "time"),
									Laps:         getInt32(resultMap, "laps"),
								})
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
	h.cache.Set(ctx, cacheKey, jsonData, time.Hour)

	return &pb.RoundsResponse{
		Metadata: &pb.Metadata{Date: int32(time.Now().Unix()), Cached: false},
		Data:     data,
	}, nil
}
