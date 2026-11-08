import { useEffect, useRef, useState, type FormEvent } from "react";
import { lichessLoginUrl, loginAuth, registerAuth } from "../../lib/api";

type LoginMode = "login" | "register";

type LoginStatus = {
  tone: "info" | "busy" | "error" | "success";
  message: string;
};

const SIGNED_OUT_QUERY_PARAM = "signedout";

const IDLE_STATUS: LoginStatus = { tone: "info", message: "" };

export function LoginPage({ notice }: { notice?: string }) {
  const [mode, setMode] = useState<LoginMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<LoginStatus>(IDLE_STATUS);
  const [submitting, setSubmitting] = useState(false);
  const [signedOut, setSignedOut] = useState(false);
  const usernameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    usernameRef.current?.focus();
    const params = new URLSearchParams(window.location.search);
    if (params.get(SIGNED_OUT_QUERY_PARAM)) {
      setSignedOut(true);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  const banner = notice ?? (signedOut ? "Signed out. See you at the next game." : undefined);
  const passwordTooShort = mode === "register" && password.length > 0 && password.length < 8;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;
    const nextUsername = username.trim();
    if (!nextUsername || !password) {
      setStatus({ tone: "error", message: "Enter a username and password" });
      return;
    }
    setSubmitting(true);
    setStatus({
      tone: "busy",
      message: mode === "login" ? "Signing in..." : "Creating account...",
    });
    try {
      if (mode === "login") {
        await loginAuth(nextUsername, password);
      } else {
        await registerAuth(nextUsername, password);
      }
      setStatus({ tone: "success", message: "Signed in" });
      window.location.assign("/journal");
    } catch (error) {
      setStatus({
        tone: "error",
        message: error instanceof Error ? error.message : "Sign in failed",
      });
      setSubmitting(false);
    }
  }

  function switchMode(nextMode: LoginMode) {
    setMode(nextMode);
    setStatus(IDLE_STATUS);
  }

  return (
    <main className="login-page">
      <div className="login-shell">
        <div className="login-brand">
          <span className="login-logo-mark" aria-hidden="true">
            <svg viewBox="0 0 200 200" width="26" height="26" aria-hidden="true"><rect width="200" height="200" rx="44" fill="#f6f3ec"/><path d="M 0 200 L 200 0 L 200 200 Z" fill="#dce14e"/><path d="M 60 158 L 150 158 L 150 147 C 150 137 143 130 134 127 C 143 119 148 108 147 98 C 146 88 140 78 132 72 L 126 54 L 118 70 L 100 58 L 102 76 C 92 80 82 88 72 100 L 60 114 C 56 119 56 125 60 129 L 76 139 C 66 144 62 150 60 158 Z" fill="#17201b"/><path d="M 60 158 L 150 158 L 150 147 C 150 137 143 130 134 127 L 60 158 Z" fill="#526159"/><circle cx="120" cy="86" r="4.6" fill="#f6f3ec"/></svg>
          </span>
          <a className="landing-logo login-logo" href="/">
            Swindle
          </a>
        </div>
        <section className="login-card" aria-labelledby="login-heading">
          <header className="login-intro">
            <p className="login-kicker">Chess activity journal</p>
            <h1 id="login-heading">Your games have stories.</h1>
            <p className="login-sub">
              Connect Chess.com or Lichess, import your recent games, and keep the moments that mattered.
            </p>
          </header>
          {banner ? (
            <p className="login-notice" role="status">
              {banner}
            </p>
          ) : null}
          <a className="login-lichess" href={lichessLoginUrl()}>
            Continue with Lichess
          </a>
          <div className="login-divider" role="separator" aria-label="or use a username">
            <span>or</span>
          </div>
          <div className="login-mode-switch" role="tablist" aria-label="Sign in options">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={mode === "login" ? "login-tab is-active" : "login-tab"}
              onClick={() => switchMode("login")}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              className={mode === "register" ? "login-tab is-active" : "login-tab"}
              onClick={() => switchMode("register")}
            >
              Create account
            </button>
          </div>
          <form className="login-form" onSubmit={handleSubmit}>
            <label htmlFor="login-username">Username</label>
            <input
              ref={usernameRef}
              id="login-username"
              name="username"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="your-handle"
            />
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={mode === "login" ? "Your password" : "At least 8 characters"}
              aria-describedby={mode === "register" ? "login-password-hint" : undefined}
            />
            {mode === "register" ? (
              <p
                id="login-password-hint"
                className={passwordTooShort ? "login-hint is-warn" : "login-hint"}
              >
                {passwordTooShort ? "Almost — use at least 8 characters." : "Use at least 8 characters."}
              </p>
            ) : null}
            <button type="submit" className="login-submit" disabled={submitting}>
              {submitting
                ? mode === "login"
                  ? "Signing in..."
                  : "Creating account..."
                : mode === "login"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>
          <p
            className={status.tone === "error" ? "login-status is-error" : "login-status"}
            role={status.tone === "error" ? "alert" : "status"}
            aria-live="polite"
          >
            {status.message}
          </p>
        </section>
        <p className="login-footnote">Sign in once and connect Lichess or Chess.com to import your games.</p>
      </div>
    </main>
  );
}
