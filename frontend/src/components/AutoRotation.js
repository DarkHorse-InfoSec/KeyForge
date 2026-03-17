import { useState, useEffect } from "react";

const AutoRotation = ({ api }) => {
  const [configs, setConfigs] = useState([]);
  const [providers, setProviders] = useState([]);
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Configure form
  const [showForm, setShowForm] = useState(false);
  const [formCredential, setFormCredential] = useState('');
  const [formInterval, setFormInterval] = useState(30);
  const [formEnabled, setFormEnabled] = useState(true);
  const [saving, setSaving] = useState(false);
  const [triggering, setTriggering] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [configsRes, providersRes, credsRes] = await Promise.allSettled([
        api.get('/auto-rotation'),
        api.get('/auto-rotation/supported-providers'),
        api.get('/credentials'),
      ]);
      if (configsRes.status === 'fulfilled') setConfigs(configsRes.value.data.configs || configsRes.value.data || []);
      if (providersRes.status === 'fulfilled') setProviders(providersRes.value.data.providers || providersRes.value.data || []);
      if (credsRes.status === 'fulfilled') setCredentials(credsRes.value.data.credentials || credsRes.value.data || []);
    } catch (err) {
      setError('Failed to load auto-rotation data.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    if (!formCredential) return;
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await api.post('/auto-rotation', {
        credential_id: formCredential,
        interval_days: formInterval,
        enabled: formEnabled,
      });
      setSuccess('Auto-rotation configured successfully.');
      setShowForm(false);
      setFormCredential('');
      setFormInterval(30);
      setFormEnabled(true);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to configure auto-rotation.');
    } finally {
      setSaving(false);
    }
  };

  const handleTrigger = async (configId) => {
    setTriggering(configId);
    setError('');
    setSuccess('');
    try {
      await api.post(`/auto-rotation/${configId}/trigger`);
      setSuccess('Rotation triggered successfully.');
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to trigger rotation.');
    } finally {
      setTriggering(null);
    }
  };

  const statusBadge = (config) => {
    if (!config.enabled) return { color: 'bg-gray-100 text-gray-800', label: 'Disabled' };
    if (config.overdue) return { color: 'bg-red-100 text-red-800', label: 'Overdue' };
    return { color: 'bg-green-100 text-green-800', label: 'Enabled' };
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
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Auto-Rotation</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm font-medium"
        >
          {showForm ? 'Cancel' : 'Configure New'}
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

      {/* Configure Form */}
      {showForm && (
        <div className="mb-6 p-4 border border-indigo-200 rounded-lg bg-indigo-50">
          <h3 className="text-sm font-semibold text-indigo-800 mb-3">Configure Auto-Rotation</h3>
          <form onSubmit={handleSaveConfig} className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs text-indigo-600 mb-1">Credential</label>
              <select
                value={formCredential}
                onChange={(e) => setFormCredential(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm"
              >
                <option value="">Select credential...</option>
                {credentials.map(c => (
                  <option key={c.id} value={c.id}>{c.api_name || c.name || c.id}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-indigo-600 mb-1">Interval (days)</label>
              <input
                type="number"
                min="1"
                max="365"
                value={formInterval}
                onChange={(e) => setFormInterval(parseInt(e.target.value) || 30)}
                className="w-24 px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formEnabled}
                onChange={(e) => setFormEnabled(e.target.checked)}
                id="autoRotationEnabled"
                className="rounded"
              />
              <label htmlFor="autoRotationEnabled" className="text-sm text-gray-700">Enabled</label>
            </div>
            <button
              type="submit"
              disabled={saving || !formCredential}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </form>
        </div>
      )}

      {/* Supported Providers */}
      {providers.length > 0 && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Supported Providers</h3>
          <div className="flex flex-wrap gap-2">
            {providers.map((provider, idx) => (
              <span key={idx} className="px-3 py-1 text-xs bg-white border border-gray-200 rounded-full text-gray-700">
                {provider.name || provider}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Configs Table */}
      {configs.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">No auto-rotation configurations</p>
          <p className="text-sm">Click "Configure New" to set up automatic key rotation.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Credential</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Interval</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Rotated</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Next Rotation</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {configs.map((config, idx) => {
                const badge = statusBadge(config);
                return (
                  <tr key={config.id || idx}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{config.credential_name || config.credential_id}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{config.interval_days} days</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${badge.color}`}>{badge.label}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {config.last_rotated ? new Date(config.last_rotated).toLocaleString() : 'Never'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {config.next_rotation ? new Date(config.next_rotation).toLocaleString() : '-'}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <button
                        onClick={() => handleTrigger(config.id)}
                        disabled={triggering === config.id}
                        className="px-3 py-1 text-xs text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-50 disabled:opacity-50"
                      >
                        {triggering === config.id ? 'Triggering...' : 'Trigger Now'}
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

export default AutoRotation;
