import { useState, useEffect } from "react";

const CredentialPermissions = ({ api }) => {
  const [activeTab, setActiveTab] = useState('shared-with-me');
  const [sharedWithMe, setSharedWithMe] = useState([]);
  const [myShares, setMyShares] = useState([]);
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Grant form
  const [grantCredential, setGrantCredential] = useState('');
  const [grantUsername, setGrantUsername] = useState('');
  const [grantPermission, setGrantPermission] = useState('read');
  const [granting, setGranting] = useState(false);
  const [revoking, setRevoking] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sharedRes, mySharesRes, credsRes] = await Promise.allSettled([
        api.get('/permissions/shared-with-me'),
        api.get('/permissions/my-shares'),
        api.get('/credentials'),
      ]);
      if (sharedRes.status === 'fulfilled') setSharedWithMe(sharedRes.value.data.permissions || sharedRes.value.data || []);
      if (mySharesRes.status === 'fulfilled') setMyShares(mySharesRes.value.data.permissions || mySharesRes.value.data || []);
      if (credsRes.status === 'fulfilled') setCredentials(credsRes.value.data.credentials || credsRes.value.data || []);
    } catch (err) {
      setError('Failed to load permissions data.');
    } finally {
      setLoading(false);
    }
  };

  const handleGrant = async (e) => {
    e.preventDefault();
    if (!grantCredential || !grantUsername.trim()) return;
    setGranting(true);
    setError('');
    setSuccess('');
    try {
      await api.post('/permissions', {
        credential_id: grantCredential,
        username: grantUsername.trim(),
        permission: grantPermission,
      });
      setSuccess('Permission granted successfully.');
      setGrantCredential('');
      setGrantUsername('');
      setGrantPermission('read');
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to grant permission.');
    } finally {
      setGranting(false);
    }
  };

  const handleRevoke = async (id) => {
    setRevoking(id);
    setError('');
    setSuccess('');
    try {
      await api.delete(`/permissions/${id}`);
      setSuccess('Permission revoked.');
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to revoke permission.');
    } finally {
      setRevoking(null);
    }
  };

  const permissionColor = (level) => {
    switch (level) {
      case 'admin': return 'bg-purple-100 text-purple-800';
      case 'manage': return 'bg-blue-100 text-blue-800';
      case 'use': return 'bg-green-100 text-green-800';
      case 'read': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Credential Permissions</h2>

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

      {/* Grant Permission Form */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Grant Permission</h3>
        <form onSubmit={handleGrant} className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Credential</label>
            <select
              value={grantCredential}
              onChange={(e) => setGrantCredential(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="">Select credential...</option>
              {credentials.map(c => (
                <option key={c.id} value={c.id}>{c.api_name || c.name || c.id}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Username</label>
            <input
              type="text"
              value={grantUsername}
              onChange={(e) => setGrantUsername(e.target.value)}
              placeholder="username"
              className="px-3 py-2 border border-gray-300 rounded-md text-sm w-40"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Permission Level</label>
            <select
              value={grantPermission}
              onChange={(e) => setGrantPermission(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
            >
              <option value="read">Read</option>
              <option value="use">Use</option>
              <option value="manage">Manage</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={granting || !grantCredential || !grantUsername.trim()}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
          >
            {granting ? 'Granting...' : 'Grant'}
          </button>
        </form>
      </div>

      {/* Tabs */}
      <div className="flex space-x-4 mb-6 border-b">
        <button
          onClick={() => setActiveTab('shared-with-me')}
          className={`pb-2 text-sm font-medium border-b-2 ${activeTab === 'shared-with-me' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500'}`}
        >
          Shared With Me
        </button>
        <button
          onClick={() => setActiveTab('my-shares')}
          className={`pb-2 text-sm font-medium border-b-2 ${activeTab === 'my-shares' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-500'}`}
        >
          My Shares
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        </div>
      ) : activeTab === 'shared-with-me' ? (
        sharedWithMe.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg mb-2">No credentials shared with you</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Credential</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Shared By</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Permission</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Granted</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sharedWithMe.map((perm, idx) => (
                  <tr key={perm.id || idx}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{perm.credential_name || perm.credential_id}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{perm.shared_by || perm.owner}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${permissionColor(perm.permission)}`}>
                        {perm.permission}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {perm.created_at ? new Date(perm.created_at).toLocaleString() : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : (
        myShares.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg mb-2">You haven't shared any credentials</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Credential</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Shared With</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Permission</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {myShares.map((perm, idx) => (
                  <tr key={perm.id || idx}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{perm.credential_name || perm.credential_id}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{perm.shared_with || perm.username}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${permissionColor(perm.permission)}`}>
                        {perm.permission}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <button
                        onClick={() => handleRevoke(perm.id)}
                        disabled={revoking === perm.id}
                        className="px-3 py-1 text-xs text-red-600 border border-red-200 rounded hover:bg-red-50 disabled:opacity-50"
                      >
                        {revoking === perm.id ? 'Revoking...' : 'Revoke'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
};

export default CredentialPermissions;
