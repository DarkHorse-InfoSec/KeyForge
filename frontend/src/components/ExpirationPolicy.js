import { useState, useEffect } from "react";

const ExpirationPolicy = ({ api }) => {
  const [policy, setPolicy] = useState(null);
  const [violations, setViolations] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionId, setActionId] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editPolicy, setEditPolicy] = useState(null);

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [policyRes, violationsRes, summaryRes] = await Promise.all([
        api.get('/policies/expiration/policy'),
        api.get('/policies/expiration/violations'),
        api.get('/policies/expiration/summary'),
      ]);
      setPolicy(policyRes.data);
      setEditPolicy(policyRes.data);
      setViolations(violationsRes.data.violations || violationsRes.data || []);
      setSummary(summaryRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load expiration policy data.');
    } finally {
      setLoading(false);
    }
  };

  const handleSavePolicy = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      const response = await api.put('/policies/expiration/policy', editPolicy);
      setPolicy(response.data);
      setSuccess('Expiration policy updated successfully.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update policy.');
    } finally {
      setSaving(false);
    }
  };

  const handleExempt = async (credentialId) => {
    setActionId(credentialId);
    setError('');
    try {
      await api.post(`/policies/expiration/exempt/${credentialId}`);
      setSuccess('Credential exempted.');
      fetchAll();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to exempt credential.');
    } finally {
      setActionId(null);
    }
  };

  const handleEnforce = async (credentialId) => {
    setActionId(credentialId);
    setError('');
    try {
      await api.post(`/policies/expiration/enforce/${credentialId}`);
      setSuccess('Policy enforced for credential.');
      fetchAll();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to enforce policy.');
    } finally {
      setActionId(null);
    }
  };

  const severityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      case 'high': return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400';
      case 'medium': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      case 'low': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-600 dark:text-gray-300';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Expiration Policy</h2>

      {error && (
        <div className="mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-center justify-between">
          <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
          <button onClick={() => setError('')} className="text-red-500 text-xs">Dismiss</button>
        </div>
      )}

      {success && (
        <div className="mb-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 flex items-center justify-between">
          <p className="text-sm text-green-700 dark:text-green-400">{success}</p>
          <button onClick={() => setSuccess('')} className="text-green-500 text-xs">Dismiss</button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      ) : (
        <div>
          {/* Summary Stats */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4">
                <p className="text-sm text-indigo-600 dark:text-indigo-400 font-medium">Total Credentials</p>
                <p className="text-2xl font-bold text-indigo-900 dark:text-indigo-200">{summary.total_credentials ?? 0}</p>
              </div>
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                <p className="text-sm text-red-600 dark:text-red-400 font-medium">Expired</p>
                <p className="text-2xl font-bold text-red-900 dark:text-red-200">{summary.expired ?? 0}</p>
              </div>
              <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-4">
                <p className="text-sm text-yellow-600 dark:text-yellow-400 font-medium">Expiring Soon</p>
                <p className="text-2xl font-bold text-yellow-900 dark:text-yellow-200">{summary.expiring_soon ?? 0}</p>
              </div>
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                <p className="text-sm text-green-600 dark:text-green-400 font-medium">Compliant</p>
                <p className="text-2xl font-bold text-green-900 dark:text-green-200">{summary.compliant ?? 0}</p>
              </div>
            </div>
          )}

          {/* Policy Config */}
          {editPolicy && (
            <div className="mb-6 bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">Policy Configuration</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Mode</label>
                  <select
                    value={editPolicy.mode || 'warn'}
                    onChange={(e) => setEditPolicy({ ...editPolicy, mode: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  >
                    <option value="warn">Warn</option>
                    <option value="block">Block</option>
                    <option value="grace">Grace Period</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Grace Period (days)</label>
                  <input
                    type="number"
                    value={editPolicy.grace_period_days ?? editPolicy.grace_period ?? 7}
                    onChange={(e) => setEditPolicy({ ...editPolicy, grace_period_days: parseInt(e.target.value, 10) })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    min="0"
                    disabled={editPolicy.mode !== 'grace'}
                  />
                </div>
                <div className="flex items-end">
                  <button
                    onClick={handleSavePolicy}
                    disabled={saving}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save Policy'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Violations List */}
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">Violations</h3>
          {violations.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <p>No policy violations found.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Credential</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Severity</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Reason</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Expires</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {violations.map((v, idx) => (
                    <tr key={v.id || v.credential_id || idx}>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-gray-100">
                        {v.credential_name || v.credential_id}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${severityColor(v.severity)}`}>
                          {v.severity || 'Unknown'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {v.reason || v.message || 'Policy violation'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {v.expires_at ? new Date(v.expires_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleExempt(v.credential_id || v.id)}
                            disabled={actionId === (v.credential_id || v.id)}
                            className="px-3 py-1 text-xs text-yellow-600 border border-yellow-200 rounded hover:bg-yellow-50 dark:hover:bg-yellow-900/20 disabled:opacity-50"
                          >
                            Exempt
                          </button>
                          <button
                            onClick={() => handleEnforce(v.credential_id || v.id)}
                            disabled={actionId === (v.credential_id || v.id)}
                            className="px-3 py-1 text-xs text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-50 dark:hover:bg-indigo-900/20 disabled:opacity-50"
                          >
                            Enforce
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ExpirationPolicy;
