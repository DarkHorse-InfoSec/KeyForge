import { useState, useEffect } from "react";

const SessionManager = ({ api }) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [revoking, setRevoking] = useState(null);
  const [revokingAll, setRevokingAll] = useState(false);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/sessions');
      setSessions(response.data.sessions || response.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load sessions.');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (id) => {
    setRevoking(id);
    setError('');
    setSuccess('');
    try {
      await api.delete(`/sessions/${id}`);
      setSuccess('Session revoked successfully.');
      fetchSessions();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to revoke session.');
    } finally {
      setRevoking(null);
    }
  };

  const handleRevokeAll = async () => {
    if (!window.confirm('Revoke all other sessions? You will remain logged in on this device only.')) return;
    setRevokingAll(true);
    setError('');
    setSuccess('');
    try {
      await api.delete('/sessions');
      setSuccess('All other sessions have been revoked.');
      fetchSessions();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to revoke sessions.');
    } finally {
      setRevokingAll(false);
    }
  };

  const formatTimestamp = (ts) => {
    if (!ts) return '-';
    return new Date(ts).toLocaleString();
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Active Sessions</h2>
        <button
          onClick={handleRevokeAll}
          disabled={revokingAll}
          className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm font-medium disabled:opacity-50"
        >
          {revokingAll ? 'Revoking...' : 'Revoke All Other Sessions'}
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

      {loading ? (
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">No active sessions found</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">IP Address</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User Agent</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Active</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sessions.map((session, idx) => (
                <tr key={session.id || idx} className={session.is_current ? 'bg-indigo-50' : ''}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {session.ip_address || session.ip || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">
                    {session.user_agent || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatTimestamp(session.created_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatTimestamp(session.last_active)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {session.is_current ? (
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800">
                        Current Session
                      </span>
                    ) : (
                      <button
                        onClick={() => handleRevoke(session.id)}
                        disabled={revoking === session.id}
                        className="px-3 py-1 text-xs text-red-600 border border-red-200 rounded hover:bg-red-50 disabled:opacity-50"
                      >
                        {revoking === session.id ? 'Revoking...' : 'Revoke'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default SessionManager;
