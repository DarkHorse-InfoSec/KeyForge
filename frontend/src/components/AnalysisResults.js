const AnalysisResults = ({ analysis }) => {
  if (!analysis) return null;

  const getStatusColor = (confidence) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800';
    if (confidence >= 0.5) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Analysis Results</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Detected APIs</h3>
          <div className="space-y-3">
            {analysis.detected_apis.map((api, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h4 className="font-semibold text-gray-900">{api.name}</h4>
                    <p className="text-sm text-gray-600">{api.category}</p>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(api.confidence)}`}>
                    {Math.round(api.confidence * 100)}% confidence
                  </span>
                </div>
                <div className="text-sm text-gray-600">
                  <p><strong>Auth Type:</strong> {api.auth_type}</p>
                  <p><strong>Scopes:</strong> {api.scopes.join(', ')}</p>
                  {api.file && <p><strong>Found in:</strong> {api.file}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Recommendations</h3>
          <div className="space-y-2">
            {analysis.recommendations.map((rec, index) => (
              <div key={index} className="flex items-start">
                <div className="flex-shrink-0 w-2 h-2 mt-2 bg-indigo-600 rounded-full"></div>
                <p className="ml-3 text-sm text-gray-700">{rec}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="font-semibold text-gray-800 mb-2">Project Stats</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-600">Files Analyzed</p>
                <p className="font-semibold">{analysis.file_count}</p>
              </div>
              <div>
                <p className="text-gray-600">APIs Detected</p>
                <p className="font-semibold">{analysis.detected_apis.length}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalysisResults;
