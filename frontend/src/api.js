import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  withCredentials: true,
});

const MUTATING_METHODS = new Set(["post", "put", "patch", "delete"]);

function readCookie(name) {
  const match = document.cookie.match(
    new RegExp("(?:^|; )" + name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "=([^;]*)")
  );
  return match ? decodeURIComponent(match[1]) : null;
}

// Request interceptor: attach CSRF token on mutating requests
api.interceptors.request.use((config) => {
  const method = (config.method || "get").toLowerCase();
  if (MUTATING_METHODS.has(method)) {
    const csrf = readCookie("keyforge_csrf");
    if (csrf) {
      config.headers["X-CSRF-Token"] = csrf;
    }
  }
  return config;
});

// Auth endpoints legitimately return 401 (probe, bad password) and must not
// trigger the session-expired reload path; the caller handles them directly.
const AUTH_PROBE_PATHS = ["/auth/me", "/auth/login", "/auth/register", "/auth/logout"];

// Response interceptor: on 401 from a session-protected endpoint, clear the
// server cookie and reload so the user is bounced back to AuthScreen.
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status;
    const url = error.config?.url || "";
    const isAuthProbe = AUTH_PROBE_PATHS.some((p) => url === p || url.endsWith(p));
    if (status === 401 && !isAuthProbe) {
      try {
        await axios.post(
          `${BACKEND_URL}/api/auth/logout`,
          {},
          { withCredentials: true }
        );
      } catch (e) {
        // ignore
      }
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

export default api;
