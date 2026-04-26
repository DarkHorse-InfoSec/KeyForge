import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import FirstRunWizard from '../components/FirstRunWizard';

describe('FirstRunWizard', () => {
  let mockApi;
  let mockOnComplete;
  let storage;

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

    // Reset the URL so GitHubConnect's connected/error effect does not fire.
    window.history.replaceState({}, '', '/');

    mockOnComplete = jest.fn();
    mockApi = {
      get: jest.fn().mockImplementation((url) => {
        if (url === '/issuers/github/installations') {
          return Promise.resolve({ data: { installations: [] } });
        }
        return Promise.resolve({ data: {} });
      }),
      post: jest.fn().mockResolvedValue({ data: {} }),
      put: jest.fn().mockResolvedValue({ data: {} }),
      delete: jest.fn().mockResolvedValue({ data: {} }),
    };
  });

  test('renders welcome step on initial mount', () => {
    render(<FirstRunWizard api={mockApi} onComplete={mockOnComplete} />);
    expect(screen.getByText('Welcome to KeyForge')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Continue$/i })).toBeInTheDocument();
    // The headings for later steps should not be visible yet.
    expect(screen.queryByText('Connect a provider')).not.toBeInTheDocument();
  });

  test('clicking Continue advances to step 2 (provider picker)', () => {
    render(<FirstRunWizard api={mockApi} onComplete={mockOnComplete} />);

    fireEvent.click(screen.getByRole('button', { name: /^Continue$/i }));

    expect(screen.getByText('Connect a provider')).toBeInTheDocument();
    // Both tiles are present.
    expect(screen.getByTestId('wizard-tile-github')).toBeInTheDocument();
    expect(screen.getByTestId('wizard-tile-other')).toBeInTheDocument();
  });

  test('picking "Other provider" jumps to step 3 with the bare key form', () => {
    render(<FirstRunWizard api={mockApi} onComplete={mockOnComplete} />);

    fireEvent.click(screen.getByRole('button', { name: /^Continue$/i }));
    fireEvent.click(screen.getByTestId('wizard-tile-other'));

    expect(screen.getByText('Paste an existing credential')).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText('Paste your credential here')
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Provider')).toBeInTheDocument();
    expect(screen.getByLabelText('Environment')).toBeInTheDocument();
  });

  test('picking "GitHub" then clicking Connect GitHub calls /issuers/github/start', async () => {
    mockApi.post.mockResolvedValueOnce({
      data: { install_url: 'https://github.com/apps/keyforge-test/installations/new' },
    });
    const originalOpen = window.open;
    window.open = jest.fn();

    try {
      render(<FirstRunWizard api={mockApi} onComplete={mockOnComplete} />);

      fireEvent.click(screen.getByRole('button', { name: /^Continue$/i }));
      fireEvent.click(screen.getByTestId('wizard-tile-github'));

      // Wait until GitHubConnect finishes loading and renders the Connect button.
      const connectBtn = await screen.findByRole('button', {
        name: /connect github/i,
      });
      fireEvent.click(connectBtn);

      await waitFor(() => {
        expect(mockApi.post).toHaveBeenCalledWith('/issuers/github/start');
      });
    } finally {
      window.open = originalOpen;
    }
  });

  test('clicking "Skip for now" sets keyforge_wizard_dismissed and calls onComplete', () => {
    render(<FirstRunWizard api={mockApi} onComplete={mockOnComplete} />);

    fireEvent.click(screen.getByText(/Skip for now/i));

    expect(window.localStorage.setItem).toHaveBeenCalledWith(
      'keyforge_wizard_dismissed',
      'true'
    );
    expect(mockOnComplete).toHaveBeenCalledTimes(1);
  });
});
