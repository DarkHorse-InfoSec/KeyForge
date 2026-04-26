import { useState } from "react";
import GitHubConnect from "./GitHubConnect";

/**
 * FirstRunWizard renders a four-step guided onboarding flow for users with
 * zero credentials. It is rendered by Dashboard.js in place of the empty
 * four-zero metric cards. Once the user has at least one credential, or
 * dismisses the wizard via "Skip for now", Dashboard renders normally.
 *
 * Persistence:
 *   - Dismissal sets localStorage["keyforge_wizard_dismissed"] = "true".
 *   - Once credentials.length > 0, Dashboard does not render this component
 *     at all, so there is nothing to persist on the success path.
 *
 * Props:
 *   - api: shared axios instance (already points at /api).
 *   - onComplete: optional callback invoked when the wizard finishes or the
 *     user skips. Dashboard uses this to refresh its credential list.
 */

const STEP_WELCOME = 1;
const STEP_PROVIDER = 2;
const STEP_GENERATE = 3;
const STEP_DONE = 4;

const PROVIDER_GITHUB = "github";
const PROVIDER_OTHER = "other";

const OTHER_PROVIDER_OPTIONS = [
  { value: "openai", label: "OpenAI" },
  { value: "stripe", label: "Stripe" },
  { value: "supabase", label: "Supabase" },
  { value: "firebase", label: "Firebase" },
  { value: "vercel", label: "Vercel" },
  { value: "anthropic", label: "Anthropic" },
  { value: "other", label: "Other" },
];

