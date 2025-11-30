package middleware

import (
	"log"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/willitbemax/content_api/internal/models"
)

func ErrorHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		defer func() {
			if err := recover(); err != nil {
				log.Printf("PANIC: %v", err)
				c.JSON(http.StatusInternalServerError, models.ErrorResponse{
					Error:   "internal_server_error",
					Message: "An unexpected error occurred",
					Code:    http.StatusInternalServerError,
				})
				c.Abort()
			}
		}()

		c.Next()

		if len(c.Errors) > 0 {
			err := c.Errors.Last()
			log.Printf("ERROR: %v", err.Err)

			if !c.Writer.Written() {
				c.JSON(http.StatusInternalServerError, models.ErrorResponse{
					Error:   "internal_server_error",
					Message: err.Error(),
					Code:    http.StatusInternalServerError,
				})
			}
		}
	}
}
