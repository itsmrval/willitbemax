import React, { useState, useEffect } from 'react';
import contentApi from '../api/contentApi';
import RoundCard from '../components/RoundCard';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';

const Home = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        let year = contentApi.getCurrentYear();
        let result = await contentApi.getNextRoundAndSession(year);

        if (!result) {
          year += 1;
          result = await contentApi.getNextRoundAndSession(year);
        }

        setData(result);
        setError(null);
        setLastUpdate(new Date());
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Refresh every 30 seconds if live, otherwise every 60 seconds
    const getInterval = () => data?.isLive ? 30000 : 60000;
    const interval = setInterval(fetchData, getInterval());
    return () => clearInterval(interval);
  }, [data?.isLive]);

  if (loading) return <Loading />;
  if (error) return <ErrorMessage message={error} />;
  if (!data) return <ErrorMessage message="No data available" />;

  const getStatusMessage = () => {
    if (data.isLive) {
      return (
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
            </span>
            <span className="text-red-500 font-bold text-lg">LIVE NOW</span>
          </div>
          <span className="text-slate-400 text-xs">
            Updates every 30 seconds • Last update: {lastUpdate.toLocaleTimeString()}
          </span>
        </div>
      );
    }
    if (data.isFinished) {
      return <span className="text-slate-400">Season Complete</span>;
    }
    return (
      <div className="flex flex-col items-center gap-2">
        <span className="text-green-500 font-bold">Upcoming</span>
        <span className="text-slate-400 text-xs">
          Last update: {lastUpdate.toLocaleTimeString()}
        </span>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        <header className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">
            Will It Be Max?
          </h1>
          <p className="text-xl text-slate-300">
            {data.isFinished ? 'Last' : 'Next'} Race Weekend
          </p>
          <div className="mt-2">{getStatusMessage()}</div>
        </header>

        <RoundCard round={data.round} session={data.session} isLive={data.isLive} />

        {data.isFinished && (
          <div className="bg-slate-700 p-6 rounded-lg text-center mt-6">
            <p className="text-lg text-slate-300">
              The season has ended. See you next year!
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Home;
