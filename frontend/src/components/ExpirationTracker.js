import { useState, useEffect } from "react";

const ExpirationTracker = ({ api }) => {
  const [alerts, setAlerts] = useState([]);
  const [expirations, setExpirations] = useState([]);
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form state
  const [selectedCredential, setSelectedCredential] = useState('');
  const [expirationDate, setExpirationDate] = useState('');
  const [alertDays, setAlertDays] = useState(7);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [alertsRes, expirationsRes, credsRes] = await Promise.allSettled([
        api.get('/expirations/alerts'),
        api.get('/expirations'),
        api.get('/credentials'),
      ]);
      if (alertsRes.status === 'fulfilled') setAlerts(alertsRes.value.data.alerts || alertsRes.value.data || []);
      if (expirationsRes.status === 'fulfilled') setExpirations(expirationsRes.value.data.expirations || expirationsRes.value.data || []);
      if (credsRes.status === 'fulfilled') setCredentials(credsRes.value.data.credentials || credsRes.value.data || []);
    } catch (err) {
      setError('Failed to load expiration data.');
    } finally {
      setLoading(false);
    }
  };

  const handleSetExpiration = async (e) => {
    e.preventDefault();
    if (!selectedCredential || !expirationDate) return;
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await api.post('/expirations', {
        credential_id: selectedCredential,
        expiration_date: expirationDate,
        alert_days: alertDays,
      });
      setSuccess('Expiration set successfully.');
      setSelectedCredential('');
      setExpirationDate('');
      setAlertDays(7);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to set expiration.');
    } finally {
      setSaving(false);
    }
  };

  const getDaysRemaining = (dateStr) => {
    if (!dateStr) return null;
    const diff = new Date(dateStr) - new Date();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  };

  const getDaysColor = (days) => {
    if (days === null) return 'text-gray-500';
    if (days < 0) return 'text-red-700 bg-red-100';
    if (days < 7) return 'text-red-600 bg-red-50';
    if (days < 30) return 'text-yellow-700 bg-yellow-100';
    return 'text-green-700 bg-green-100';
  };

  const getDaysBadge = (days) => {
    if (days === null) return 'N/A';
    if (days < 0) return `Expired ${Math.abs(days)}d ago`;
    if (days === 0) return 'Expires today';
    return `${days}d remaining`;
  };

  const summary = {
    total: expirations.length,
    expired: expirations.filter(e => getDaysRemaining(e.expiration_date) !== null && getDaysRemaining(e.expiration_date) < 0).length,
    expiringSoon: expirations.filter(e => {
      const d = getDaysRemaining(e.expiration_date);
      return d !== null && d >= 0 && d <= 30;
    }).length,
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
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Expiration Tracker</h2>

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
          <p className="text-sm text-indigo-600 font-medium">Total Tracked</p>
          <p className="text-2xl font-bold text-indigo-900">{summary.total}</p>
          <p className="text-xs text-indigo-500">credentials with expirations</p>
        </div>
        <div className="bg-red-50 rounded-lg p-4">
          <p className="text-sm text-red-600 font-medium">Expired</p>
          <p className="text-2xl font-bold text-red-900">{summary.expired}</p>
          <p className="text-xs text-red-500">need immediate attention</p>
        </div>
        <div className="bg-yellow-50 rounded-lg p-4">
          <p className="text-sm text-yellow-600 font-medium">Expiring Soon</p>
          <p className="text-2xl font-bold text-yellow-900">{summary.expiringSoon}</p>
          <p className="text-xs text-yellow-500">within 30 days</p>
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Alerts</h3>
          <div className="space-y-2">
            {alerts.map((alert, idx) => {
              const days = getDaysRemaining(alert.expiration_date);
              return (
                <div key={alert.id || idx} className={`p-3 rounded-lg border text-sm flex items-center justify-between ${days !== null && days < 0 ? 'bg-red-50 border-red-200' : 'bg-yellow-50 border-yellow-200'}`}>
                  <div>
                    <span className="font-medium">{alert.credential_name || alert.credential_id}</span>
                    <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${getDaysColor(days)}`}>
                      {getDaysBadge(days)}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500">{alert.expiration_date}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Set Expiration Form */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Set Expiration</h3>
        <form onSubmit={handleSetExpiration} className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Credential</label>
            <select
              value={selectedCredential}
              onChange={(e) => setSelectedCredential(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="">Select credential...</option>
              {credentials.map(c => (
                <option key={c.id} value={c.id}>{c.api_name || c.name || c.id}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Expiration Date</label>
            <input
              type="date"
              value={expirationDate}
              onChange={(e) => setExpirationDate(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Alert (days before)</label>
            <input
              type="number"
              min="1"
              max="90"
              value={alertDays}
              onChange={(e) => setAlertDays(parseInt(e.target.value) || 7)}
              className="w-20 px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={saving || !selectedCredential || !expirationDate}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Set Expiration'}
          </button>
        </form>
      </div>

      {/* Expirations Table */}
      {expirations.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">No expirations tracked yet</p>
          <p className="text-sm">Use the form above to set credential expirations.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Credential</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Expiration Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Days Remaining</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Alert At</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {expirations.map((exp, idx) => {
                const days = getDaysRemaining(exp.expiration_date);
                return (
                  <tr key={exp.id || idx}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{exp.credential_name || exp.credential_id}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{exp.expiration_date}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs rounded-full ${getDaysColor(days)}`}>
                        {getDaysBadge(days)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">{exp.alert_days || '-'} days before</td>
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

export default ExpirationTracker;
