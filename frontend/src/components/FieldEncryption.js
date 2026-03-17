import { useState, useEffect } from "react";

const FieldEncryption = ({ api }) => {
  const [status, setStatus] = useState([]);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionCollection, setActionCollection] = useState(null);
  const [actionType, setActionType] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statusRes, configRes] = await Promise.all([
        api.get('/encryption/fields/status'),
        api.get('/encryption/fields/config'),
      ]);
      setStatus(statusRes.data.collections || statusRes.data || []);
      setConfig(configRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load field encryption data.');
    } finally {
      setLoading(false);
    }
  };

  const handleEncrypt = async (collection) => {
    setActionCollection(collection);
    setActionType('encrypt');
    setError('');
    setSuccess('');
    try {
      const response = await api.post('/encryption/fields/encrypt-collection', { collection });
      setSuccess(response.data.message || `Collection "${collection}" encrypted successfully.`);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Encryption failed.');
    } finally {
      setActionCollection(null);
      setActionType('');
    }
  };

  const handleDecrypt = async (collection) => {
    if (!window.confirm(`Are you sure you want to decrypt collection "${collection}"?`)) return;
    setActionCollection(collection);
    setActionType('decrypt');
    setError('');
    setSuccess('');
    try {
      const response = await api.post('/encryption/fields/decrypt-collection', { collection });
      setSuccess(response.data.message || `Collection "${collection}" decrypted successfully.`);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Decryption failed.');
    } finally {
      setActionCollection(null);
      setActionType('');
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Field Encryption</h2>

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
          {/* Config */}
          {config && (
            <div className="mb-6 bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Current Configuration</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                {config.algorithm && (
                  <>
                    <span className="text-gray-500 dark:text-gray-400">Algorithm:</span>
                    <span className="text-gray-900 dark:text-gray-100">{config.algorithm}</span>
                  </>
                )}
                {config.key_derivation && (
                  <>
                    <span className="text-gray-500 dark:text-gray-400">Key Derivation:</span>
                    <span className="text-gray-900 dark:text-gray-100">{config.key_derivation}</span>
                  </>
                )}
                {config.enabled !== undefined && (
                  <>
                    <span className="text-gray-500 dark:text-gray-400">Status:</span>
                    <span className={`font-medium ${config.enabled ? 'text-green-600' : 'text-gray-500'}`}>
                      {config.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Collection Status */}
          <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-3">Encryption Status by Collection</h3>
          {status.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <p>No collections found.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {status.map((col, idx) => {
                const pct = col.percentage ?? (col.total_fields > 0 ? Math.round((col.encrypted_count / col.total_fields) * 100) : 0);
                return (
                  <div key={col.collection || idx} className="border dark:border-gray-600 rounded-lg p-4">
                    <div className="flex justify-between items-center mb-2">
                      <h4 className="font-semibold text-gray-900 dark:text-gray-100">{col.collection || col.name}</h4>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEncrypt(col.collection || col.name)}
                          disabled={actionCollection === (col.collection || col.name)}
                          className="px-3 py-1 text-xs text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-50 dark:hover:bg-indigo-900/20 disabled:opacity-50"
                        >
                          {actionCollection === (col.collection || col.name) && actionType === 'encrypt' ? 'Encrypting...' : 'Encrypt'}
                        </button>
                        <button
                          onClick={() => handleDecrypt(col.collection || col.name)}
                          disabled={actionCollection === (col.collection || col.name)}
                          className="px-3 py-1 text-xs text-orange-600 border border-orange-200 rounded hover:bg-orange-50 dark:hover:bg-orange-900/20 disabled:opacity-50"
                        >
                          {actionCollection === (col.collection || col.name) && actionType === 'decrypt' ? 'Decrypting...' : 'Decrypt'}
                        </button>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div
                          className="bg-indigo-600 h-2 rounded-full transition-all"
                          style={{ width: `${pct}%` }}
                        ></div>
                      </div>
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 w-12 text-right">{pct}%</span>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {col.encrypted_count ?? 0} of {col.total_fields ?? 0} fields encrypted
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FieldEncryption;