const FirstRunWizard = ({ api, onComplete }) => {
  const [step, setStep] = useState(STEP_WELCOME);
  const [provider, setProvider] = useState(null);
  const [otherApiName, setOtherApiName] = useState("");
  const [otherApiKey, setOtherApiKey] = useState("");
  const [otherEnvironment, setOtherEnvironment] = useState("development");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const dismiss = () => {
    try {
      localStorage.setItem("keyforge_wizard_dismissed", "true");
    } catch (e) {
      // localStorage may be unavailable (private mode); proceed regardless.
    }
    if (onComplete) {
      onComplete();
    }
  };

  const finish = () => {
    if (onComplete) {
      onComplete();
    }
  };

  const pickGithub = () => {
    setProvider(PROVIDER_GITHUB);
    setStep(STEP_GENERATE);
  };

  const pickOther = () => {
    setProvider(PROVIDER_OTHER);
    setStep(STEP_GENERATE);
  };

  const submitOtherCredential = async (e) => {
    e.preventDefault();
    setError("");
    if (!otherApiName || !otherApiKey) {
      setError("Pick a provider and paste your credential to continue.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/credentials", {
        api_name: otherApiName,
        api_key: otherApiKey,
        environment: otherEnvironment,
      });
      setStep(STEP_DONE);
    } catch (err) {
      const message =
        err.response?.data?.detail || err.message || "Failed to save credential.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const stepLabel = (n, label) => {
    const isActive = n === step;
    const isDone = n < step;
    const base = "flex items-center gap-2 text-sm";
    const dotBase =
      "w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold";
    let dotColor = "bg-gray-200 text-gray-600";
    if (isActive) {
      dotColor = "bg-indigo-600 text-white";
    } else if (isDone) {
      dotColor = "bg-green-600 text-white";
    }
    return (
      <div key={n} className={base}>
        <span className={`${dotBase} ${dotColor}`} aria-hidden="true">
          {isDone ? (
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="3"
                d="M5 13l4 4L19 7"
              />
            </svg>
          ) : (
            n
          )}
        </span>
        <span
          className={
            isActive ? "font-semibold text-gray-900" : "text-gray-500"
          }
        >
          {label}
        </span>
      </div>
    );
  };

  const skipLink = (
    <button
      type="button"
      onClick={dismiss}
      className="text-xs text-gray-500 hover:text-gray-700 underline"
    >
      Skip for now
    </button>
  );

  return (
    <div
      className="bg-white rounded-lg shadow-md p-8 max-w-3xl mx-auto"
      data-testid="first-run-wizard"
    >
      <div className="flex items-center justify-between mb-8 flex-wrap gap-3">
        {stepLabel(STEP_WELCOME, "Welcome")}
        <div
          className="hidden sm:block flex-1 h-px bg-gray-200 mx-2"
          aria-hidden="true"
        ></div>
        {stepLabel(STEP_PROVIDER, "Provider")}
        <div
          className="hidden sm:block flex-1 h-px bg-gray-200 mx-2"
          aria-hidden="true"
        ></div>
        {stepLabel(STEP_GENERATE, "Generate")}
        <div
          className="hidden sm:block flex-1 h-px bg-gray-200 mx-2"
          aria-hidden="true"
        ></div>
        {stepLabel(STEP_DONE, "Done")}
      </div>

      {step === STEP_WELCOME && (
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">
            Welcome to KeyForge
          </h2>
          <p className="text-gray-700 leading-relaxed mb-6">
            KeyForge is your team's vault for the credentials your apps use to
            talk to other services. We store them encrypted, rotate them on
            schedule, and make it impossible for someone to copy them out of
            your browser. This wizard gets you to your first credential.
          </p>
          <div className="flex justify-between items-center">
            <button
              type="button"
              onClick={() => setStep(STEP_PROVIDER)}
              className="bg-indigo-600 text-white px-5 py-2.5 rounded-md hover:bg-indigo-700 font-medium"
            >
              Continue
            </button>
            {skipLink}
          </div>
        </div>
      )}

      {step === STEP_PROVIDER && (
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">
            Connect a provider
          </h2>
          <p className="text-gray-700 mb-6">
            Pick how you want to bring your first credential into KeyForge.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <button
              type="button"
              onClick={pickGithub}
              data-testid="wizard-tile-github"
              className="text-left p-6 border-2 border-gray-200 rounded-lg hover:border-indigo-500 hover:bg-indigo-50 transition"
            >
              <div className="flex items-center gap-3 mb-2">
                <svg
                  className="w-8 h-8 text-gray-900"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2.19c-3.2.7-3.87-1.36-3.87-1.36-.52-1.33-1.27-1.69-1.27-1.69-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.75 2.69 1.24 3.34.95.1-.74.4-1.24.72-1.53-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.05 0 0 .96-.31 3.15 1.18a10.95 10.95 0 0 1 5.74 0c2.19-1.49 3.15-1.18 3.15-1.18.62 1.59.23 2.76.11 3.05.74.81 1.18 1.84 1.18 3.1 0 4.42-2.69 5.39-5.25 5.68.41.36.78 1.06.78 2.13v3.16c0 .31.21.67.8.56C20.21 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5z" />
                </svg>
                <span className="font-semibold text-gray-900">GitHub</span>
              </div>
              <p className="text-sm text-gray-600">
                Generate a fresh GitHub credential without ever visiting GitHub
                settings.
              </p>
            </button>

            <button
              type="button"
              onClick={pickOther}
              data-testid="wizard-tile-other"
              className="text-left p-6 border-2 border-gray-200 rounded-lg hover:border-indigo-500 hover:bg-indigo-50 transition"
            >
              <div className="flex items-center gap-3 mb-2">
                <svg
                  className="w-8 h-8 text-gray-700"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
                  />
                </svg>
                <span className="font-semibold text-gray-900">
                  Other provider
                </span>
              </div>
              <p className="text-sm text-gray-600">
                I have a credential I already created somewhere else.
              </p>
            </button>
          </div>
          <div className="flex justify-between items-center">
            <button
              type="button"
              onClick={() => setStep(STEP_WELCOME)}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Back
            </button>
            {skipLink}
          </div>
        </div>
      )}

      {step === STEP_GENERATE && provider === PROVIDER_GITHUB && (
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">
            Generate a GitHub credential
          </h2>
          <p className="text-gray-700 mb-6">
            KeyForge installs a GitHub App into your account; you pick a repo;
            KeyForge mints a fine-grained credential KeyForge alone can read.
            You will never see or have to handle the raw token.
          </p>
          <GitHubConnect
            api={api}
            onCredentialMinted={() => setStep(STEP_DONE)}
          />
          <div className="flex justify-between items-center mt-6">
            <button
              type="button"
              onClick={() => setStep(STEP_PROVIDER)}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Back
            </button>
            {skipLink}
          </div>
        </div>
      )}

      {step === STEP_GENERATE && provider === PROVIDER_OTHER && (
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">
            Paste an existing credential
          </h2>
          <p className="text-gray-700 mb-6">
            Pick the provider and paste the credential you already created.
            KeyForge will encrypt it before storing it.
          </p>
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
          <form onSubmit={submitOtherCredential} className="space-y-4">
            <div>
              <label
                htmlFor="wizard-api-name"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Provider
              </label>
              <select
                id="wizard-api-name"
                value={otherApiName}
                onChange={(e) => setOtherApiName(e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Select provider</option>
                {OTHER_PROVIDER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="wizard-api-key"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Credential
              </label>
              <input
                id="wizard-api-key"
                type="password"
                value={otherApiKey}
                onChange={(e) => setOtherApiKey(e.target.value)}
                required
                placeholder="Paste your credential here"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label
                htmlFor="wizard-environment"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Environment
              </label>
              <select
                id="wizard-environment"
                value={otherEnvironment}
                onChange={(e) => setOtherEnvironment(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="development">Development</option>
                <option value="staging">Staging</option>
                <option value="production">Production</option>
              </select>
            </div>
            <div className="flex justify-between items-center pt-2">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setStep(STEP_PROVIDER)}
                  className="text-sm text-gray-600 hover:text-gray-900 px-3 py-2"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="bg-indigo-600 text-white px-5 py-2 rounded-md hover:bg-indigo-700 disabled:opacity-50 font-medium"
                >
                  {submitting ? "Saving..." : "Save credential"}
                </button>
              </div>
              {skipLink}
            </div>
          </form>
        </div>
      )}

      {step === STEP_DONE && (
        <div className="text-center py-6">
          <div className="mx-auto w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mb-4">
            <svg
              className="w-10 h-10 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="3"
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Your first credential is in the vault.
          </h2>
          <p className="text-gray-700 mb-6">
            From here you can rotate it on a schedule, scope it down to a
            single service, or hand it to a teammate without ever exposing the
            raw value.
          </p>
          <button
            type="button"
            onClick={finish}
            className="bg-indigo-600 text-white px-6 py-2.5 rounded-md hover:bg-indigo-700 font-medium"
          >
            Go to dashboard
          </button>
        </div>
      )}
    </div>
  );
};

export default FirstRunWizard;
