import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import Dashboard from '../components/Dashboard';

describe('Dashboard', () => {
  let mockApi;
  let storage;

  // Helper to build a get() that matches both /dashboard/overview and /credentials.
  const makeGet = ({ overview, credentials, overviewError, credsError }) =>
    jest.fn((url) => {
      if (url === '/dashboard/overview') {
        if (overviewError) {
          return Promise.reject(overviewError);
        }
        return Promise.resolve({ data: overview });
      }
      if (url === '/credentials') {
        if (credsError) {
          return Promise.reject(credsError);
        }
        return Promise.resolve({ data: credentials || [] });
      }
      if (url === '/issuers/github/installations') {
        return Promise.resolve({ data: { installations: [] } });
      }
      return Promise.resolve({ data: {} });
    });

  beforeEach(() => {
    jest.clearAllMocks();

    storage = {};
    const localStorageMock = {
      getItem: jest.fn((k) => (k in storage ? storage[k] : null)),
      setItem: jest.fn((k, v) => {
        storage[k] = String(v);
      }),
      removeItem: jest.fn((k) => {
        delete storage[k];
      }),
      clear: jest.fn(() => {
        storage = {};
      }),
    };
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true,
      configurable: true,
    });

    mockApi = {
      get: jest.fn(),
      post: jest.fn().mockResolvedValue({ data: {} }),
      put: jest.fn().mockResolvedValue({ data: {} }),
      delete: jest.fn().mockResolvedValue({ data: {} }),
    };
  });

  // Sample non-empty credential list used to keep the metric-card path active.
  const sampleCredentials = [
    { id: 'c1', api_name: 'openai', status: 'active', environment: 'production' },
  ];

  test('renders loading state initially', () => {
    mockApi.get.mockReturnValue(new Promise(() => {})); // Never resolves
    render(<Dashboard api={mockApi} />);
    expect(screen.getByText('Loading dashboard...')).toBeInTheDocument();
  });

  test('displays stats after loading', async () => {
    mockApi.get = makeGet({
      overview: {
        total_credentials: 12,
        status_breakdown: {
          active: 8,
          invalid: 2,
          expired: 1,
        },
        health_score: 85,
      },
      credentials: sampleCredentials,
    });

    render(<Dashboard api={mockApi} />);

    await waitFor(() => {
      expect(screen.getByText('12')).toBeInTheDocument();
    });
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument(); // 2 invalid + 1 expired
    expect(screen.getByText('Total Credentials')).toBeInTheDocument();
    expect(screen.getByText('Active APIs')).toBeInTheDocument();
    expect(screen.getByText('Health Score')).toBeInTheDocument();
    expect(screen.getByText('Issues')).toBeInTheDocument();
  });

  test('shows error state on API failure', async () => {
    mockApi.get = makeGet({
      overviewError: { response: { data: { detail: 'Server error occurred' } } },
      credentials: sampleCredentials,
    });

    render(<Dashboard api={mockApi} />);

    await waitFor(() => {
      expect(screen.getByText('Server error occurred')).toBeInTheDocument();
    });
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  test('shows generic error message when no detail provided', async () => {
    mockApi.get = makeGet({
      overviewError: new Error('Network Error'),
      credentials: sampleCredentials,
    });

    render(<Dashboard api={mockApi} />);

    await waitFor(() => {
      expect(screen.getByText('Network Error')).toBeInTheDocument();
    });
  });

  test('retry button works after error', async () => {
    let firstCall = true;
    mockApi.get = jest.fn((url) => {
      if (url === '/dashboard/overview') {
        if (firstCall) {
          firstCall = false;
          return Promise.reject({
            response: { data: { detail: 'Temporary failure' } },
          });
        }
        return Promise.resolve({
          data: {
            total_credentials: 5,
            status_breakdown: { active: 3, invalid: 1, expired: 0 },
            health_score: 90,
          },
        });
      }
      if (url === '/credentials') {
        return Promise.resolve({ data: sampleCredentials });
      }
      return Promise.resolve({ data: {} });
    });

    render(<Dashboard api={mockApi} />);

    await waitFor(() => {
      expect(screen.getByText('Temporary failure')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Retry'));

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument();
    });
    expect(screen.getByText('90%')).toBeInTheDocument();
  });

  test('calls /dashboard/overview endpoint on mount', () => {
    mockApi.get.mockReturnValue(new Promise(() => {}));
    render(<Dashboard api={mockApi} />);
    expect(mockApi.get).toHaveBeenCalledWith('/dashboard/overview');
  });

  test('renders FirstRunWizard when there are no credentials', async () => {
    mockApi.get = makeGet({
      overview: {
        total_credentials: 0,
        status_breakdown: { active: 0, invalid: 0, expired: 0 },
        health_score: 0,
      },
      credentials: [],
    });

    render(<Dashboard api={mockApi} />);

    await waitFor(() => {
      expect(screen.getByText('Welcome to KeyForge')).toBeInTheDocument();
    });
    // The metric cards should NOT render in this path.
    expect(screen.queryByText('Total Credentials')).not.toBeInTheDocument();
  });

  test('does not render the wizard when it has been dismissed previously', async () => {
    storage['keyforge_wizard_dismissed'] = 'true';

    mockApi.get = makeGet({
      overview: {
        total_credentials: 0,
        status_breakdown: { active: 0, invalid: 0, expired: 0 },
        health_score: 0,
      },
      credentials: [],
    });

    render(<Dashboard api={mockApi} />);

    await waitFor(() => {
      expect(screen.getByText('Total Credentials')).toBeInTheDocument();
    });
    expect(screen.queryByText('Welcome to KeyForge')).not.toBeInTheDocument();
  });
});
