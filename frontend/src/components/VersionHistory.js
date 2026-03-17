import { useState, useEffect } from "react";

const VersionHistory = ({ api }) => {
  const [credentials, setCredentials] = useState([]);
  const [selectedCredential, setSelectedCredential] = useState('');
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // New version form
  const [showNewVersion, setShowNewVersion] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [changeReason, setChangeReason] = useState('');
  const [creating, setCreating] = useState(false);
  const [rollingBack, setRollingBack] = useState(null);

  useEffect(() => {
    fetchCredentials();
  }, []);

  useEffect(() => {
    if (selectedCredential) {
      fetchVersions(selectedCredential);
    } else {
      setVersions([]);
    }
  }, [selectedCredential]);

  const fetchCredentials = async () => {
    setLoading(true);
    try {
      const response = await api.get('/credentials');
      setCredentials(response.data.credentials || response.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load credentials.');
    } finally {
      setLoading(false);
    }
  };

  const fetchVersions = async (credId) => {
    setVersionsLoading(true);
    setError('');
    try {
      const response = await api.get(`/credentials/${credId}/versions`);
      setVersions(response.data.versions || response.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load version history.');
    } finally {
      setVersionsLoading(false);
    }
  };

  const handleCreateVersion = async (e) => {
    e.preventDefault();
    if (!newKey.trim() || !selectedCredential) return;
    setCreating(true);
    setError('');
    setSuccess('');
    try {
      await api.post(`/credentials/${selectedCredential}/versions`, {
        api_key: newKey.trim(),
        change_reason: changeReason.trim(),
      });
      setSuccess('New version created successfully.');
      setNewKey('');
      setChangeReason('');
      setShowNewVersion(false);
      fetchVersions(selectedCredential);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create new version.');
    } finally {
      setCreating(false);
    }
  };

  const handleRollback = async (versionId) => {
    if (!window.confirm('Roll back to this version? The current key will be replaced.')) return;
    setRollingBack(versionId);
    setError('');
    setSuccess('');
    try {
      await api.post(`/credentials/${selectedCredential}/versions/${versionId}/rollback`);
      setSuccess('Rolled back successfully.');
      fetchVersions(selectedCredential);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to rollback.');
    } finally {
      setRollingBack(null);
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
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Version History</h2>

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

      {/* Credential Selector */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Select Credential</label>
            <select
              value={selectedCredential}
              onChange={(e) => setSelectedCredential(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm min-w-[200px]"
            >
              <option value="">Choose a credential...</option>
              {credentials.map(c => (
                <option key={c.id} value={c.id}>{c.api_name || c.name || c.id}</option>
              ))}
            </select>
          </div>
          {selectedCredential && (
            <button
              onClick={() => setShowNewVersion(!showNewVersion)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm font-medium"
            >
              {showNewVersion ? 'Cancel' : 'Create New Version'}
            </button>
          )}
        </div>
      </div>

      {/* New Version Form */}
      {showNewVersion && selectedCredential && (
        <div className="mb-6 p-4 border border-indigo-200 rounded-lg bg-indigo-50">
          <h3 className="text-sm font-semibold text-indigo-800 mb-3">Create New Version</h3>
          <form onSubmit={handleCreateVersion} className="space-y-3">
            <div>
              <label className="block text-xs text-indigo-600 mb-1">New API Key</label>
              <input
                type="text"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                placeholder="Enter new API key..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-indigo-600 mb-1">Change Reason</label>
              <input
                type="text"
                value={changeReason}
                onChange={(e) => setChangeReason(e.target.value)}
                placeholder="Why is this key being changed?"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={creating || !newKey.trim()}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Create Version'}
            </button>
          </form>
        </div>
      )}

      {/* Version Timeline */}
      {!selectedCredential ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">Select a credential</p>
          <p className="text-sm">Choose a credential above to view its version history.</p>
        </div>
      ) : versionsLoading ? (
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      ) : versions.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">No version history</p>
          <p className="text-sm">This credential has no recorded versions.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {versions.map((version, idx) => (
            <div
              key={version.id || idx}
              className={`p-4 rounded-lg border ${version.is_current ? 'border-indigo-300 bg-indigo-50' : 'border-gray-200 bg-white'}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-sm font-bold">
                    v{version.version || versions.length - idx}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900">
                        {version.masked_key || version.key_preview || '****'}
                      </span>
                      {version.is_current && (
                        <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800">
                          Current
                        </span>
                      )}
                    </div>
                    {version.change_reason && (
                      <p className="text-xs text-gray-500 mt-0.5">{version.change_reason}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400">
                    {version.created_at ? new Date(version.created_at).toLocaleString() : '-'}
                  </span>
                  {!version.is_current && (
                    <button
                      onClick={() => handleRollback(version.id)}
                      disabled={rollingBack === version.id}
                      className="px-3 py-1 text-xs text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-50 disabled:opacity-50"
                    >
                      {rollingBack === version.id ? 'Rolling back...' : 'Rollback'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default VersionHistory;
