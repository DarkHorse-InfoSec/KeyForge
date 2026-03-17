import { useState } from "react";

const ProjectAnalyzer = ({ api, onAnalysisComplete }) => {
  const [projectName, setProjectName] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [files, setFiles] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleAnalyze = async () => {
    if (!projectName.trim()) return;

    setAnalyzing(true);
    setError('');
    setSuccess('');
    try {
      const response = await api.post('/projects/analyze', {
        project_name: projectName
      });
      onAnalysisComplete(response.data);
      setSuccess(`Project "${projectName}" analyzed successfully! Found ${response.data.detected_apis?.length || 0} APIs.`);
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Failed to analyze project.';
      setError(message);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleFileUpload = async (event) => {
    const selectedFiles = Array.from(event.target.files);
    setFiles(selectedFiles);
    setError('');
    setSuccess('');

    if (selectedFiles.length > 0 && projectName) {
      setAnalyzing(true);
      try {
        // First analyze the project to get its ID
        const analysisResponse = await api.post('/projects/analyze', {
          project_name: projectName
        });

        // Use the actual project ID from the analysis response instead of hardcoded "demo-project"
        const projectId = analysisResponse.data.project_id || analysisResponse.data.id || projectName;

        const formData = new FormData();
        selectedFiles.forEach(file => formData.append('files', file));

        const response = await api.post(`/projects/${projectId}/upload-files`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });

        // Merge uploaded file analysis with project analysis
        const mergedAnalysis = {
          ...analysisResponse.data,
          detected_apis: response.data.detected_apis || analysisResponse.data.detected_apis,
          file_count: response.data.file_count || analysisResponse.data.file_count
        };

        onAnalysisComplete(mergedAnalysis);
        setSuccess(`Files uploaded and analyzed successfully! Found ${mergedAnalysis.detected_apis?.length || 0} APIs.`);
      } catch (err) {
        const message = err.response?.data?.detail || err.message || 'Failed to upload and analyze files.';
        setError(message);
      } finally {
        setAnalyzing(false);
      }
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Project Analysis</h2>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-red-600 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-red-700">{error}</p>
          </div>
          <button onClick={() => setError('')} className="text-red-500 hover:text-red-700 ml-3">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {success && (
        <div className="mb-4 bg-green-50 border border-green-200 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-green-600 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-green-700">{success}</p>
          </div>
          <button onClick={() => setSuccess('')} className="text-green-500 hover:text-green-700 ml-3">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Project Name
          </label>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Enter your project name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Upload Project Files (Optional)
          </label>
          <input
            type="file"
            multiple
            accept=".py,.js,.ts,.jsx,.tsx,.json,.yml,.yaml"
            onChange={handleFileUpload}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          {files.length > 0 && (
            <p className="text-sm text-gray-600 mt-2">{files.length} files selected</p>
          )}
        </div>

        <button
          onClick={handleAnalyze}
          disabled={!projectName.trim() || analyzing}
          className="w-full bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {analyzing ? (
            <div className="flex items-center justify-center">
              <img
                src="https://customer-assets.emergentagent.com/job_apiforge-2/artifacts/r0co6pp1_1000006696-removebg-preview.png"
                alt="KeyForge Logo"
                className="h-4 w-4 animate-pulse mr-2"
              />
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Analyzing Project...
            </div>
          ) : (
            'Analyze Project'
          )}
        </button>
      </div>
    </div>
  );
};

export default ProjectAnalyzer;
