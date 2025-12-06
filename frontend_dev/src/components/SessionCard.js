import React from 'react';

const SessionCard = ({ session, isLive }) => {
  if (!session) return null;

  const formatDate = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short'
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

  return (
    <div className={`p-6 rounded-lg ${isLive ? 'bg-red-600' : 'bg-slate-700'}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xl font-bold">{getSessionTypeLabel(session.type)}</h3>
        {isLive && (
          <span className="px-3 py-1 bg-white text-red-600 rounded-full text-sm font-bold animate-pulse">
            LIVE
          </span>
        )}
      </div>
      <p className="text-slate-300">{formatDate(session.date)}</p>
      {session.status && (
        <p className="mt-2 text-sm text-slate-400 capitalize">{session.status}</p>
      )}
    </div>
  );
};

export default SessionCard;
