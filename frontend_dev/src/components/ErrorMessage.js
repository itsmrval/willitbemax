import React from 'react';

const ErrorMessage = ({ message }) => {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="bg-red-900 border border-red-700 text-red-200 px-6 py-4 rounded-lg max-w-md">
        <h3 className="font-bold mb-2">Error</h3>
        <p>{message || 'An unexpected error occurred'}</p>
      </div>
    </div>
  );
};

export default ErrorMessage;
