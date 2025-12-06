const API_BASE_URL = process.env.REACT_APP_CONTENT_API_URL || 'http://localhost';

class ContentAPI {
  /**
   * Fetch rounds for a specific season
   * @param {number} year - The season year
   * @returns {Promise<Object>} - API response with rounds data
   */
  async getRounds(year) {
    try {
      const response = await fetch(`${API_BASE_URL}/content/v1/seasons/${year}/rounds`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error fetching rounds:', error);
      throw error;
    }
  }

  /**
   * Find the next or current round and session
   * @param {number} year - The season year
   * @returns {Promise<Object|null>} - Object with round and session info, or null
   */
  async getNextRoundAndSession(year) {
    try {
      const data = await this.getRounds(year);

      if (!data.result || !data.result.rounds || data.result.rounds.length === 0) {
        return null;
      }

      const now = Math.floor(Date.now() / 1000);
      const rounds = data.result.rounds;

      // Find the next/current round
      for (const round of rounds) {
        // Check if this round is still ongoing or upcoming
        if (round.end_date >= now) {
          // Find the next/current session within this round
          const sessions = round.sessions || [];

          let nextSession = null;
          let currentSession = null;

          for (const session of sessions) {
            if (session.is_live) {
              currentSession = session;
              break;
            } else if (session.date >= now && !nextSession) {
              nextSession = session;
            }
          }

          return {
            round,
            session: currentSession || nextSession,
            isLive: !!currentSession,
            isFinished: false
          };
        }
      }

      // If all rounds are finished, return the last round
      const lastRound = rounds[rounds.length - 1];
      return {
        round: lastRound,
        session: null,
        isLive: false,
        isFinished: true
      };
    } catch (error) {
      console.error('Error getting next round and session:', error);
      throw error;
    }
  }

  /**
   * Get current year
   * @returns {number} - Current year
   */
  getCurrentYear() {
    return new Date().getFullYear();
  }
}

export default new ContentAPI();
