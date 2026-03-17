import { useState, useEffect } from "react";

const ComplianceCenter = ({ api }) => {
  const [score, setScore] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportDetail, setReportDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [scoreRes, reportsRes] = await Promise.allSettled([
        api.get('/compliance/score'),
        api.get('/compliance/reports'),
      ]);
      if (scoreRes.status === 'fulfilled') setScore(scoreRes.value.data);
      if (reportsRes.status === 'fulfilled') setReports(reportsRes.value.data.reports || reportsRes.value.data || []);
    } catch (err) {
      setError('Failed to load compliance data.');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async (type) => {
    setGenerating(type);
    setError('');
    setSuccess('');
    try {
      const response = await api.post('/compliance/reports', { type });
      setSuccess(`${type.toUpperCase()} report generated successfully.`);
      setReports(prev => [response.data, ...prev]);
      fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate report.');
    } finally {
      setGenerating(null);
    }
  };

  const handleViewReport = async (reportId) => {
    setSelectedReport(reportId);
    setDetailLoading(true);
    try {
      const response = await api.get(`/compliance/reports/${reportId}`);
      setReportDetail(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load report.');
    } finally {
      setDetailLoading(false);
    }
  };

  const getScoreColor = (val) => {
    if (val === null || val === undefined) return 'text-gray-400';
    if (val >= 80) return 'text-green-600';
    if (val >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBg = (val) => {
    if (val === null || val === undefined) return 'bg-gray-100';
    if (val >= 80) return 'bg-green-50 border-green-200';
    if (val >= 50) return 'bg-yellow-50 border-yellow-200';
    return 'bg-red-50 border-red-200';
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
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Compliance Center</h2>

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

      {/* Compliance Score */}
      {score && (
        <div className="mb-6">
          <div className={`p-6 rounded-lg border ${getScoreBg(score.overall_score ?? score.score)}`}>
            <div className="flex items-center gap-6">
              <div className="flex-shrink-0 text-center">
                <p className={`text-5xl font-bold ${getScoreColor(score.overall_score ?? score.score)}`}>
                  {score.overall_score ?? score.score ?? '--'}
                </p>
                <p className="text-sm text-gray-500 mt-1">/ 100</p>
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 mb-1">Overall Compliance Score</h3>
                <p className="text-sm text-gray-600">
                  {(score.overall_score ?? score.score) >= 80 && 'Your security posture is strong. Keep up the good work.'}
                  {(score.overall_score ?? score.score) >= 50 && (score.overall_score ?? score.score) < 80 && 'There are areas that need improvement. Review the breakdown below.'}
                  {(score.overall_score ?? score.score) < 50 && 'Your compliance score needs attention. Address the issues below.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Score Breakdown */}
      {score?.breakdown && score.breakdown.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Score Breakdown</h3>
          <div className="space-y-2">
            {score.breakdown.map((criterion, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className={`w-2 h-2 rounded-full ${criterion.passed ? 'bg-green-500' : 'bg-red-500'}`}></span>
                  <span className="text-sm text-gray-700">{criterion.name || criterion.criterion}</span>
                </div>
                <div className="flex items-center gap-3">
                  {criterion.score !== undefined && (
                    <span className={`text-sm font-medium ${getScoreColor(criterion.score)}`}>
                      {criterion.score}
                    </span>
                  )}
                  <span className={`px-2 py-0.5 text-xs rounded-full ${criterion.passed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                    {criterion.passed ? 'Pass' : 'Fail'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generate Reports */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Generate Report</h3>
        <div className="flex flex-wrap gap-3">
          {['soc2', 'gdpr', 'general'].map((type) => (
            <button
              key={type}
              onClick={() => handleGenerateReport(type)}
              disabled={generating === type}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
            >
              {generating === type ? 'Generating...' : `Generate ${type.toUpperCase()}`}
            </button>
          ))}
        </div>
      </div>

      {/* Report History */}
      {reports.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Report History</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Generated</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {reports.map((report, idx) => (
                  <tr key={report.id || idx}>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      <span className="px-2 py-1 text-xs rounded-full bg-indigo-100 text-indigo-800 uppercase">
                        {report.type || report.report_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {report.created_at ? new Date(report.created_at).toLocaleString() : '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`text-sm font-medium ${getScoreColor(report.score)}`}>
                        {report.score ?? '-'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <button
                        onClick={() => handleViewReport(report.id)}
                        className="px-3 py-1 text-xs text-indigo-600 border border-indigo-200 rounded hover:bg-indigo-50"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Report Detail */}
      {selectedReport && (
        <div className="p-4 border border-indigo-200 rounded-lg bg-indigo-50">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-sm font-semibold text-indigo-800">Report Detail</h3>
            <button
              onClick={() => { setSelectedReport(null); setReportDetail(null); }}
              className="text-indigo-500 text-xs hover:text-indigo-700"
            >
              Close
            </button>
          </div>
          {detailLoading ? (
            <div className="flex justify-center items-center h-16">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
            </div>
          ) : reportDetail ? (
            <div>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="bg-white rounded p-3">
                  <p className="text-xs text-gray-500">Type</p>
                  <p className="text-sm font-medium text-gray-900 uppercase">{reportDetail.type || reportDetail.report_type}</p>
                </div>
                <div className="bg-white rounded p-3">
                  <p className="text-xs text-gray-500">Score</p>
                  <p className={`text-lg font-bold ${getScoreColor(reportDetail.score)}`}>{reportDetail.score ?? '-'}</p>
                </div>
                <div className="bg-white rounded p-3">
                  <p className="text-xs text-gray-500">Generated</p>
                  <p className="text-sm font-medium text-gray-900">
                    {reportDetail.created_at ? new Date(reportDetail.created_at).toLocaleString() : '-'}
                  </p>
                </div>
              </div>
              {reportDetail.findings && reportDetail.findings.length > 0 && (
                <div>
                  <p className="text-xs text-indigo-600 font-medium mb-2">Findings</p>
                  <div className="space-y-2">
                    {reportDetail.findings.map((finding, idx) => (
                      <div key={idx} className="bg-white rounded p-3 border border-indigo-100">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 text-xs rounded-full ${finding.severity === 'high' ? 'bg-red-100 text-red-800' : finding.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-800'}`}>
                            {finding.severity || 'info'}
                          </span>
                          <span className="text-sm font-medium text-gray-900">{finding.title || finding.name}</span>
                        </div>
                        {finding.description && (
                          <p className="text-xs text-gray-500 mt-1">{finding.description}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {reportDetail.summary && (
                <div className="mt-3 bg-white rounded p-3 border border-indigo-100">
                  <p className="text-xs text-indigo-600 font-medium mb-1">Summary</p>
                  <p className="text-sm text-gray-700">{reportDetail.summary}</p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-indigo-600">No report data available.</p>
          )}
        </div>
      )}
    </div>
  );
};

export default ComplianceCenter;
