import React from 'react';

const RoundCard = ({ round, session, isLive }) => {
  if (!round) return null;

  const formatDate = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatSessionDate = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getSessionTypeLabel = (type) => {
    const labels = {
      'race': 'Race',
      'qualifying': 'Qualifying',
      'sprint': 'Sprint',
      'practice_1': 'Practice 1',
      'practice_2': 'Practice 2',
      'practice_3': 'Practice 3'
    };
    return labels[type] || type;
  };

  const getStatusBadge = () => {
    if (isLive) {
      return (
        <span className="px-3 py-1 bg-red-600 text-white rounded-full text-xs font-bold animate-pulse">
          LIVE
        </span>
      );
    }
    return (
      <span className="px-3 py-1 bg-green-600 text-white rounded-full text-xs font-bold">
        UPCOMING
      </span>
    );
  };

  const getPreviousSessions = () => {
    if (!round.sessions) return [];
    const now = Math.floor(Date.now() / 1000);
    return round.sessions.filter(s => s.date < now && s.status === 'finished').reverse();
  };

  const previousSessions = getPreviousSessions();

  return (
    <div className="space-y-6">
      <div className="bg-slate-800 rounded-lg shadow-2xl overflow-hidden">
        <div className="flex flex-col md:flex-row">
          <div className="md:w-1/2 p-8">
            <h3 className="text-lg font-semibold text-slate-300 mb-4">Upcoming Event</h3>
            {round.circuit?.image_base64 && (
              <img
                src={`data:image/png;base64,${round.circuit.image_base64}`}
                alt={round.circuit.name}
                className="w-full rounded-lg shadow-lg"
              />
            )}
          </div>

          <div className="md:w-1/2 p-8 flex flex-col justify-between">
            <div>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-3xl font-bold text-white mb-2">{round.name}</h2>
                  {round.circuit && (
                    <p className="text-xl text-slate-300">{round.circuit.name}</p>
                  )}
                </div>
                <span className="text-sm text-slate-400 bg-slate-700 px-3 py-1 rounded">
                  Round {round.round_id}
                </span>
              </div>

              <div className="flex flex-wrap gap-4 mb-6 text-sm">
                <div>
                  <span className="text-slate-400">Date: </span>
                  <span className="text-white">{formatDate(round.first_date)} - {formatDate(round.end_date)}</span>
                </div>
                {round.circuit?.laps > 0 && (
                  <div>
                    <span className="text-slate-400">Laps: </span>
                    <span className="text-white">{round.circuit.laps}</span>
                  </div>
                )}
              </div>
            </div>

            {session && (
              <div className="bg-slate-700 rounded-lg p-5">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xl font-bold text-white">
                    {getSessionTypeLabel(session.type)}
                  </h4>
                  {getStatusBadge()}
                </div>
                <p className="text-slate-200 text-sm mb-1">{formatSessionDate(session.date)}</p>

                {isLive && session.results && session.results.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-slate-600">
                    <h5 className="text-sm font-semibold text-slate-300 mb-3">Live Standings</h5>
                    <div className="space-y-2">
                      {session.results.slice(0, 5).map((result, idx) => (
                        <div key={idx} className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-3">
                            <span className="text-slate-400 font-bold font-mono w-5">{result.position}</span>
                            <span className="text-white font-semibold">{result.driver_name}</span>
                          </div>
                          <span className="text-slate-300 font-mono text-xs">{result.time}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {previousSessions.length > 0 && (
        <div className="bg-slate-800 rounded-lg p-6 shadow-2xl">
          <h3 className="text-xl font-bold text-white mb-4">Previous Sessions</h3>
          <div className="space-y-4">
            {previousSessions.map((prevSession, idx) => (
              <div key={idx} className="bg-slate-700 rounded-lg p-5">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-lg font-semibold text-white">
                    {getSessionTypeLabel(prevSession.type)}
                  </h4>
                  <span className="px-3 py-1 bg-slate-600 text-slate-300 rounded-full text-xs font-semibold capitalize">
                    {prevSession.status}
                  </span>
                </div>
                {prevSession.results && prevSession.results.length > 0 && (
                  <div className="space-y-2">
                    {prevSession.results.slice(0, 5).map((result, resultIdx) => (
                      <div key={resultIdx} className="flex items-center justify-between text-sm py-1">
                        <div className="flex items-center gap-4">
                          <span className="text-slate-400 font-bold font-mono w-5">{result.position}</span>
                          <div>
                            <div className="text-white font-semibold">{result.driver_name}</div>
                            <div className="text-slate-500 text-xs">{result.team}</div>
                          </div>
                        </div>
                        <span className="text-slate-300 font-mono text-sm">{result.time}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default RoundCard;
