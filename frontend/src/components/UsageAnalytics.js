import { useState, useEffect } from "react";

const UsageAnalytics = ({ api }) => {
  const [dashboard, setDashboard] = useState(null);
  const [idleCredentials, setIdleCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedCredential, setSelectedCredential] = useState(null);
  const [credentialUsage, setCredentialUsage] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [dashRes, idleRes] = await Promise.allSettled([
        api.get('/usage/dashboard'),
        api.get('/usage/idle-credentials'),
      ]);
      if (dashRes.status === 'fulfilled') setDashboard(dashRes.value.data);
      if (idleRes.status === 'fulfilled') setIdleCredentials(idleRes.value.data.credentials || idleRes.value.data || []);
    } catch (err) {
      setError('Failed to load usage analytics.');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = async (credentialId, credentialName) => {
    setSelectedCredential({ id: credentialId, name: credentialName });
    setDetailLoading(true);
    try {
      const response = await api.get(`/usage/credentials/${credentialId}`);
      setCredentialUsage(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load credential usage.');
    } finally {
      setDetailLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Usage Analytics</h2>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4 flex items-center justify-between">
          <p className="text-sm text-red-700">{error}</p>
          <button onClick={() => setError('')} className="text-red-500 text-xs">Dismiss</button>
        </div>
      )}

      {/* Dashboard Stats */}
      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-indigo-50 rounded-lg p-4">
            <p className="text-sm text-indigo-600 font-medium">Total</p>
            <p className="text-2xl font-bold text-indigo-900">{dashboard.total ?? 0}</p>
            <p className="text-xs text-indigo-500">credentials</p>
          </div>
          <div className="bg-green-50 rounded-lg p-4">
            <p className="text-sm text-green-600 font-medium">Active</p>
            <p className="text-2xl font-bold text-green-900">{dashboard.active ?? 0}</p>
            <p className="text-xs text-green-500">recently used</p>
          </div>
          <div className="bg-yellow-50 rounded-lg p-4">
            <p className="text-sm text-yellow-600 font-medium">Idle</p>
            <p className="text-2xl font-bold text-yellow-900">{dashboard.idle ?? 0}</p>
            <p className="text-xs text-yellow-500">no recent usage</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-600 font-medium">Never Used</p>
            <p className="text-2xl font-bold text-gray-900">{dashboard.never_used ?? 0}</p>
            <p className="text-xs text-gray-500">no recorded usage</p>
          </div>
        </div>
      )}

      {/* Top 5 Most Used */}
      {dashboard?.top_used && dashboard.top_used.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Top 5 Most Used</h3>
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
            {dashboard.top_used.slice(0, 5).map((item, idx) => (
              <button
                key={item.credential_id || idx}
                onClick={() => handleViewDetails(item.credential_id, item.credential_name)}
                className="p-3 bg-indigo-50 rounded-lg text-left hover:bg-indigo-100 transition-colors"
              >
                <p className="text-xs text-indigo-600 font-medium truncate">{item.credential_name || item.credential_id}</p>
                <p className="text-lg font-bold text-indigo-900">{item.usage_count ?? item.count ?? 0}</p>
                <p className="text-xs text-indigo-500">uses</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Idle Credentials Warning */}
      {idleCredentials.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Idle Credentials</h3>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-700 mb-3">
              The following credentials have not been used recently. Consider rotating or removing them.
            </p>
            <div className="space-y-2">
              {idleCredentials.map((cred, idx) => (
                <div key={cred.id || idx} className="flex items-center justify-between p-2 bg-white rounded border border-yellow-100">
                  <div>
                    <span className="text-sm font-medium text-gray-900">{cred.credential_name || cred.api_name || cred.id}</span>
                    {cred.last_used && (
                      <span className="ml-2 text-xs text-gray-500">Last used: {new Date(cred.last_used).toLocaleDateString()}</span>
                    )}
                    {cred.idle_days && (
                      <span className="ml-2 text-xs text-yellow-600">{cred.idle_days} days idle</span>
                    )}
                  </div>
                  <button
                    onClick={() => handleViewDetails(cred.credential_id || cred.id, cred.credential_name || cred.api_name)}
                    className="px-3 py-1 text-xs text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-50"
                  >
                    Details
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Credential Usage Detail */}
      {selectedCredential && (
        <div className="p-4 border border-indigo-200 rounded-lg bg-indigo-50">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-semibold text-indigo-800">
              Usage Details: {selectedCredential.name || selectedCredential.id}
            </h3>
            <button
              onClick={() => { setSelectedCredential(null); setCredentialUsage(null); }}
              className="text-indigo-500 text-xs hover:text-indigo-700"
            >
              Close
            </button>
          </div>
          {detailLoading ? (
            <div className="flex justify-center items-center h-16">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
            </div>
          ) : credentialUsage ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="bg-white rounded p-3">
                <p className="text-xs text-gray-500">Total Uses</p>
                <p className="text-lg font-bold text-gray-900">{credentialUsage.total_uses ?? credentialUsage.usage_count ?? 0}</p>
              </div>
              <div className="bg-white rounded p-3">
                <p className="text-xs text-gray-500">Last Used</p>
                <p className="text-sm font-medium text-gray-900">
                  {credentialUsage.last_used ? new Date(credentialUsage.last_used).toLocaleString() : 'Never'}
                </p>
              </div>
              <div className="bg-white rounded p-3">
                <p className="text-xs text-gray-500">First Used</p>
                <p className="text-sm font-medium text-gray-900">
                  {credentialUsage.first_used ? new Date(credentialUsage.first_used).toLocaleString() : 'N/A'}
                </p>
              </div>
              <div className="bg-white rounded p-3">
                <p className="text-xs text-gray-500">Avg Daily</p>
                <p className="text-lg font-bold text-gray-900">{credentialUsage.avg_daily ?? 'N/A'}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-indigo-600">No usage data available.</p>
          )}
        </div>
      )}
    </div>
  );
};

export default UsageAnalytics;
