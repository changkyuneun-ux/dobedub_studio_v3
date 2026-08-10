import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { apiClient, HealthResponse } from "./api/client";
import { routeFromLocation, routePath, StudioRoute } from "./router";
// E-01: User/AuthSession types and permission helpers moved to ./auth so
// components/AppShell.tsx can use them without importing this entry file.
import { User, AuthSession, canUse } from "./auth";
import "./styles.css";
import { serviceStatusLabel, qwenStatusLabel } from "./helpers/format";
import { canUseAdminConsole } from "./helpers/adminForms";
import { SESSION_USER_STORAGE_KEY, loadSessionUser, clearLoginSession } from "./auth-session";
import { StudioShell } from "./StudioShell";

function App() {
  const initialUser = useMemo(() => loadSessionUser(), []);
  const [user, setUser] = useState<User | null>(() => initialUser);
  const [route, setRoute] = useState<StudioRoute>(() => routeFromLocation(window.location.pathname, Boolean(initialUser)));
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState("");

  useEffect(() => {
    let active = true;
    apiClient
      .health()
      .then((value) => {
        if (active) {
          setHealth(value);
          setHealthError("");
        }
      })
      .catch((error: Error) => {
        if (active) {
          setHealthError(error.message);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const nextRoute = routeFromLocation(window.location.pathname, Boolean(user));
    if (!user && window.location.pathname !== routePath("access.login")) {
      navigate("access.login", true);
    } else if (nextRoute !== route) {
      setRoute(nextRoute);
    }
  }, [route, user]);

  useEffect(() => {
    function syncRouteFromHistory() {
      setRoute(routeFromLocation(window.location.pathname, Boolean(user)));
    }
    window.addEventListener("popstate", syncRouteFromHistory);
    return () => window.removeEventListener("popstate", syncRouteFromHistory);
  }, [user]);

  useEffect(() => {
    function clearSessionOnPageExit() {
      clearLoginSession();
    }
    window.addEventListener("pagehide", clearSessionOnPageExit);
    window.addEventListener("beforeunload", clearSessionOnPageExit);
    return () => {
      window.removeEventListener("pagehide", clearSessionOnPageExit);
      window.removeEventListener("beforeunload", clearSessionOnPageExit);
    };
  }, []);

  useEffect(() => {
    if (!user) {
      return;
    }
    let active = true;
    async function refreshSessionPermissions() {
      try {
        const response = await apiClient.currentSession();
        if (!active || !response.user) {
          return;
        }
        const raw = sessionStorage.getItem(SESSION_USER_STORAGE_KEY);
        const currentSession = raw ? JSON.parse(raw) as AuthSession : null;
        if (!currentSession?.accessToken) {
          return;
        }
        const nextSession = { ...currentSession, user: response.user };
        sessionStorage.setItem(SESSION_USER_STORAGE_KEY, JSON.stringify(nextSession));
        setUser(response.user);
      } catch {
        // A temporary refresh failure must not discard an otherwise valid session.
      }
    }
    function refreshOnVisible() {
      if (document.visibilityState === "visible") {
        void refreshSessionPermissions();
      }
    }
    void refreshSessionPermissions();
    window.addEventListener("focus", refreshSessionPermissions);
    document.addEventListener("visibilitychange", refreshOnVisible);
    return () => {
      active = false;
      window.removeEventListener("focus", refreshSessionPermissions);
      document.removeEventListener("visibilitychange", refreshOnVisible);
    };
  }, [user?.id]);

  function handleLogin(nextSession: AuthSession) {
    clearLoginSession();
    sessionStorage.setItem(SESSION_USER_STORAGE_KEY, JSON.stringify(nextSession));
    setUser(nextSession.user);
    // 로그인 직후 랜딩은 구버전 전체 워크스페이스가 아니라 신규 S1(2a) 화면이다.
    // E-02: design_handoff 2 Create.dc.html 흐름의 실제 첫 단계.
    navigate("create.load");
  }

  function handleLogout() {
    clearLoginSession();
    setUser(null);
    setRoute("access.login");
    window.location.replace(routePath("access.login"));
  }

  function navigate(nextRoute: StudioRoute, replace = false) {
    setRoute(nextRoute);
    const path = routePath(nextRoute);
    if (window.location.pathname === path) {
      return;
    }
    if (replace) {
      window.history.replaceState(null, "", path);
    } else {
      window.history.pushState(null, "", path);
    }
  }

  return (
    <div className="app-shell">
      <TopBar
        user={user}
        health={health}
        healthError={healthError}
        onLogout={handleLogout}
        route={route}
        onNavigate={navigate}
      />
      {user && route !== "access.login" ? (
        <StudioShell
          user={user}
          health={health}
          route={route}
          onNavigate={navigate}
        />
      ) : <LoginView onLogin={handleLogin} />}
    </div>
  );
}

function TopBar({
  user,
  health,
  healthError,
  onLogout,
  route,
  onNavigate
}: {
  user: User | null;
  health: HealthResponse | null;
  healthError: string;
  onLogout: () => void;
  route: StudioRoute;
  onNavigate: (route: StudioRoute) => void;
}) {
  const system = health?.system || health?.legacy;
  const comfyStatus = serviceStatusLabel(Boolean(system?.runpod?.configured), healthError, system?.dryRun ? "DRY-RUN" : undefined);
  const qwenStatus = qwenStatusLabel(system?.promptLlm, healthError);
  return (
    <header className="topbar">
      <div className="brand">
        <img className="brand-mark" src="/studio/favicon.png" alt="" aria-hidden="true" />
        <span>DOBEDUB STUDIO</span>
      </div>
      <nav className="toolbar" aria-label="주요 메뉴">
        <button className={["create.load", "create.prompt", "create.segments", "create.confirm", "create.progress", "create.result"].includes(route) ? "is-active" : ""} type="button" onClick={() => onNavigate("create.load")}>Workspace</button>
        {canUse(user, "history:read") ? <button className={route === "review.history" ? "is-active" : ""} type="button" onClick={() => onNavigate("review.history")}>Task History</button> : null}
        {canUse(user, "history:read") ? <button className={route === "review.assets" ? "is-active" : ""} type="button" onClick={() => onNavigate("review.assets")}>Assets</button> : null}
        {canUse(user, "system:read") ? <button className={route === "admin.status" ? "is-active" : ""} type="button" onClick={() => onNavigate("admin.status")}>Check Status</button> : null}
        {canUse(user, "metadata:read") ? <button className={route === "admin.metadata" ? "is-active" : ""} type="button" onClick={() => onNavigate("admin.metadata")}>Metadata View</button> : null}
        {canUse(user, "manual:read") ? <button className={route === "access.manual" ? "is-active" : ""} type="button" onClick={() => onNavigate("access.manual")}>User Manual</button> : null}
        {canUse(user, "prompts:build") ? <button className={route === "admin.systemPrompt" ? "is-active" : ""} type="button" onClick={() => onNavigate("admin.systemPrompt")}>System Prompt</button> : null}
        {canUseAdminConsole(user) ? <button className={route === "admin.roles" ? "is-active" : ""} type="button" onClick={() => onNavigate("admin.roles")}>Admin</button> : null}
      </nav>
      <div className="service-status-group" aria-label="API 서버 상태">
        <div className={`status-pill ${comfyStatus.toLowerCase()}`}>ComfyUI: <strong>{comfyStatus}</strong><span /></div>
        <div className={`status-pill ${qwenStatus.toLowerCase()}`}>Qwen: <strong>{qwenStatus}</strong><span /></div>
      </div>
      {user ? (
        <div className="user-chip">
          <span>User: <strong>{user.name || user.id}</strong></span>
          <button type="button" onClick={onLogout}>로그아웃</button>
        </div>
      ) : null}
    </header>
  );
}

function LoginView({ onLogin }: { onLogin: (session: AuthSession) => void }) {
  const [id, setId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const response = await apiClient.login({ id, password });
      onLogin(response);
    } catch (error) {
      setError(loginErrorMessage(error));
    }
  }

  return (
    <main className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <h1>DOBEDUB STUDIO | 접속</h1>
        <label>
          <span>ID (Email Address)</span>
          <input value={id} onChange={(event) => setId(event.target.value)} placeholder="Enter your Employee ID" required />
        </label>
        <label>
          <span>Password</span>
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter your Password" required />
        </label>
        {error ? <p className="error-text">{error}</p> : null}
        <button className="primary-button" type="submit">접속하기</button>
      </form>
    </main>
  );
}

function loginErrorMessage(error: unknown) {
  const message = error instanceof Error ? error.message : "";
  if (message === "Invalid credentials") {
    return "아이디 또는 비밀번호가 올바르지 않습니다.";
  }
  if (message === "User is inactive") {
    return "비활성화된 사용자입니다. 관리자에게 문의하세요.";
  }
  if (message === "id and password are required") {
    return "아이디와 비밀번호를 입력하세요.";
  }
  return message || "로그인에 실패했습니다.";
}

createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
