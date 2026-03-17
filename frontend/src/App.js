import { useState, useEffect } from "react";
import "./App.css";
import api from "./api";
import Dashboard from "./components/Dashboard";
import ProjectAnalyzer from "./components/ProjectAnalyzer";
import AnalysisResults from "./components/AnalysisResults";
import CredentialManager from "./components/CredentialManager";
import AuthScreen from "./components/AuthScreen";

function App() {
  const [token, setToken] = useState(null);
  const [currentView, setCurrentView] = useState('dashboard');
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
    const storedToken = localStorage.getItem('keyforge_token');
    if (storedToken) {
      setToken(storedToken);
    }
  }, []);

  const handleAuth = (newToken) => {
    localStorage.setItem('keyforge_token', newToken);
    setToken(newToken);
  };

  const handleLogout = () => {
    localStorage.removeItem('keyforge_token');
    setToken(null);
  };

  if (!token) {
    return <AuthScreen api={api} onAuth={handleAuth} />;
  }

  const navigation = [
    { id: 'dashboard', name: 'Dashboard', icon: '\uD83D\uDCCA' },
    { id: 'analyzer', name: 'Project Analyzer', icon: '\uD83D\uDD0D' },
    { id: 'credentials', name: 'Credentials', icon: '\uD83D\uDD10' }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <div className="flex items-center">
                <img
                  src="https://customer-assets.emergentagent.com/job_apiforge-2/artifacts/r0co6pp1_1000006696-removebg-preview.png"
                  alt="KeyForge Logo"
                  className="h-10 w-10 mr-3"
                />
                <div>
                  <h1 className="text-2xl font-bold text-indigo-600">KeyForge</h1>
                  <p className="text-xs text-gray-500 -mt-1">Universal API Infrastructure Assistant</p>
                </div>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-gray-700 font-medium px-3 py-1.5 rounded-md hover:bg-gray-100"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation */}
        <nav className="flex space-x-8 mb-8">
          {navigation.map((item) => (
            <button
              key={item.id}
              onClick={() => setCurrentView(item.id)}
              className={`flex items-center px-3 py-2 rounded-md text-sm font-medium ${
                currentView === item.id
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <span className="mr-2">{item.icon}</span>
              {item.name}
            </button>
          ))}
        </nav>

        {/* Main Content */}
        <main>
          {currentView === 'dashboard' && (
            <div>
              <Dashboard api={api} />
              {analysis && <AnalysisResults analysis={analysis} />}
            </div>
          )}

          {currentView === 'analyzer' && (
            <div>
              <ProjectAnalyzer api={api} onAnalysisComplete={setAnalysis} />
              {analysis && <AnalysisResults analysis={analysis} />}
            </div>
          )}

          {currentView === 'credentials' && <CredentialManager api={api} />}
        </main>
      </div>
    </div>
  );
}

export default App;
