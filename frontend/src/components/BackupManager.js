import { useState, useEffect } from "react";

const BackupManager = ({ api }) => {
  const [backups, setBackups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [actionId, setActionId] = useState(null);
  const [actionType, setActionType] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchBackups();
  }, []);

  const fetchBackups = async () => {
    setLoading(true);
    try {
      const response = await api.get('/backup/list');
      setBackups(response.data.backups || response.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load backups.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    setCreating(true);
    setError('');
    setSuccess('');
    try {
      const response = await api.post('/backup/create');
      setSuccess(response.data.message || 'Backup created successfully.');
      fetchBackups();
    } catch (err) {
      setError(err.response?.data?.detail || 'Backup creation failed.');
    } finally {
      setCreating(false);
    }
  };

  const handleVerify = async (id) => {
    setActionId(id);
    setActionType('verify');
    setError('');
    try {
      const response = await api.post(`/backup/verify/${id}`);
      setSuccess(response.data.message || `Backup ${id} verified: ${response.data.valid ? 'Valid' : 'Invalid'}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Verification failed.');
    } finally {
      setActionId(null);
      setActionType('');
    }
  };

  const handleRestore = async (id) => {
    if (!window.confirm('Are you sure you want to restore from this backup? This may overwrite current data.')) return;
    setActionId(id);
    setActionType('restore');
    setError('');
    try {
      const response = await api.post(`/backup/restore/${id}`);
      setSuccess(response.data.message || 'Restore completed successfully.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Restore failed.');
    } finally {
      setActionId(null);
      setActionType('');
    }
  };

  const formatSize = (bytes) => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Backup Manager</h2>
        <button
          onClick={handleCreate}
          disabled={creating}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
        >
          {creating ? 'Creating...' : 'Create Backup'}
        </button>
      </div>

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
      ) : backups.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <p className="text-lg mb-2">No backups found</p>
          <p className="text-sm">Click "Create Backup" to create your first backup.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {backups.map((backup, idx) => (
            <div key={backup.id || idx} className="border dark:border-gray-600 rounded-lg p-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                    {backup.name || backup.filename || `Backup #${backup.id}`}
                  </h3>
                  <div className="flex gap-4 mt-1 text-sm text-gray-500 dark:text-gray-400">
                    <span>Size: {formatSize(backup.size || backup.size_bytes)}</span>
                    <span>Date: {backup.created_at ? new Date(backup.created_at).toLocaleString() : 'N/A'}</span>
                    {backup.collections && (
                      <span>Collections: {Array.isArray(backup.collections) ? backup.collections.join(', ') : backup.collections}</span>
                    )}
                  </div>
                  {backup.status && (
                    <span className={`inline-block mt-2 px-2 py-1 text-xs font-medium rounded-full ${
                      backup.status === 'valid' || backup.status === 'complete'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                    }`}>
                      {backup.status}
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleVerify(backup.id)}
                    disabled={actionId === backup.id}
                    className="px-3 py-1 text-xs text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-50 dark:hover:bg-indigo-900/20 disabled:opacity-50"
                  >
                    {actionId === backup.id && actionType === 'verify' ? 'Verifying...' : 'Verify'}
                  </button>
                  <button
                    onClick={() => handleRestore(backup.id)}
                    disabled={actionId === backup.id}
                    className="px-3 py-1 text-xs text-orange-600 border border-orange-200 rounded hover:bg-orange-50 dark:hover:bg-orange-900/20 disabled:opacity-50"
                  >
                    {actionId === backup.id && actionType === 'restore' ? 'Restoring...' : 'Restore'}
                  </button>
                  {backup.download_url && (
                    <a
                      href={backup.download_url}
                      className="px-3 py-1 text-xs text-gray-600 border border-gray-200 rounded hover:bg-gray-50 dark:hover:bg-gray-700"
                      download
                    >
                      Download
                    </a>
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

export default BackupManager;
