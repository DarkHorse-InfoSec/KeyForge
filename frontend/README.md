# KeyForge Frontend

The KeyForge frontend is a React 19 single-page application that provides a dashboard for managing API credentials, security settings, team collaboration, and compliance monitoring.

## Tech Stack

- **React 19** with React Router v7
- **Tailwind CSS 3** for styling
- **Axios** for API communication
- **Craco** for webpack configuration overrides
- **Jest + React Testing Library** for component tests
- **ESLint 9** with flat config for linting

## Getting Started

### Prerequisites

- Node.js 20+
- npm or yarn

### Install Dependencies

```bash
npm install
```

### Development Server

```bash
npm start
```

Opens [http://localhost:3000](http://localhost:3000). The app proxies API requests to the backend at `http://localhost:8001`.

### Environment Variables

Create a `.env` file (see `.env.example`):

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm start` | Start development server with hot reload |
| `npm run build` | Build optimized production bundle to `build/` |
| `npm test` | Run Jest tests (via `jest.config.js`) |
| `npx eslint src/` | Lint source files with ESLint |

## Project Structure

```
src/
├── App.js                    # Root component with routing and sidebar navigation
├── api.js                    # Axios instance with JWT interceptors
├── setupTests.js             # Jest/RTL test setup
├── components/
│   ├── AuthScreen.js         # Login and registration
│   ├── Dashboard.js          # Overview stats and health score
│   ├── CredentialManager.js  # CRUD for API credentials
│   ├── AuditLog.js           # Tamper-proof audit trail viewer
│   ├── TeamManager.js        # Team RBAC management
│   ├── MFASetup.js           # TOTP multi-factor authentication
│   ├── SessionManager.js     # Active session tracking
│   ├── SecretScanner.js      # Codebase secret detection
│   ├── RotationTracker.js    # Key rotation policies
│   ├── HealthChecks.js       # Credential validation checks
│   ├── CredentialGroups.js   # Logical credential grouping
│   ├── ImportExport.js       # .env and JSON import/export
│   └── ...                   # 22 components total
└── __tests__/
    ├── App.test.js
    ├── AuthScreen.test.js
    ├── Dashboard.test.js
    ├── CredentialManager.test.js
    └── components.test.js
```

## Testing

```bash
# Run all tests
NODE_ENV=test npx jest --watchAll=false

# Run with coverage
NODE_ENV=test npx jest --coverage

# Run a specific test file
NODE_ENV=test npx jest src/__tests__/Dashboard.test.js
```

51 component tests covering authentication, credential management, dashboard rendering, and smoke tests for all major components.

## Building for Production

```bash
npm run build
```

Generates an optimized production build in the `build/` directory, ready to be served by any static file server or deployed via Docker.
