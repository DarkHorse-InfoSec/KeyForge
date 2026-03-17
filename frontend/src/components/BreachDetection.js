import { useState, useEffect } from "react";

const BreachDetection = ({ api }) => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [checkingId, setCheckingId] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const response = await api.get('/breach-check');
      setResults(response.data.results || response.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load breach check results.');
    } finally {
      setLoading(false);
    }
  };

  const handleScanAll = async () => {
    setScanning(true);
    setError('');
    setSuccess('');
    try {
      const response = await api.post('/breach-check/scan-all');
      setSuccess(response.data.message || 'Scan complete.');
      fetchResults();
    } catch (err) {
      setError(err.response?.data?.detail || 'Scan failed.');
    } finally {
      setScanning(false);
    }
  };

  const handleCheckOne = async (credentialId) => {
    setCheckingId(credentialId);
    setError('');
    try {
      await api.post(`/breach-check/${credentialId}`);
      fetchResults();
    } catch (err) {
      setError(err.response?.data?.detail || 'Check failed.');
    } finally {
      setCheckingId(null);
    }
  };

  const summary = {
    total: results.length,
    compromised: results.filter(r => r.status === 'compromised' || r.compromised).length,
    clean: results.filter(r => r.status === 'clean' || r.status === 'safe' || (!r.compromised && r.status !== 'compromised')).length,
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Breach Detection</h2>
        <button
          onClick={handleScanAll}
          disabled={scanning}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
        >
          {scanning ? 'Scanning...' : 'Scan All'}
        </button>
      </div>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4 flex items-center justify-between">
          <p className="text-sm text-red-700">{error}</p>
          <button onClick={() => setError('')} className="text-red-500 text-xs">Dismiss</button>
        </div>
      )}

      {success && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-4 flex items-center justify-between">
          <p className="text-sm text-green-700">{success}</p>
          <button onClick={() => setSuccess('')} className="text-green-500 text-xs">Dismiss</button>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-indigo-50 rounded-lg p-4">
          <p className="text-sm text-indigo-600 font-medium">Total Checked</p>
          <p className="text-2xl font-bold text-indigo-900">{summary.total}</p>
          <p className="text-xs text-indigo-500">credentials scanned</p>
        </div>
        <div className="bg-red-50 rounded-lg p-4">
          <p className="text-sm text-red-600 font-medium">Compromised</p>
          <p className="text-2xl font-bold text-red-900">{summary.compromised}</p>
          <p className="text-xs text-red-500">found in breaches</p>
        </div>
        <div className="bg-green-50 rounded-lg p-4">
          <p className="text-sm text-green-600 font-medium">Clean</p>
          <p className="text-2xl font-bold text-green-900">{summary.clean}</p>
          <p className="text-xs text-green-500">no breaches detected</p>
        </div>
      </div>

      {/* Results Table */}
      {loading ? (
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      ) : results.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">No breach check results</p>
          <p className="text-sm">Click "Scan All" to check your credentials against known breaches.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Credential</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Checked</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Recommendation</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {results.map((result, idx) => {
                const isCompromised = result.status === 'compromised' || result.compromised;
                return (
                  <tr key={result.id || idx}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {result.credential_name || result.credential_id}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${isCompromised ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                        {isCompromised ? 'Compromised' : 'Clean'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {result.checked_at ? new Date(result.checked_at).toLocaleString() : '-'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 max-w-xs">
                      {isCompromised ? (
                        <span className="text-red-600">{result.recommendation || 'Rotate this credential immediately.'}</span>
                      ) : (
                        <span className="text-green-600">{result.recommendation || 'No action needed.'}</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <button
                        onClick={() => handleCheckOne(result.credential_id || result.id)}
                        disabled={checkingId === (result.credential_id || result.id)}
                        className="px-3 py-1 text-xs text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-50 disabled:opacity-50"
                      >
                        {checkingId === (result.credential_id || result.id) ? 'Checking...' : 'Re-check'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default BreachDetection;
