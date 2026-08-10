import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  apiClient,
  AdminUser,
  AdminWorkflow,
  ConfigControl,
  HealthResponse,
  HistoryItem,
  HistorySegment,
  InputImage,
  JobStatusResponse,
  MetadataStatusResponse,
  ModelMetadataResponse,
  OutputAsset,
  PermissionGovernance,
  PromptCategoryGroup,
  PromptCatalogResponse,
  PromptCategory,
  PromptEntry,
  PromptGenerateResponse,
  PromptSceneResponse,
  PromptSystemPromptResponse,
  TaskPromptItem,
  TaskPromptReviewFlags,
  SegmentDefaultsResponse,
  PromptTerm,
  RunpodConnectionResponse,
  SandboxPodStatus,
  SystemStatusResponse,
  UploadResponse,
  WorkflowItem,
  WorkflowWidgetMetadata,
  WorkflowSchema
} from "./api/client";
import { routeFromLocation, routePath, StudioRoute } from "./router";
// E-01: User/AuthSession types and permission helpers moved to ./auth so
// components/AppShell.tsx can use them without importing this entry file.
import { User, AuthSession, canUse, canUseAny } from "./auth";
import "./styles.css";

type SegmentState = {
  index: number;
  nodeId: string;
  subgraphName: string;
  displayName: string;
  startImageIndex: number;
  endImageIndex: number;
  progress: number;
  positivePrompt: string;
  defaultNegativePrompt: string;
  negativePrompt: string;
  negativePromptAddition: string;
  config: Record<string, string | number>;
  configControls: ConfigControl[];
};

type KeyframeState = {
  index: number;
  file: File | null;
  upload: UploadResponse | null;
  previewUrl: string;
  metaText: string;
  uploading: boolean;
  error: string;
};

const LOGIN_DISABLED_FOR_DEV = false;
const RESTORE_LOGIN_SESSION_ON_REFRESH = false;
const SESSION_USER_STORAGE_KEY = "dobedub.react.user.db-auth.v1";
const LEGACY_SESSION_USER_STORAGE_KEYS = ["dobedub.react.user", "dobedub.react.user.auth"];
const DEV_USER: User = { id: "dobedub", name: "장균은", role: "SUPER_ADMIN", permissions: ["admin:*"], isActive: true };

const ADMIN_USER_PERMISSIONS = ["users:read"];
const ADMIN_PERMISSION_PERMISSIONS = ["roles:read"];
const ADMIN_WORKFLOW_PERMISSIONS = ["workflows:write", "workflows:activate"];
const ADMIN_CATALOG_PERMISSIONS = ["prompt-catalog:write"];
const ADMIN_SANDBOX_POD_PERMISSIONS = ["sandbox:read"];
const ADMIN_CONSOLE_PERMISSIONS = [
  ...ADMIN_USER_PERMISSIONS,
  ...ADMIN_PERMISSION_PERMISSIONS,
  ...ADMIN_WORKFLOW_PERMISSIONS,
  ...ADMIN_CATALOG_PERMISSIONS,
  ...ADMIN_SANDBOX_POD_PERMISSIONS
];

function canUseAdminConsole(user: User | null) {
  return canUseAny(user, ADMIN_CONSOLE_PERMISSIONS);
}

function canUseAdminUsers(user: User | null) {
  return canUseAny(user, ADMIN_USER_PERMISSIONS);
}

function canUseAdminPermissions(user: User | null) {
  return canUseAny(user, ADMIN_PERMISSION_PERMISSIONS);
}

function canUseAdminWorkflows(user: User | null) {
  return canUseAny(user, ADMIN_WORKFLOW_PERMISSIONS);
}

function canUseAdminCatalog(user: User | null) {
  return canUseAny(user, ADMIN_CATALOG_PERMISSIONS);
}

function canUseAdminSandboxPod(user: User | null) {
  return canUseAny(user, ADMIN_SANDBOX_POD_PERMISSIONS);
}

// 권한 가드 버그 수정: 이전에는 route === "history"/"status"/"metadata"/"manual" 값만
// 보고 모달을 열어, 사이드바에 메뉴가 숨겨져 있어도 주소창에 직접 경로를 입력하면
// 권한 없이 데이터를 조회할 수 있었다. admin만 canUseAdminConsole 체크가 있었지만
// 그마저도 조용히 studio로 되돌릴 뿐 사용자에게 이유를 보여주지 않았다.
// design_handoff_dobedub_v3/README.md: "권한이 없는 메뉴는 사이드바에서 숨깁니다.
// 직접 URL 진입만 7g의 403 화면에 도달합니다." — 정식 7g 화면은 아직 없으므로(E-05/C-09
// 대상) 여기서는 임시로 AccessDeniedModal을 띄운다. 화면이 만들어지면 그쪽으로 교체.
const ROUTE_REQUIRED_PERMISSION: Partial<Record<StudioRoute, string>> = {
  history: "history:read",
  status: "system:read",
  metadata: "metadata:read",
  manual: "manual:read"
};

function routeAccessGranted(user: User | null, route: StudioRoute): boolean {
  if (route === "admin") {
    return canUseAdminConsole(user);
  }
  const requiredPermission = ROUTE_REQUIRED_PERMISSION[route];
  if (!requiredPermission) {
    return true;
  }
  return canUse(user, requiredPermission);
}

const ROUTE_LABEL: Partial<Record<StudioRoute, string>> = {
  history: "Task History",
  status: "Check Status",
  metadata: "Metadata View",
  manual: "User Manual",
  admin: "Admin"
};

const PROMPT_SCOPE_ORDER = ["positive", "negative"];
const FIXED_PROMPT_ROOT_CODES = new Set(["POSITIVE_ROOT", "NEGATIVE_ROOT"]);

async function copyText(text: string) {
  if (!text) {
    return;
  }
  try {
    await navigator.clipboard?.writeText(text);
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }
}

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
    if (!user && window.location.pathname !== routePath("login")) {
      navigate("login", true);
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
    navigate("studio");
  }

  function handleLogout() {
    clearLoginSession();
    setUser(null);
    setRoute("login");
    window.location.replace(routePath("login"));
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
      {user && route !== "login" ? (
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
        {canUse(user, "history:read") ? <button className={route === "history" ? "is-active" : ""} type="button" onClick={() => onNavigate("history")}>Task History</button> : null}
        {canUse(user, "system:read") ? <button className={route === "status" ? "is-active" : ""} type="button" onClick={() => onNavigate("status")}>Check Status</button> : null}
        {canUse(user, "metadata:read") ? <button className={route === "metadata" ? "is-active" : ""} type="button" onClick={() => onNavigate("metadata")}>Metadata View</button> : null}
        {canUse(user, "manual:read") ? <button className={route === "manual" ? "is-active" : ""} type="button" onClick={() => onNavigate("manual")}>User Manual</button> : null}
        {canUseAdminConsole(user) ? <button className={route === "admin" ? "is-active" : ""} type="button" onClick={() => onNavigate("admin")}>Admin</button> : null}
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

function serviceStatusLabel(configured: boolean, error: string, override?: string) {
  if (error) {
    return "FAIL";
  }
  if (override) {
    return override;
  }
  return configured ? "ONLINE" : "CHECK";
}

function qwenStatusLabel(promptLlm: SystemStatusResponse["promptLlm"] | undefined, error: string) {
  if (error) {
    return "FAIL";
  }
  const provider = (promptLlm?.provider || "mock").toLowerCase();
  if (provider === "mock") {
    return "MOCK";
  }
  return promptLlm?.configured && promptLlm?.apiKeyConfigured ? "ONLINE" : "CHECK";
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

function StudioShell({
  user,
  health,
  route,
  onNavigate
}: {
  user: User;
  health: HealthResponse | null;
  route: StudioRoute;
  onNavigate: (route: StudioRoute) => void;
}) {
  const skipWorkflowLoadRef = useRef(false);
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyPage, setHistoryPage] = useState(1);
  // B-01: 백엔드 기본값(20)·설계(3a 페이지 20건)와 통일. 사용자가 20/50 중
  // 고르면 이 값을 그대로 apiClient.history에 명시 전송한다.
  const [historyPageSize, setHistoryPageSize] = useState<20 | 50>(20);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [selectedHistoryTaskId, setSelectedHistoryTaskId] = useState("");
  const [historyTab, setHistoryTab] = useState<"overview" | "images" | "config" | "video" | "review">("overview");
  const [deleteTarget, setDeleteTarget] = useState<HistoryItem | null>(null);
  const [modalNotice, setModalNotice] = useState("");
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null);
  const [runpodConnection, setRunpodConnection] = useState<RunpodConnectionResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [statusNotice, setStatusNotice] = useState("");
  const [manualModalOpen, setManualModalOpen] = useState(false);
  const [manualHtml, setManualHtml] = useState("");
  const [manualLoading, setManualLoading] = useState(false);
  const [manualError, setManualError] = useState("");
  const [metadataModalOpen, setMetadataModalOpen] = useState(false);
  const [metadataWorkflowId, setMetadataWorkflowId] = useState("");
  const [metadataTab, setMetadataTab] = useState<"summary" | "subgraphs" | "parameters" | "models" | "nodes">("summary");
  const [metadataStatus, setMetadataStatus] = useState<MetadataStatusResponse | null>(null);
  const [workflowMetadata, setWorkflowMetadata] = useState<WorkflowWidgetMetadata | null>(null);
  const [modelMetadata, setModelMetadata] = useState<ModelMetadataResponse | null>(null);
  const [metadataLoading, setMetadataLoading] = useState(false);
  const [metadataNotice, setMetadataNotice] = useState("");
  const [adminModalOpen, setAdminModalOpen] = useState(false);
  const [accessDeniedRoute, setAccessDeniedRoute] = useState<StudioRoute | null>(null);
  const [promptBuilderOpen, setPromptBuilderOpen] = useState(false);
  const [promptCatalogAdminOpen, setPromptCatalogAdminOpen] = useState(false);
  const [promptCatalog, setPromptCatalog] = useState<PromptCatalogResponse | null>(null);
  const [promptSystemPrompt, setPromptSystemPrompt] = useState<PromptSystemPromptResponse | null>(null);
  const [promptSystemPromptText, setPromptSystemPromptText] = useState("");
  const [promptBuilderPanel, setPromptBuilderPanel] = useState<"keywords" | "systemPrompt">("keywords");
  const [promptSelectedTermIds, setPromptSelectedTermIds] = useState<number[]>([]);
  const [promptScene, setPromptScene] = useState<PromptSceneResponse | null>(null);
  const [promptGenerated, setPromptGenerated] = useState<PromptGenerateResponse | null>(null);
  const [promptSceneDescription, setPromptSceneDescription] = useState("");
  const [promptBuilderLoading, setPromptBuilderLoading] = useState(false);
  const [promptBuilderNotice, setPromptBuilderNotice] = useState("");
  const [promptReviewItems, setPromptReviewItems] = useState<TaskPromptItem[]>([]);
  const [promptReviewLoading, setPromptReviewLoading] = useState(false);
  const [promptReviewNotice, setPromptReviewNotice] = useState("");
  const [promptReuseOpen, setPromptReuseOpen] = useState(false);
  const [promptReuseKeyword, setPromptReuseKeyword] = useState("");
  const [promptReuseItems, setPromptReuseItems] = useState<TaskPromptItem[]>([]);
  const [promptReuseLoading, setPromptReuseLoading] = useState(false);
  const [promptReuseNotice, setPromptReuseNotice] = useState("");
  const [selectedWorkflow, setSelectedWorkflow] = useState("");
  const [schema, setSchema] = useState<WorkflowSchema | null>(null);
  const [segments, setSegments] = useState<SegmentState[]>([]);
  const [selectedSegmentIndex, setSelectedSegmentIndex] = useState(1);
  const [keyframes, setKeyframes] = useState<KeyframeState[]>([]);
  const [running, setRunning] = useState(false);
  const [cancelRequested, setCancelRequested] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState("");
  const [progress, setProgress] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [logText, setLogText] = useState("");
  const [latestJob, setLatestJob] = useState<JobStatusResponse | null>(null);
  const [outputAssets, setOutputAssets] = useState<OutputAsset[]>([]);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const workflowSelectionLocked = running || cancelRequested;

  async function loadWorkflowIntoState(workflowId: string, options?: { preserveNotice?: boolean }) {
    setError("");
    const nextSchema = await apiClient.workflowSchema(workflowId);
    releaseKeyframePreviews(keyframes);
    setSchema(nextSchema);
    setSegments(createSegmentsFromSchema(nextSchema));
    setSelectedSegmentIndex(1);
    setKeyframes(createKeyframes(nextSchema.keyframeCount || 1));
    setPromptSceneDescription("");
    setPromptScene(null);
    setPromptGenerated(null);
    resetRunState();
    if (!options?.preserveNotice) {
      setNotice("");
    }
    return nextSchema;
  }

  async function loadHistoryPage(page = historyPage, pageSize = historyPageSize) {
    setHistoryLoading(true);
    setModalNotice("");
    try {
      const response = await apiClient.history(page, pageSize);
      const items = response.items || [];
      setHistory(items);
      setHistoryPage(response.page || page);
      setHistoryTotal(response.total || 0);
      setSelectedHistoryTaskId((current) => {
        if (current && items.some((item) => item.taskId === current)) {
          return current;
        }
        return items[0]?.taskId || "";
      });
    } catch (error) {
      setModalNotice(error instanceof Error ? error.message : "작업 이력을 불러오지 못했습니다.");
    } finally {
      setHistoryLoading(false);
    }
  }

  // B-01: 페이지 크기를 바꾸면 현재 페이지 번호 기준이 달라지므로 1페이지로
  // 되돌아가 새 크기로 다시 불러온다.
  function changeHistoryPageSize(pageSize: 20 | 50) {
    setHistoryPageSize(pageSize);
    void loadHistoryPage(1, pageSize);
  }

  async function loadPromptReview(taskId: string) {
    if (!taskId) {
      setPromptReviewItems([]);
      return;
    }
    setPromptReviewLoading(true);
    setPromptReviewNotice("");
    try {
      const response = await apiClient.jobPrompts(taskId);
      setPromptReviewItems(response.items || []);
    } catch (error) {
      setPromptReviewItems([]);
      setPromptReviewNotice(error instanceof Error ? error.message : "작업 프롬프트 정보를 불러오지 못했습니다.");
    } finally {
      setPromptReviewLoading(false);
    }
  }

  async function savePromptReview(segmentIndex: number, payload: Record<string, unknown>) {
    if (!selectedHistoryTaskId) {
      return;
    }
    setPromptReviewLoading(true);
    setPromptReviewNotice("");
    try {
      const updated = await apiClient.updateJobPromptReview(selectedHistoryTaskId, segmentIndex, payload);
      setPromptReviewItems((items) => items.map((item) => item.segmentIndex === segmentIndex ? updated : item));
      setPromptReviewNotice("프롬프트 리뷰 정보를 저장했습니다.");
    } catch (error) {
      setPromptReviewNotice(error instanceof Error ? error.message : "프롬프트 리뷰 저장에 실패했습니다.");
    } finally {
      setPromptReviewLoading(false);
    }
  }

  // B-02: task_prompts 기반 "영상 결과 평가"(savePromptReview, 위)와 역할이 분리된
  // "프롬프트 생성 품질" 평가 저장 경로. 3f Run 상세 화면에서만 호출되며,
  // prompt_feedback.taskId를 항상 채워 두 기록을 연결한다(완료 기준).
  // 응답이 outputId 하나 기준의 부분 정보만 담고 있어(id/outputId/taskId/rating),
  // 전체 목록 상태를 신뢰성 있게 갱신하려고 프롬프트 리뷰 전체를 재조회한다.
  async function savePromptFeedback(outputId: string, payload: { rating?: number; notes?: string }) {
    if (!selectedHistoryTaskId || !outputId) {
      return;
    }
    setPromptReviewLoading(true);
    setPromptReviewNotice("");
    try {
      await apiClient.savePromptFeedback({
        outputId,
        taskId: selectedHistoryTaskId,
        rating: payload.rating,
        notes: payload.notes
      });
      await loadPromptReview(selectedHistoryTaskId);
      setPromptReviewNotice("프롬프트 생성 품질 평가를 저장했습니다.");
    } catch (error) {
      setPromptReviewNotice(error instanceof Error ? error.message : "프롬프트 생성 품질 평가 저장에 실패했습니다.");
    } finally {
      setPromptReviewLoading(false);
    }
  }

  async function openPromptReuse() {
    setPromptReuseOpen(true);
    setPromptReuseNotice("");
    await searchPromptReuse(promptReuseKeyword);
  }

  async function searchPromptReuse(keyword = promptReuseKeyword) {
    setPromptReuseLoading(true);
    setPromptReuseNotice("");
    try {
      const response = await apiClient.reusablePrompts({
        keyword: keyword.trim(),
        reuseEligible: true,
        limit: 50
      });
      setPromptReuseItems(response.items || []);
      if (!(response.items || []).length) {
        setPromptReuseNotice("검색 조건에 맞는 재사용 프롬프트가 없습니다.");
      }
    } catch (error) {
      setPromptReuseItems([]);
      setPromptReuseNotice(error instanceof Error ? error.message : "재사용 프롬프트 검색에 실패했습니다.");
    } finally {
      setPromptReuseLoading(false);
    }
  }

  function applyReusablePrompt(prompt: TaskPromptItem) {
    applyPromptSceneToSegment({
      positivePrompt: prompt.positivePrompt,
      negativePrompt: prompt.negativePrompt,
      negativePromptAddition: "",
      source: `Prompt Reuse #${prompt.id}`
    });
    setPromptReuseOpen(false);
  }

  async function loadSystemStatus() {
    setStatusLoading(true);
    setStatusNotice("");
    try {
      setSystemStatus(await apiClient.systemStatus());
    } catch (error) {
      setStatusNotice(error instanceof Error ? error.message : "시스템 상태를 불러오지 못했습니다.");
    } finally {
      setStatusLoading(false);
    }
  }

  async function testRunpodConnection() {
    setStatusLoading(true);
    setStatusNotice("Checking ComfyUI RunPod endpoint...");
    try {
      const response = await apiClient.runpodConnection();
      setRunpodConnection(response);
      const workers = response.workers || {};
      const jobs = response.jobs || {};
      setStatusNotice(`${response.message || "ComfyUI RunPod checked."} Workers idle/running: ${workers.idle ?? 0}/${workers.running ?? 0}, Queue: ${jobs.inQueue ?? 0}`);
    } catch (error) {
      setRunpodConnection(null);
      setStatusNotice(error instanceof Error ? error.message : "ComfyUI RunPod 연결 확인에 실패했습니다.");
    } finally {
      setStatusLoading(false);
    }
  }

  async function loadManual() {
    setManualLoading(true);
    setManualError("");
    try {
      setManualHtml(await apiClient.manualHtml());
    } catch (error) {
      setManualHtml("");
      setManualError(error instanceof Error ? error.message : "사용자 매뉴얼을 불러오지 못했습니다.");
    } finally {
      setManualLoading(false);
    }
  }

  async function loadMetadata(workflowId = metadataWorkflowId || selectedWorkflow || workflows[0]?.id || "") {
    if (!workflowId) {
      setMetadataNotice("조회할 워크플로우가 없습니다.");
      return;
    }
    setMetadataLoading(true);
    setMetadataNotice("");
    setMetadataWorkflowId(workflowId);
    try {
      const [status, metadata, models] = await Promise.all([
        apiClient.metadataStatus(),
        apiClient.workflowWidgetMetadata(workflowId),
        apiClient.metadataModels()
      ]);
      setMetadataStatus(status);
      setWorkflowMetadata(metadata);
      setModelMetadata(models);
    } catch (error) {
      setMetadataStatus(null);
      setWorkflowMetadata(null);
      setModelMetadata(null);
      setMetadataNotice(error instanceof Error ? error.message : "Metadata를 불러오지 못했습니다.");
    } finally {
      setMetadataLoading(false);
    }
  }

  async function rebuildMetadata() {
    setMetadataLoading(true);
    setMetadataNotice("Metadata를 재생성하고 있습니다.");
    try {
      await apiClient.rebuildMetadata();
      await loadMetadata(metadataWorkflowId || selectedWorkflow);
      setMetadataNotice("Metadata를 재생성했습니다.");
    } catch (error) {
      setMetadataNotice(error instanceof Error ? error.message : "Metadata 재생성에 실패했습니다.");
    } finally {
      setMetadataLoading(false);
    }
  }

  async function openPromptBuilder() {
    setPromptBuilderOpen(true);
    setPromptBuilderPanel("keywords");
    setPromptBuilderNotice("");
    if (!promptCatalog) {
      await loadPromptCatalog();
    }
  }

  async function loadPromptCatalog(successNotice = "") {
    setPromptBuilderLoading(true);
    setPromptBuilderNotice("");
    try {
      const catalog = await apiClient.promptCatalog();
      setPromptCatalog(catalog);
      if (!promptCatalogHasTerms(catalog)) {
        setPromptBuilderNotice("Prompt catalog가 비어 있습니다. Admin Console에서 카테고리와 key word를 등록하세요.");
      } else if (successNotice) {
        setPromptBuilderNotice(successNotice);
      }
    } catch (error) {
      setPromptCatalog(null);
      setPromptBuilderNotice(error instanceof Error ? error.message : "Prompt catalog를 불러오지 못했습니다.");
    } finally {
      setPromptBuilderLoading(false);
    }
  }

  async function refreshPromptBuilder() {
    setPromptBuilderPanel("keywords");
    setPromptSelectedTermIds([]);
    setPromptScene(null);
    setPromptGenerated(null);
    setPromptSceneDescription("");
    await loadPromptCatalog("빌더 화면을 초기화하고 카탈로그를 새로고침했습니다.");
  }

  async function loadPromptSystemPrompt() {
    setPromptBuilderLoading(true);
    setPromptBuilderNotice("");
    try {
      const response = await apiClient.promptSystemPrompt();
      setPromptSystemPrompt(response);
      setPromptSystemPromptText(response.promptText || "");
    } catch (error) {
      setPromptBuilderNotice(error instanceof Error ? error.message : "System Prompt를 불러오지 못했습니다.");
    } finally {
      setPromptBuilderLoading(false);
    }
  }

  async function savePromptSystemPrompt() {
    setPromptBuilderLoading(true);
    setPromptBuilderNotice("");
    try {
      const response = await apiClient.savePromptSystemPrompt({
        code: promptSystemPrompt?.code || "qwen_wan_i2v_positive",
        name: promptSystemPrompt?.name || "Qwen WAN I2V Positive Prompt Composer",
        provider: promptSystemPrompt?.provider || "runpod_vllm",
        modelFamily: promptSystemPrompt?.modelFamily || "qwen",
        promptText: promptSystemPromptText
      });
      setPromptSystemPrompt(response);
      setPromptSystemPromptText(response.promptText || "");
      setPromptBuilderNotice("System Prompt를 저장했습니다.");
    } catch (error) {
      setPromptBuilderNotice(error instanceof Error ? error.message : "System Prompt 저장에 실패했습니다.");
    } finally {
      setPromptBuilderLoading(false);
    }
  }

  async function savePromptCategory(payload: Record<string, unknown>, categoryId?: number) {
    setPromptBuilderLoading(true);
    setPromptBuilderNotice("");
    try {
      const catalog = await apiClient.savePromptCategory(payload, categoryId);
      setPromptCatalog(catalog);
      setPromptBuilderNotice("Prompt category를 저장했습니다.");
    } catch (error) {
      setPromptBuilderNotice(error instanceof Error ? error.message : "Prompt category 저장에 실패했습니다.");
    } finally {
      setPromptBuilderLoading(false);
    }
  }

  async function savePromptCategoryGroup(payload: Record<string, unknown>, groupId?: number) {
    setPromptBuilderLoading(true);
    setPromptBuilderNotice("");
    try {
      const catalog = await apiClient.savePromptCategoryGroup(payload, groupId);
      setPromptCatalog(catalog);
      setPromptBuilderNotice("카테고리를 저장했습니다.");
    } catch (error) {
      setPromptBuilderNotice(error instanceof Error ? error.message : "카테고리 저장에 실패했습니다.");
    } finally {
      setPromptBuilderLoading(false);
    }
  }

  async function deactivatePromptCategoryGroup(groupId: number) {
    if (!window.confirm("카테고리와 하위 서브 카테고리, key word 연결을 비활성화합니다. 기존 이력은 유지됩니다. 진행하시겠습니까?")) {
      return;
    }
    setPromptBuilderLoading(true);
    setPromptBuilderNotice("");
    try {
      const catalog = await apiClient.deactivatePromptCategoryGroup(groupId);
      setPromptCatalog(catalog);
      setPromptBuilderNotice("카테고리를 비활성화했습니다.");
    } catch (error) {
      setPromptBuilderNotice(error instanceof Error ? error.message : "카테고리 비활성화에 실패했습니다.");
    } finally {
      setPromptBuilderLoading(false);
    }
  }

  async function deactivatePromptCategory(categoryId: number) {
    if (!window.confirm("카테고리와 포함된 key word를 비활성화합니다. 기존 이력은 유지됩니다. 진행하시겠습니까?")) {
      return;
    }
    setPromptBuilderLoading(true);
    setPromptBuilderNotice("");
    try {
      const catalog = await apiClient.deactivatePromptCategory(categoryId);
      setPromptCatalog(catalog);
      setPromptBuilderNotice("Prompt category를 비활성화했습니다.");
    } catch (error) {
      setPromptBuilderNotice(error instanceof Error ? error.message : "Prompt category 비활성화에 실패했습니다.");
    } finally {
      setPromptBuilderLoading(false);
    }
  }

  async function savePromptTerm(payload: Record<string, unknown>, termId?: number) {
    setPromptBuilderLoading(true);
    setPromptBuilderNotice("");
    try {
      const catalog = await apiClient.savePromptTerm(payload, termId);
      setPromptCatalog(catalog);
      setPromptBuilderNotice("Key word를 저장했습니다.");
    } catch (error) {
      setPromptBuilderNotice(error instanceof Error ? error.message : "Key word 저장에 실패했습니다.");
    } finally {
      setPromptBuilderLoading(false);
    }
  }

  async function deactivatePromptTerm(termId: number) {
    if (!window.confirm("선택한 key word를 비활성화합니다. 기존 이력은 유지됩니다. 진행하시겠습니까?")) {
      return;
    }
    setPromptBuilderLoading(true);
    setPromptBuilderNotice("");
    try {
      const catalog = await apiClient.deactivatePromptTerm(termId);
      setPromptCatalog(catalog);
      setPromptBuilderNotice("Key word를 비활성화했습니다.");
    } catch (error) {
      setPromptBuilderNotice(error instanceof Error ? error.message : "Key word 비활성화에 실패했습니다.");
    } finally {
      setPromptBuilderLoading(false);
    }
  }

  async function buildPromptSceneRequest(): Promise<PromptSceneResponse | null> {
    if (!selectedSegment) {
      setPromptBuilderNotice("선택된 서브그래프가 없습니다.");
      return null;
    }
    return apiClient.buildPromptScene({
      workflowId: selectedWorkflow,
      segmentIndex: selectedSegment.index,
      termIds: promptSelectedTermIds,
      language: "ko",
      description: promptSceneDescription.trim(),
      constraints: {
        i2v_mode: true,
        preserve_identity: true,
        avoid_new_objects: true
      }
    });
  }

  async function generatePromptDraft() {
    if (!selectedSegment) {
      setPromptBuilderNotice("선택된 서브그래프가 없습니다.");
      return;
    }
    setPromptBuilderLoading(true);
    setPromptBuilderNotice("");
    try {
      const sceneForGeneration = promptScene || await buildPromptSceneRequest();
      if (!sceneForGeneration) {
        return;
      }
      if (!promptScene) {
        setPromptScene(sceneForGeneration);
      }
      const generated = await apiClient.generatePrompt({
        workflowId: selectedWorkflow,
        segmentIndex: selectedSegment.index,
        scene: sceneForGeneration.scene,
        constraints: sceneForGeneration.constraints,
        termIds: sceneForGeneration.usedTermIds,
        language: "ko"
      });
      setPromptGenerated(generated);
      setPromptBuilderNotice(`${promptScene ? "" : "Scene JSON 자동 생성 후 "}Prompt generation 완료 (${generated.provider}).`);
    } catch (error) {
      setPromptGenerated(null);
      setPromptBuilderNotice(error instanceof Error ? error.message : "Prompt generation에 실패했습니다.");
    } finally {
      setPromptBuilderLoading(false);
    }
  }

  function togglePromptTerm(termId: number) {
    const category = findPromptTermCategory(promptCatalog, termId);
    setPromptScene(null);
    setPromptGenerated(null);
    const sameCategoryTermIds = new Set((category?.terms || []).map((term) => term.id));
    setPromptSelectedTermIds((items) => {
      if (items.includes(termId)) {
        return items.filter((item) => item !== termId);
      }
      if (category?.selectionMode === "single") {
        return [...items.filter((item) => !sameCategoryTermIds.has(item)), termId];
      }
      if (category?.maxSelectCount) {
        const selectedInCategory = items.filter((item) => sameCategoryTermIds.has(item));
        if (selectedInCategory.length >= category.maxSelectCount) {
          return items;
        }
      }
      return [...items, termId];
    });
    if (category?.maxSelectCount && category.selectionMode !== "single") {
      const selectedInCategory = promptSelectedTermIds.filter((item) => sameCategoryTermIds.has(item));
      if (!promptSelectedTermIds.includes(termId) && selectedInCategory.length >= category.maxSelectCount) {
        setPromptBuilderNotice(`${category.nameKo || category.code}는 최대 ${category.maxSelectCount}개까지 선택할 수 있습니다.`);
      }
    }
  }

  function clearPromptBuilderSelection(termIds?: number[]) {
    if (termIds?.length) {
      const removeIds = new Set(termIds);
      setPromptSelectedTermIds((items) => items.filter((item) => !removeIds.has(item)));
    } else {
      setPromptSelectedTermIds([]);
    }
    setPromptScene(null);
    setPromptGenerated(null);
    setPromptBuilderNotice("선택한 key word를 초기화했습니다.");
  }

  function applyPromptSceneToSegment(promptOverride?: {
    positivePrompt?: string;
    negativePrompt?: string;
    negativePromptAddition?: string;
    source?: string;
  }) {
    if (!selectedSegment) {
      return;
    }
    const positivePrompt = promptOverride?.positivePrompt ?? promptGenerated?.positivePrompt ?? promptScene?.positivePromptDraft ?? "";
    const negativePromptAddition = promptOverride?.negativePromptAddition ?? promptGenerated?.negativePrompt ?? promptScene?.negativePromptDraft ?? "";
    updateSegment(selectedSegment.index, (segment) => ({
      ...segment,
      positivePrompt,
      defaultNegativePrompt: segment.defaultNegativePrompt || segment.negativePrompt,
      negativePrompt: promptOverride?.negativePrompt ?? combinePromptText(segment.defaultNegativePrompt || segment.negativePrompt, negativePromptAddition),
      negativePromptAddition: promptOverride?.negativePrompt ?? combinePromptText(segment.defaultNegativePrompt || segment.negativePrompt, negativePromptAddition)
    }));
    setPromptBuilderOpen(false);
    setNotice(`${selectedSegment.displayName}에 ${promptOverride?.source || (promptGenerated ? "Generated Prompt" : "Prompt Builder")} 결과를 적용했습니다.`);
  }

  async function loadWorkflows(preferredWorkflowId?: string) {
    const workflowResponse = await apiClient.workflows();
    setWorkflows(workflowResponse || []);
    if (workflowSelectionLocked) {
      return;
    }
    const defaultWorkflow = (workflowResponse || []).find((workflow) => workflow.id === preferredWorkflowId)
      || (workflowResponse || []).find((workflow) => workflow.id === selectedWorkflow)
      || (workflowResponse || []).find((workflow) => workflow.id === "1-images.json")
      || (workflowResponse || [])[0];
    setSelectedWorkflow(defaultWorkflow?.id || "");
  }

  useEffect(() => {
    let active = true;
    Promise.all([apiClient.workflows(), apiClient.history(1, historyPageSize)])
      .then(([workflowResponse, historyResponse]) => {
        if (!active) {
          return;
        }
        setWorkflows(workflowResponse || []);
        const defaultWorkflow = (workflowResponse || []).find((workflow) => workflow.id === "1-images.json") || (workflowResponse || [])[0];
        setSelectedWorkflow(defaultWorkflow?.id || "");
        setHistory(historyResponse.items || []);
        setHistoryTotal(historyResponse.total || 0);
        setSelectedHistoryTaskId(historyResponse.items?.[0]?.taskId || "");
      })
      .catch((error: Error) => {
        if (active) {
          setError(error.message);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedWorkflow) {
      return;
    }
    if (skipWorkflowLoadRef.current) {
      skipWorkflowLoadRef.current = false;
      return;
    }
    let active = true;
    setError("");
    loadWorkflowIntoState(selectedWorkflow)
      .then((nextSchema) => {
        if (!active) {
          return;
        }
        setSchema(nextSchema);
      })
      .catch((error: Error) => {
        if (active) {
          setError(error.message);
        }
      });
    return () => {
      active = false;
    };
  }, [selectedWorkflow]);

  useEffect(() => {
    const granted = routeAccessGranted(user, route);
    setHistoryModalOpen(route === "history" && granted);
    setStatusModalOpen(route === "status" && granted);
    setManualModalOpen(route === "manual" && granted);
    setMetadataModalOpen(route === "metadata" && granted);
    setAdminModalOpen(route === "admin" && granted);
    setAccessDeniedRoute(!granted && route !== "studio" && route !== "login" ? route : null);

    if (!granted) {
      return;
    }

    if (route === "history") {
      void loadHistoryPage(1);
    }
    if (route === "status") {
      void loadSystemStatus();
    }
    if (route === "manual" && !manualHtml) {
      void loadManual();
    }
    if (route === "metadata") {
      const workflowId = selectedWorkflow || workflows[0]?.id || "";
      if (!workflowId) {
        return;
      }
      setMetadataWorkflowId(workflowId);
      void loadMetadata(workflowId);
    }
  }, [route, selectedWorkflow, workflows.length, user]);

  useEffect(() => {
    if (historyModalOpen && historyTab === "review" && selectedHistoryTaskId) {
      void loadPromptReview(selectedHistoryTaskId);
    }
  }, [historyModalOpen, historyTab, selectedHistoryTaskId]);

  useEffect(() => {
    return () => releaseKeyframePreviews(keyframes);
  }, []);

  const selected = useMemo(
    () => workflows.find((workflow) => workflow.id === selectedWorkflow),
    [workflows, selectedWorkflow]
  );
  const selectedSegment = useMemo(
    () => segments.find((segment) => segment.index === selectedSegmentIndex) || segments[0],
    [segments, selectedSegmentIndex]
  );
  const activeImageIndexes = useMemo(() => {
    if (!selectedSegment) {
      return new Set<number>();
    }
    return new Set([selectedSegment.startImageIndex, selectedSegment.endImageIndex].filter(Boolean));
  }, [selectedSegment]);

  function updateSegment(index: number, updater: (segment: SegmentState) => SegmentState) {
    setSegments((items) => items.map((segment) => (segment.index === index ? updater(segment) : segment)));
  }

  function updateSelectedPrompt(field: "positivePrompt" | "negativePrompt", value: string) {
    if (!selectedSegment) {
      return;
    }
    updateSegment(selectedSegment.index, (segment) => ({ ...segment, [field]: value }));
  }

  function updateConfigValue(key: string, value: string, control?: ConfigControl) {
    if (!selectedSegment) {
      return;
    }
    const resolvedValue = ["string", "text"].includes(control?.type || "") ? value : Number(value);
    updateSegment(selectedSegment.index, (segment) => ({
      ...segment,
      config: {
        ...segment.config,
        [key]: Number.isNaN(resolvedValue) ? value : resolvedValue
      }
    }));
  }

  async function resetSegmentConfigsToDefaults() {
    if (!selectedWorkflow) {
      setNotice("워크플로우를 먼저 선택하세요.");
      return;
    }
    try {
      const defaults = await apiClient.workflowSegmentDefaults(selectedWorkflow);
      const defaultSegments = defaults.segments || [];
      if (!defaultSegments.length) {
        setNotice("현재 워크플로우의 세그먼트 기본값이 없습니다.");
        return;
      }
      setSegments((items) => items.map((segment, index) => {
        const source = defaultSegments[index] || defaultSegments[0] || {};
        const { seed: _seed, Seed: _legacySeed, ...currentConfig } = segment.config;
        const { seed: _defaultSeed, Seed: _legacyDefaultSeed, ...defaultConfig } = source.config || {};
        return {
          ...segment,
          config: {
            ...currentConfig,
            ...defaultConfig
          }
        };
      }));
      setNotice("세그먼트 설정을 워크플로우 기본값으로 초기화했습니다.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "세그먼트 기본값을 불러오지 못했습니다.");
    }
  }

  async function applySelectedFiles(startIndex: number, files: FileList | null) {
    const selectedFiles = Array.from(files || []);
    if (!selectedFiles.length) {
      return;
    }
    setNotice("이미지 미리보기를 준비하고 업로드를 시작합니다.");
    for (const [offset, file] of selectedFiles.entries()) {
      const targetIndex = startIndex + offset;
      if (targetIndex > keyframes.length) {
        continue;
      }
      const previewUrl = URL.createObjectURL(file);
      setKeyframes((items) =>
        items.map((keyframe) => {
          if (keyframe.index !== targetIndex) {
            return keyframe;
          }
          if (keyframe.previewUrl.startsWith("blob:")) {
            URL.revokeObjectURL(keyframe.previewUrl);
          }
          return {
            ...keyframe,
            file,
            upload: null,
            previewUrl,
            metaText: `${Math.round(file.size / 1024)}KB · pending upload`,
            uploading: true,
            error: ""
          };
        })
      );
      try {
        const upload = await apiClient.upload({
          fileName: file.name,
          mimeType: file.type || "application/octet-stream",
          dataUrl: await fileToDataUrl(file)
        });
        setKeyframes((items) =>
          items.map((keyframe) =>
            keyframe.index === targetIndex
              ? {
                  ...keyframe,
                  upload,
                  uploading: false,
                  metaText: `${upload.fileName} · ${(upload.sizeBytes / 1024 / 1024).toFixed(1)}MB · uploaded`,
                  error: ""
                }
              : keyframe
          )
        );
        setNotice("이미지 업로드가 완료되었습니다.");
      } catch (error) {
        setKeyframes((items) =>
          items.map((keyframe) =>
            keyframe.index === targetIndex
              ? {
                  ...keyframe,
                  uploading: false,
                  error: error instanceof Error ? error.message : "Upload failed"
                }
              : keyframe
          )
        );
        setNotice("일부 이미지 업로드에 실패했습니다.");
      }
    }
  }

  function clearKeyframe(index: number) {
    setKeyframes((items) =>
      items.map((keyframe) => {
        if (keyframe.index !== index) {
          return keyframe;
        }
        if (keyframe.previewUrl.startsWith("blob:")) {
          URL.revokeObjectURL(keyframe.previewUrl);
        }
        return createKeyframe(index);
      })
    );
  }

  const jobPayloadPreview = useMemo(
    () => ({
      workflowId: selectedWorkflow,
      user,
      keyframes: keyframes.map((keyframe) => ({
        index: keyframe.index,
        uploadId: keyframe.upload?.assetId || null,
        fileName: keyframe.upload?.fileName || keyframe.file?.name || `keyframe-${keyframe.index}.png`
      })),
      segments: segments.map((segment) => ({
        index: segment.index,
        nodeId: segment.nodeId,
        subgraphName: segment.subgraphName,
        displayName: segment.displayName,
        positivePrompt: segment.positivePrompt,
        negativePromptAddition: segment.negativePromptAddition || segment.negativePrompt,
        config: segment.config
      }))
    }),
    [keyframes, segments, selectedWorkflow, user]
  );
  const selectedOutput = useMemo(() => selectedOutputAsset(outputAssets, selectedSegmentIndex), [outputAssets, selectedSegmentIndex]);
  const finalOutput = useMemo(() => finalOutputAsset(outputAssets), [outputAssets]);
  const displayOutput = finalOutput || selectedOutput || (latestJob?.outputUrl ? { downloadUrl: latestJob.outputUrl, fileName: "generated output", outputRole: "final" } : null);
  const displayOutputRawUrl = displayOutput?.downloadUrl || displayOutput?.url || "";
  const displayOutputInlineUrl = displayOutputRawUrl ? fileUrlWithMode(displayOutputRawUrl, "inline") : "";
  const displayOutputDownloadUrl = displayOutputRawUrl ? fileUrlWithMode(displayOutputRawUrl, "download") : "";
  const displayOutputMediaUrl = useProtectedAssetUrl(displayOutputInlineUrl);
  const hasSuccessfulOutput = isSuccessStatus(latestJob?.status) && Boolean(displayOutputInlineUrl);
  const hasFailedJob = Boolean(latestJob && ["fail", "failed", "timed_out"].includes(latestJob.status.toLowerCase()));
  const segmentDetailRows = selectedSegment
    ? previewSegmentDetailRows(selectedWorkflow, selectedSegment, segments.length, selectedOutput, finalOutput)
    : [];
  const selectedHistory = useMemo(
    () => history.find((item) => item.taskId === selectedHistoryTaskId) || history[0] || null,
    [history, selectedHistoryTaskId]
  );
  const historyPageCount = Math.max(1, Math.ceil(historyTotal / historyPageSize));

  async function copyPromptList(prompts: PromptEntry[] | undefined) {
    const text = formatPromptList(prompts);
    if (!text) {
      setModalNotice("복사할 프롬프트가 없습니다.");
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
    }
    setModalNotice("프롬프트를 복사했습니다.");
  }

  async function deleteHistoryItem() {
    if (!deleteTarget?.taskId) {
      return;
    }
    setModalNotice("");
    try {
      await apiClient.deleteHistory(deleteTarget.taskId);
      setDeleteTarget(null);
      await loadHistoryPage(historyPage);
      setNotice("작업 내역과 연결된 asset을 삭제했습니다.");
    } catch (error) {
      setModalNotice(error instanceof Error ? error.message : "삭제에 실패했습니다.");
    }
  }

  async function applyHistoryRework(item: HistoryItem) {
    if (workflowSelectionLocked) {
      setModalNotice("생성 작업이 종료된 후 재작업 정보를 불러올 수 있습니다.");
      return;
    }
    const targetWorkflowId = workflowIdFromHistoryItem(item, workflows, selectedWorkflow);
    if (!targetWorkflowId) {
      setModalNotice("재작업에 사용할 워크플로우를 찾지 못했습니다.");
      return;
    }
    setModalNotice("");
    try {
      const nextSchema = await apiClient.workflowSchema(targetWorkflowId);
      const nextSegments = createSegmentsFromHistory(nextSchema, item);
      const nextKeyframes = createKeyframesFromHistory(nextSchema, item);
      releaseKeyframePreviews(keyframes);
      skipWorkflowLoadRef.current = targetWorkflowId !== selectedWorkflow;
      setSelectedWorkflow(targetWorkflowId);
      setSchema(nextSchema);
      setSegments(nextSegments);
      setSelectedSegmentIndex(1);
      setKeyframes(nextKeyframes);
      resetRunState();
      // The history modal is route-controlled. Closing only its local state leaves
      // the URL on /studio/history, which prevents the Task History button opening it again.
      onNavigate("studio");
      setNotice(`재작업 정보를 생성 화면에 불러왔습니다. 입력 이미지 ${nextKeyframes.filter((keyframe) => keyframe.upload?.assetId).length}개 로드됨.`);
    } catch (error) {
      setModalNotice(error instanceof Error ? error.message : "재작업 정보를 불러오지 못했습니다.");
    }
  }

  async function generateVideo() {
    if (running) {
      return;
    }
    const missing = keyframes.filter((keyframe) => !keyframe.upload?.assetId);
    if (missing.length) {
      setError("입력파일을 업로드하세요. 이 워크플로우는 i2v 전용입니다. t2i, t2v는 지원하지 않습니다.");
      return;
    }
    setRunning(true);
    setCancelRequested(false);
    setError("");
    setNotice("작업을 제출합니다.");
    setProgress(0);
    setElapsedSeconds(0);
    setOutputAssets([]);
    setLatestJob(null);
    setLogText("RUNPOD STATUS : QUEUED");
    try {
      const created = await apiClient.createJob(jobPayloadPreview);
      setCurrentTaskId(created.taskId);
      const finalJob = await pollJob(created.taskId);
      setLatestJob(finalJob);
      if (finalJob.status === "success") {
        setNotice("작업이 완료되었습니다.");
        setOutputAssets(finalJob.outputAssets || []);
        setSegments((items) => items.map((segment) => ({ ...segment, progress: 100 })));
        setHistory((await apiClient.history(1, historyPageSize)).items || []);
      } else if (finalJob.status === "cancelled") {
        setNotice("작업이 취소되었습니다.");
      } else {
        setNotice(finalJob.message || "작업이 종료되었습니다.");
        setOutputAssets(finalJob.outputAssets || []);
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : "Generate failed");
      setLogText(`RUNPOD STATUS : FAILED`);
    } finally {
      setRunning(false);
      setCancelRequested(false);
    }
  }

  async function pollJob(taskId: string): Promise<JobStatusResponse> {
    let latest: JobStatusResponse | null = null;
    for (;;) {
      const job = await apiClient.jobStatus(taskId);
      latest = job;
      updateRunProgress(job);
      if (["success", "fail", "cancelled", "timed_out"].includes(job.status.toLowerCase())) {
        return job;
      }
      await sleep(900);
    }
  }

  function updateRunProgress(job: JobStatusResponse) {
    const nextProgress = Math.min(100, Math.max(0, Math.round(job.progress || 0)));
    setProgress(nextProgress);
    setElapsedSeconds(Math.round(job.elapsedSeconds || 0));
    setLogText(job.rawStatus ? `RUNPOD STATUS : ${job.rawStatus.toUpperCase()}` : job.message || job.status);
    setLatestJob(job);
    setSegments((items) => {
      const count = Math.max(1, items.length);
      const range = 100 / count;
      return items.map((segment, index) => {
        const start = index * range;
        const segmentProgress = ((nextProgress - start) / range) * 100;
        return { ...segment, progress: Math.min(100, Math.max(0, Math.round(segmentProgress))) };
      });
    });
  }

  async function cancelGeneration() {
    if (!running || !currentTaskId || cancelRequested) {
      return;
    }
    setCancelRequested(true);
    setNotice("취소 요청을 보냈습니다.");
    try {
      const job = await apiClient.cancelJob(currentTaskId);
      updateRunProgress(job);
      setLatestJob(job);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Cancel failed");
      setCancelRequested(false);
    }
  }

  function resetRunState() {
    setRunning(false);
    setCancelRequested(false);
    setCurrentTaskId("");
    setProgress(0);
    setElapsedSeconds(0);
    setLogText("");
    setLatestJob(null);
    setOutputAssets([]);
  }

  return (
    <>
    <main className="studio-grid">
      <aside className="sidebar">
        <h2>Control Panel</h2>
        {segments.map((segment) => (
          <button
            className={`segment-card ${segment.index === selectedSegmentIndex ? "is-active" : ""}`}
            key={segment.index}
            type="button"
            onClick={() => setSelectedSegmentIndex(segment.index)}
          >
            <strong className="segment-name">{segmentTitleParts(segment.displayName).map((part, index) => (
              <span className={index === 0 ? "segment-name-main" : "segment-name-detail"} key={`${segment.index}-${part}-${index}`}>
                {part}
              </span>
            ))}</strong>
            <span>{segment.progress}%</span>
          </button>
        ))}
      </aside>
      <section className="work-panel">
        <div className="section-title">
          <h2>Workflow List</h2>
          <span>{health?.system?.database?.persistenceBackend || "json"}</span>
        </div>
        <select
          aria-describedby={workflowSelectionLocked ? "workflow-selection-lock" : undefined}
          disabled={workflowSelectionLocked}
          title={workflowSelectionLocked ? "생성 중에는 워크플로우를 변경할 수 없습니다." : undefined}
          value={selectedWorkflow}
          onChange={(event) => {
            if (workflowSelectionLocked) {
              setNotice("생성 중에는 워크플로우를 변경할 수 없습니다. 완료 또는 실패 후 다시 선택하세요.");
              return;
            }
            setSelectedWorkflow(event.target.value);
          }}
        >
          {workflows.map((workflow) => (
            <option key={workflow.id} value={workflow.id}>
              Workflow Type: Wan {workflow.label || workflow.name || workflow.id} ({workflow.keyframeCount || 1} keyframes)
            </option>
          ))}
        </select>
        {workflowSelectionLocked ? <p className="workflow-selection-lock" id="workflow-selection-lock">생성 중에는 워크플로우 변경이 잠깐 잠깁니다. 현재 작업이 완료 또는 실패하면 다시 선택할 수 있습니다.</p> : null}
        <div className="workflow-meta">
          <span>{schema?.keyframeCount || selected?.keyframeCount || 0} input image(s)</span>
          <span>{schema?.segmentCount || selected?.segmentCount || 0} subgraph segment(s)</span>
        </div>
        <div className="upload-row">
          {keyframes.map((keyframe) => (
            <label
              className={`upload-box ${activeImageIndexes.has(keyframe.index) ? "is-linked" : ""} ${keyframe.previewUrl ? "has-image" : ""}`}
              key={keyframe.index}
            >
              <input type="file" accept="image/*" multiple onChange={(event) => applySelectedFiles(keyframe.index, event.target.files)} />
              <span>Image {keyframe.index}</span>
              {keyframe.previewUrl ? <ProtectedImage src={keyframe.previewUrl} alt={`Input ${keyframe.index}`} /> : <b>Select Image</b>}
              <small>{keyframe.uploading ? "uploading..." : keyframe.error || keyframe.metaText}</small>
              {keyframe.previewUrl ? (
                <button type="button" onClick={(event) => { event.preventDefault(); clearKeyframe(keyframe.index); }}>
                  x
                </button>
              ) : null}
            </label>
          ))}
        </div>
        <label className="field">
          <span className="field-header">
            Positive Prompt
            <span className="field-actions">
              {canUse(user, "prompts:reuse") ? <button className="inline-action-button" type="button" onClick={() => void openPromptReuse()}>Prompt Reuse</button> : null}
              {canUse(user, "prompts:build") ? <button className="inline-action-button" type="button" onClick={() => void openPromptBuilder()}>Prompt Builder</button> : null}
            </span>
          </span>
          <textarea
            placeholder="프롬프트 입력"
            value={selectedSegment?.positivePrompt || ""}
            onChange={(event) => updateSelectedPrompt("positivePrompt", event.target.value)}
          />
        </label>
        <label className="field">
          <span>Negative Prompt</span>
          <textarea
            placeholder="네거티브 프롬프트 입력"
            value={selectedSegment?.negativePrompt || ""}
            onChange={(event) => updateSelectedPrompt("negativePrompt", event.target.value)}
          />
        </label>
        <div className="config-panel">
          <div className="node-config-title">
            <h3>Wan Node Config (ComfyUI)</h3>
            <button className="secondary-button compact-action-button" type="button" onClick={() => void resetSegmentConfigsToDefaults()}>
              세그먼트 설정 초기화
            </button>
          </div>
          {(selectedSegment?.configControls || []).filter((control) => control.key !== "seed" && control.key !== "Seed").map((control) => (
            <ConfigRow
              control={control}
              key={control.key}
              value={selectedSegment?.config[control.key] ?? control.default ?? ""}
              onChange={(value) => updateConfigValue(control.key, value, control)}
            />
          ))}
        </div>
        <div className="generation-actions">
          <button className="primary-button" type="button" disabled={running || !canUse(user, "jobs:run")} onClick={generateVideo}>
            {running ? "GENERATING..." : "GENERATE VIDEO"}
          </button>
          {running && canUse(user, "jobs:cancel") ? (
            <button className="secondary-danger-button" type="button" disabled={!currentTaskId || cancelRequested} onClick={cancelGeneration}>
              {cancelRequested ? "Cancelling..." : "Cancel Generation"}
            </button>
          ) : null}
        </div>
        {notice ? <p className="notice-text">{notice}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
      </section>
      <section className="preview-panel">
        <div className="section-title">
          <h2>Preview & Output</h2>
        </div>
        <div className="progress-card" style={{ "--progress": progress } as React.CSSProperties}>
          <strong>{progress}%</strong>
          <span>Generation Time: {formatElapsed(elapsedSeconds)}</span>
        </div>
        <div className="output-grid">
          <div className={`log-card ${hasFailedJob ? "is-failed" : ""}`}>
            <h3>Log Stream: ({progress}%)</h3>
            <p>{logText || selectedSegment?.positivePrompt || "Waiting for generation."}</p>
            {hasFailedJob && latestJob?.message ? <p>{latestJob.message}</p> : null}
          </div>
          <section className="video-column">
            <div className="video-toolbar">
              <span>View Subgraph:</span>
              <select value={selectedSegmentIndex} onChange={(event) => setSelectedSegmentIndex(Number(event.target.value))}>
                {segments.map((segment) => (
                  <option value={segment.index} key={segment.index}>{segment.displayName}</option>
                ))}
              </select>
            </div>
            {hasFailedJob ? (
              <div className="failure-card">
                <h3>Generation Failed</h3>
                <p>{latestJob?.message || logText || "작업이 실패했습니다. RunPod 로그를 확인하세요."}</p>
              </div>
            ) : null}
            {!hasSuccessfulOutput && !hasFailedJob ? (
              <div className="video-frame">
                <div className="neon-scene" aria-label="생성 영상 프리뷰" />
                <div className="player-bar"><span /><b>0:00</b><i /></div>
              </div>
            ) : null}
            <section className="generation-info">
              <h3>Generation Info</h3>
              {hasSuccessfulOutput ? (
                <div className="result-card generation-result-card">
                  <video src={displayOutputMediaUrl} controls playsInline preload="metadata" />
                  <div className="result-info">
                    <p>File: {displayOutput?.fileName || displayOutput?.assetId || "generated output"}</p>
                    <p>Applied Seed: {latestJob?.generationSeed || "-"}</p>
                    <p>FPS: {selectedSegment?.config.fps || selectedSegment?.config.FPS || "-"}</p>
                    <p>Segments: {segments.length}</p>
                  </div>
                  <button
                    className="primary-button"
                    type="button"
                    onClick={() => downloadProtectedAsset(displayOutputDownloadUrl, displayOutput?.fileName || "generated-output.mp4").catch((downloadError) => setError(downloadError instanceof Error ? downloadError.message : "영상 다운로드에 실패했습니다."))}
                  >
                    Download MP4
                  </button>
                </div>
              ) : null}
              <div className="info-row">
                <div className="thumb-scene" aria-hidden="true" />
                <div>
                  <p>Applied Seed: <strong>{latestJob?.generationSeed || "-"}</strong></p>
                  <p>FPS: <strong>{selectedSegment?.config.fps || selectedSegment?.config.FPS || "-"}</strong></p>
                </div>
              </div>
              <p className="prompt-summary">{selectedSegment?.positivePrompt || "생성 완료 후 결과 영상이 이 영역에 표시됩니다."}</p>
              <div className="segment-detail-text">
                {segmentDetailRows.map(([label, value]) => (
                  <p key={label}><span>{label}</span><strong>{value || "-"}</strong></p>
                ))}
              </div>
            </section>
            <div className="payload-card">
              <h3>Payload Preview</h3>
              <pre>{JSON.stringify(jobPayloadPreview, null, 2)}</pre>
            </div>
          </section>
        </div>
      </section>
    </main>
    {historyModalOpen ? (
      <HistoryModal
        history={history}
        page={historyPage}
        pageCount={historyPageCount}
        pageSize={historyPageSize}
        total={historyTotal}
        loading={historyLoading}
        selectedItem={selectedHistory}
        selectedTaskId={selectedHistoryTaskId}
        activeTab={historyTab}
        notice={modalNotice}
        promptReviewItems={promptReviewItems}
        promptReviewLoading={promptReviewLoading}
        promptReviewNotice={promptReviewNotice}
        onClose={() => onNavigate("studio")}
        onPageChange={(page) => void loadHistoryPage(page)}
        onPageSizeChange={changeHistoryPageSize}
        onSelect={(item) => {
          setSelectedHistoryTaskId(item.taskId);
          setHistoryTab("overview");
          setPromptReviewItems([]);
          setPromptReviewNotice("");
        }}
        onTabChange={setHistoryTab}
        onCopyPrompt={copyPromptList}
        onDownload={(item) => openOutputAsset(item)}
        onRework={(item) => void applyHistoryRework(item)}
        onDelete={setDeleteTarget}
        onSavePromptReview={(segmentIndex, payload) => void savePromptReview(segmentIndex, payload)}
        onSavePromptFeedback={(outputId, payload) => void savePromptFeedback(outputId, payload)}
        canRework={canUse(user, "jobs:run")}
        canDelete={canUse(user, "history:delete")}
        canReview={canUse(user, "prompts:review")}
        // B-03: POST /api/prompts/feedback가 이제 prompts:review를 요구한다(이전
        // prompts:build 시절엔 ADMIN처럼 review만 있고 build가 없는 역할은 저장
        // 버튼이 보여도 403이 났다 - B-02 커밋의 주석대로 여기서 맞춰 바꾼다).
        canGiveFeedback={canUse(user, "prompts:review")}
      />
    ) : null}
    {deleteTarget ? (
      <ConfirmDeleteModal
        item={deleteTarget}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => void deleteHistoryItem()}
      />
    ) : null}
    {statusModalOpen ? (
      <StatusModal
        status={systemStatus}
        connection={runpodConnection}
        loading={statusLoading}
        notice={statusNotice}
        onClose={() => onNavigate("studio")}
        onRefresh={() => void loadSystemStatus()}
        onTestRunpod={() => void testRunpodConnection()}
      />
    ) : null}
    {manualModalOpen ? (
      <ManualModal
        html={manualHtml}
        loading={manualLoading}
        error={manualError}
        onClose={() => onNavigate("studio")}
      />
    ) : null}
    {metadataModalOpen ? (
      <MetadataModal
        workflows={workflows}
        workflowId={metadataWorkflowId}
        activeTab={metadataTab}
        status={metadataStatus}
        metadata={workflowMetadata}
        models={modelMetadata}
        loading={metadataLoading}
        notice={metadataNotice}
        onClose={() => onNavigate("studio")}
        onWorkflowChange={(workflowId) => void loadMetadata(workflowId)}
        onTabChange={setMetadataTab}
        onRebuild={() => void rebuildMetadata()}
      />
    ) : null}
    {adminModalOpen ? (
      <AdminConsoleModal
        user={user}
        onClose={() => onNavigate("studio")}
        catalog={promptCatalog}
        catalogLoading={promptBuilderLoading}
        catalogNotice={promptBuilderNotice}
        onCatalogVisible={() => {
          if (!promptCatalog && !promptBuilderLoading) {
            void loadPromptCatalog();
          }
        }}
        onSaveCategoryGroup={(payload, groupId) => void savePromptCategoryGroup(payload, groupId)}
        onDeactivateCategoryGroup={(groupId) => void deactivatePromptCategoryGroup(groupId)}
        onSaveCategory={(payload, categoryId) => void savePromptCategory(payload, categoryId)}
        onDeactivateCategory={(categoryId) => void deactivatePromptCategory(categoryId)}
        onSaveTerm={(payload, termId) => void savePromptTerm(payload, termId)}
        onDeactivateTerm={(termId) => void deactivatePromptTerm(termId)}
        onWorkflowChanged={(workflowId) => void loadWorkflows(workflowId)}
      />
    ) : null}
    {accessDeniedRoute ? (
      <AccessDeniedModal
        routeLabel={ROUTE_LABEL[accessDeniedRoute] || accessDeniedRoute}
        onClose={() => onNavigate("studio")}
      />
    ) : null}
    {promptBuilderOpen ? (
      <PromptBuilderModal
        catalog={promptCatalog}
        loading={promptBuilderLoading}
        notice={promptBuilderNotice}
        selectedTermIds={promptSelectedTermIds}
        activePanel={promptBuilderPanel}
        systemPrompt={promptSystemPrompt}
        systemPromptText={promptSystemPromptText}
        scene={promptScene}
        generated={promptGenerated}
        sceneDescription={promptSceneDescription}
        workflowName={selected?.label || selected?.name || selectedWorkflow}
        segmentName={selectedSegment?.displayName || ""}
        baseNegativePrompt={selectedSegment?.defaultNegativePrompt || selectedSegment?.negativePrompt || ""}
        onClose={() => setPromptBuilderOpen(false)}
        onRefreshBuilder={() => void refreshPromptBuilder()}
        onReloadSystemPrompt={() => void loadPromptSystemPrompt()}
        onSaveSystemPrompt={() => void savePromptSystemPrompt()}
        onSystemPromptTextChange={setPromptSystemPromptText}
        onPanelChange={setPromptBuilderPanel}
        onToggleTerm={togglePromptTerm}
        onSceneDescriptionChange={(value) => {
          setPromptSceneDescription(value);
          setPromptScene(null);
          setPromptGenerated(null);
        }}
        onClearSelection={clearPromptBuilderSelection}
        onGenerate={() => void generatePromptDraft()}
        onApply={applyPromptSceneToSegment}
      />
    ) : null}
    {promptReuseOpen ? (
      <PromptReuseModal
        keyword={promptReuseKeyword}
        items={promptReuseItems}
        loading={promptReuseLoading}
        notice={promptReuseNotice}
        workflowName={selected?.label || selected?.name || selectedWorkflow}
        onKeywordChange={setPromptReuseKeyword}
        onSearch={() => void searchPromptReuse()}
        onClose={() => setPromptReuseOpen(false)}
        onApply={applyReusablePrompt}
      />
    ) : null}
    {promptCatalogAdminOpen ? (
      <PromptCatalogAdminModal
        catalog={promptCatalog}
        loading={promptBuilderLoading}
        notice={promptBuilderNotice}
        onClose={() => setPromptCatalogAdminOpen(false)}
        onSaveCategoryGroup={(payload, groupId) => void savePromptCategoryGroup(payload, groupId)}
        onDeactivateCategoryGroup={(groupId) => void deactivatePromptCategoryGroup(groupId)}
        onSaveCategory={(payload, categoryId) => void savePromptCategory(payload, categoryId)}
        onDeactivateCategory={(categoryId) => void deactivatePromptCategory(categoryId)}
        onSaveTerm={(payload, termId) => void savePromptTerm(payload, termId)}
        onDeactivateTerm={(termId) => void deactivatePromptTerm(termId)}
      />
    ) : null}
    </>
  );
}

type PromptCatalogRenderGroup = {
  key: string;
  label: string;
  sortOrder: number;
  categories: PromptCategory[];
};

type PromptCatalogRenderScope = {
  key: "positive" | "negative";
  label: string;
  termCount: number;
  groups: PromptCatalogRenderGroup[];
};

function allPromptCatalogTerms(categories: PromptCategory[]) {
  return categories.flatMap((category) => category.terms || []);
}

function promptCatalogCategories(catalog: PromptCatalogResponse | null): PromptCategory[] {
  // B-06 3단계: 백엔드가 구형 "categories" 배열을 완전히 제거했다("groups"가 유일한
  // canonical 응답). 이제 신형 groups[].subcategories[]만 평탄화한다 - 구형 fallback은
  // 더 이상 존재하지 않는다(항상 stale이었을 것이므로 제거가 맞다).
  const groups = catalog?.groups || [];
  return groups.flatMap((group) => (
    group.subcategories || []
  ).map((subcategory) => ({
    ...subcategory,
    groupId: group.id,
    groupCode: group.code,
    groupNameKo: group.nameKo,
    groupNameEn: group.nameEn,
    groupSortOrder: group.sortOrder,
    scopeType: group.scopeCode || group.scopeType || subcategory.scopeType
  })));
}

function promptCatalogHasTerms(catalog: PromptCatalogResponse | null) {
  return promptCatalogCategories(catalog).some((category) => category.terms?.length);
}

function selectedPromptKeywordsByScope(categories: PromptCategory[], selectedTermIds: number[]) {
  const selectedIds = new Set(selectedTermIds);
  const selected = {
    positive: [] as PromptTerm[],
    negative: [] as PromptTerm[]
  };
  for (const category of categories) {
    const scopeKey = promptCategoryScopeKey(category);
    for (const keyword of category.terms || []) {
      if (!selectedIds.has(keyword.id)) {
        continue;
      }
      selected[scopeKey].push(keyword);
    }
  }
  return selected;
}

function promptCatalogRenderScopes(categories: PromptCategory[], includeEmptyCategories = false): PromptCatalogRenderScope[] {
  const scopes = new Map<"positive" | "negative", Map<string, PromptCategory[]>>();

  for (const category of categories) {
    if (FIXED_PROMPT_ROOT_CODES.has(category.code)) {
      continue;
    }
    if (!includeEmptyCategories && !(category.terms || []).length) {
      continue;
    }
    const scopeKey = promptCategoryScopeKey(category);
    const groupKey = promptCategoryGroupKey(category);
    const scopeGroups = scopes.get(scopeKey) || new Map<string, PromptCategory[]>();
    const groupCategories = scopeGroups.get(groupKey) || [];
    groupCategories.push(category);
    scopeGroups.set(groupKey, groupCategories);
    scopes.set(scopeKey, scopeGroups);
  }

  return PROMPT_SCOPE_ORDER.map((scopeKey) => {
    const typedScopeKey = scopeKey as "positive" | "negative";
    const scopeGroups = scopes.get(typedScopeKey) || new Map<string, PromptCategory[]>();
    const groups = Array.from(scopeGroups.entries())
      .sort(([leftKey, leftCategories], [rightKey, rightCategories]) => {
        const leftOrder = leftCategories[0]?.groupSortOrder ?? 1000;
        const rightOrder = rightCategories[0]?.groupSortOrder ?? 1000;
        if (leftOrder === rightOrder) {
          return leftKey.localeCompare(rightKey);
        }
        return leftOrder - rightOrder;
      })
      .map(([groupKey, groupCategories]) => ({
        key: groupKey,
        label: groupCategories[0]?.groupNameKo || groupCategories[0]?.groupNameEn || groupKey,
        sortOrder: groupCategories[0]?.groupSortOrder ?? 1000,
        categories: [...groupCategories].sort((left, right) => (left.sortOrder || 100) - (right.sortOrder || 100))
      }));
    return {
      key: typedScopeKey,
      label: typedScopeKey === "negative" ? "Negative" : "Positive",
      termCount: groups.reduce((count, group) => count + group.categories.reduce((innerCount, category) => innerCount + (category.terms || []).length, 0), 0),
      groups
    };
  }).filter((scope) => scope.groups.length);
}

function promptCategoryScopeKey(category: PromptCategory): "positive" | "negative" {
  // B-06 3단계(TASKS.md 2단계 항목): 프론트가 참조하던 groupCode 문자열 접두어 휴리스틱
  // ("negative"로 시작하는지)을 백엔드가 내려주는 scopeCode(POSITIVE/NEGATIVE)로 대체한다.
  // promptCatalogCategories()가 groups[].subcategories[]를 평탄화하며 이미
  // category.scopeType에 그룹의 scopeCode를 채워 넣으므로(위 함수 참조) 여기서는 그 값만
  // 읽으면 된다. 구형 catalog.categories 경로(parentCategoryId/ROOT 기반)는 더 이상
  // 응답에 존재하지 않으므로 categoryById 기반 fallback도 함께 제거한다.
  const scopeCode = String(category.scopeType || "").toUpperCase();
  if (scopeCode === "NEGATIVE") {
    return "negative";
  }
  if (scopeCode === "POSITIVE") {
    return "positive";
  }
  // 방어적 fallback: scopeCode가 없는 예상 밖의 데이터에 한해서만 코드 접두어를 본다.
  const categoryCode = category.code.toUpperCase();
  return categoryCode.startsWith("NEGATIVE_") ? "negative" : "positive";
}

function promptCategoryGroupKey(category: PromptCategory) {
  const groupCode = (category.groupCode || "").toLowerCase();
  return groupCode || "uncategorized";
}

function promptScopeAccordionKey(scopeKey: string) {
  return `scope:${scopeKey}`;
}

function promptGroupAccordionKey(scopeKey: string, groupKey: string) {
  return `group:${scopeKey}:${groupKey}`;
}

function promptCategoryAccordionKey(scopeKey: string, groupKey: string, categoryCode: string) {
  return `category:${scopeKey}:${groupKey}:${categoryCode}`;
}

function promptAccordionDefaultKeys() {
  return new Set<string>();
}

type PromptCatalogAdminScope = {
  key: "positive" | "negative";
  label: string;
  groups: PromptCategoryGroup[];
};

type AdminTab = "users" | "permissions" | "workflows" | "catalog" | "sandbox";

const ADMIN_ROLE_GUIDE = [
  { role: "SUPER_ADMIN", description: "전체 운영 및 시스템 설정 권한. 기본 관리자 계정에만 권장합니다." },
  { role: "ADMIN", description: "사용자, 워크플로우, Prompt Catalog 등 운영 관리 권한." },
  { role: "OPERATOR", description: "영상 생성, 작업 조회, 프롬프트 리뷰 등 실무 작업 권한." },
  { role: "VIEWER", description: "작업과 결과 조회 중심의 읽기 전용 권한." }
];

const ADMIN_PERMISSION_OPTIONS = [
  { value: "admin:*", label: "Admin 전체", description: "관리자 기능 전체 접근" },
  { value: "users:read", label: "사용자 조회", description: "사용자 목록과 상세 조회" },
  { value: "users:write", label: "사용자 수정", description: "사용자 등록, 수정, 상태 변경" },
  { value: "roles:read", label: "역할/권한 조회", description: "역할과 권한 그룹 조회" },
  { value: "roles:write", label: "역할/권한 수정", description: "역할별 권한 구성 변경" },
  { value: "workflows:read", label: "워크플로우 조회", description: "워크플로우 목록과 메타데이터 조회" },
  { value: "workflows:write", label: "워크플로우 수정", description: "워크플로우 등록과 수정" },
  { value: "workflows:activate", label: "워크플로우 활성화", description: "워크플로우 활성화와 비활성화" },
  { value: "prompt-catalog:read", label: "카탈로그 조회", description: "Prompt Catalog 조회" },
  { value: "prompt-catalog:write", label: "카탈로그 수정", description: "카테고리, 서브 카테고리, 키워드 관리" },
  { value: "jobs:run", label: "작업 실행", description: "영상 생성 작업 제출" },
  { value: "jobs:cancel", label: "작업 취소", description: "RunPod 생성 작업 취소" },
  { value: "history:read", label: "작업 이력 조회", description: "작업 결과와 이력 조회" },
  { value: "history:delete", label: "작업 이력 삭제", description: "작업과 관련 asset 삭제" },
  { value: "prompts:build", label: "프롬프트 생성", description: "Prompt Builder와 Qwen 프롬프트 생성" },
  { value: "prompts:reuse", label: "프롬프트 재사용", description: "재사용 가능 프롬프트 검색과 적용" },
  { value: "prompts:review", label: "프롬프트 리뷰", description: "품질 등급, 코멘트, 재사용 가능 여부 관리" },
  { value: "metadata:read", label: "메타데이터 조회", description: "Workflow metadata 조회" },
  { value: "metadata:rebuild", label: "메타데이터 재생성", description: "Workflow metadata rebuild" },
  { value: "system:read", label: "시스템 상태 조회", description: "ComfyUI/Qwen/DB 상태 확인" },
  { value: "manual:read", label: "사용자 매뉴얼 조회", description: "사용자 매뉴얼 조회" },
  { value: "sandbox:read", label: "Sandbox Pod 조회", description: "전용 RunPod Pod 상태와 HTTP 서비스 조회" },
  { value: "sandbox:control", label: "Sandbox Pod 제어", description: "전용 RunPod Pod 시작 및 중지" }
];

function adminUserFormFrom(user: AdminUser | null): Record<string, string> {
  return {
    id: user?.id || "",
    name: user?.name || "",
    role: user?.role || "OPERATOR",
    isActive: user?.isActive === false ? "false" : "true",
    permissions: (user?.extraPermissionCodes || user?.permissions || []).join(", "),
    password: ""
  };
}

function adminPermissionsFromText(value: string): string[] {
  return value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function adminPermissionsToText(values: string[]) {
  return Array.from(new Set(values.map((item) => item.trim()).filter(Boolean))).join(", ");
}

function adminPermissionOptions(governance: PermissionGovernance | null) {
  if (governance?.permissions?.length) {
    return governance.permissions
      .filter((item) => item.isActive)
      .map((item) => ({
        value: item.code,
        label: item.name,
        description: item.description || `${item.domain}:${item.action}`
      }));
  }
  return ADMIN_PERMISSION_OPTIONS;
}

function adminRoleOptions(governance: PermissionGovernance | null) {
  if (governance?.roles?.length) {
    return governance.roles.filter((item) => item.isActive);
  }
  return ADMIN_ROLE_GUIDE.map((item, index) => ({
    id: index + 1,
    code: item.role,
    name: item.role,
    description: item.description,
    level: 0,
    isSystem: true,
    isActive: true,
    sortOrder: index + 1,
    permissionCodes: []
  }));
}

function adminRolePermissionCodes(governance: PermissionGovernance | null, roleCode: string) {
  return adminRoleOptions(governance).find((item) => item.code === roleCode)?.permissionCodes || [];
}

function adminPermissionLabel(governance: PermissionGovernance | null, permissionCode: string) {
  return adminPermissionOptions(governance).find((item) => item.value === permissionCode)?.label || permissionCode;
}

function promptCatalogAdminScopes(groups: PromptCategoryGroup[]): PromptCatalogAdminScope[] {
  const grouped = {
    positive: [] as PromptCategoryGroup[],
    negative: [] as PromptCategoryGroup[]
  };
  for (const group of groups) {
    const scope = String(group.scopeCode || group.scopeType || "").toUpperCase() === "NEGATIVE" ? "negative" : "positive";
    grouped[scope].push(group);
  }
  const scopes: PromptCatalogAdminScope[] = [
    {
      key: "positive",
      label: "Positive",
      groups: [...grouped.positive].sort((left, right) => (left.sortOrder || 100) - (right.sortOrder || 100))
    },
    {
      key: "negative",
      label: "Negative",
      groups: [...grouped.negative].sort((left, right) => (left.sortOrder || 100) - (right.sortOrder || 100))
    }
  ];
  return scopes.filter((scope) => scope.groups.length);
}

function promptAdminScopeAccordionKey(scopeKey: string) {
  return `admin-scope:${scopeKey}`;
}

function promptAdminGroupAccordionKey(scopeKey: string, groupId: number) {
  return `admin-group:${scopeKey}:${groupId}`;
}

function promptAdminSubcategoryAccordionKey(subcategoryId: number) {
  return `admin-subcategory:${subcategoryId}`;
}

function AdminConsoleModal({
  user,
  onClose,
  catalog,
  catalogLoading,
  catalogNotice,
  onCatalogVisible,
  onSaveCategoryGroup,
  onDeactivateCategoryGroup,
  onSaveCategory,
  onDeactivateCategory,
  onSaveTerm,
  onDeactivateTerm,
  onWorkflowChanged
}: {
  user: User;
  onClose: () => void;
  catalog: PromptCatalogResponse | null;
  catalogLoading: boolean;
  catalogNotice: string;
  onCatalogVisible: () => void;
  onSaveCategoryGroup: (payload: Record<string, unknown>, groupId?: number) => void;
  onDeactivateCategoryGroup: (groupId: number) => void;
  onSaveCategory: (payload: Record<string, unknown>, categoryId?: number) => void;
  onDeactivateCategory: (categoryId: number) => void;
  onSaveTerm: (payload: Record<string, unknown>, termId?: number) => void;
  onDeactivateTerm: (termId: number) => void;
  onWorkflowChanged: (workflowId?: string) => void;
}) {
  const canManageUsers = canUseAdminUsers(user);
  const canManagePermissions = canUseAdminPermissions(user);
  const canManageWorkflows = canUseAdminWorkflows(user);
  const canManageCatalog = canUseAdminCatalog(user);
  const canManageSandboxPod = canUseAdminSandboxPod(user);
  const availableAdminTabs = [
    canManageUsers ? "users" : null,
    canManagePermissions ? "permissions" : null,
    canManageWorkflows ? "workflows" : null,
    canManageCatalog ? "catalog" : null,
    canManageSandboxPod ? "sandbox" : null
  ].filter(Boolean) as AdminTab[];
  const [activeTab, setActiveTab] = useState<AdminTab>(availableAdminTabs[0] || "users");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [workflows, setWorkflows] = useState<AdminWorkflow[]>([]);
  const [permissionGovernance, setPermissionGovernance] = useState<PermissionGovernance | null>(null);
  const [selectedRoleCode, setSelectedRoleCode] = useState("");
  const selectedAdminRole = adminRoleOptions(permissionGovernance).find((item) => item.code === selectedRoleCode) || adminRoleOptions(permissionGovernance)[0] || null;
  const [rolePermissionDraft, setRolePermissionDraft] = useState<string[]>([]);
  const [selectedUserId, setSelectedUserId] = useState("");
  const selectedUser = users.find((item) => item.id === selectedUserId) || null;
  const selectedUserIsDefaultAdmin = selectedUser?.id === "dobedub";
  const [userForm, setUserForm] = useState<Record<string, string>>(() => adminUserFormFrom(null));
  const [selectedAdminWorkflowId, setSelectedAdminWorkflowId] = useState("");
  const selectedAdminWorkflow = workflows.find((item) => item.id === selectedAdminWorkflowId) || null;
  const [workflowForm, setWorkflowForm] = useState<Record<string, string>>({
    workflowId: "",
    description: "",
    workflowJson: "",
    paramConfigJson: ""
  });
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [sandboxPod, setSandboxPod] = useState<SandboxPodStatus | null>(null);
  const [sandboxPodLoading, setSandboxPodLoading] = useState(false);
  const [sandboxPodPendingAction, setSandboxPodPendingAction] = useState<"start" | "stop" | null>(null);
  const sandboxPodAutoLoadAttempted = useRef(false);

  useEffect(() => {
    void loadAdminData();
  }, []);

  useEffect(() => {
    if (!availableAdminTabs.includes(activeTab)) {
      setActiveTab(availableAdminTabs[0] || "users");
    }
  }, [activeTab, availableAdminTabs.join("|")]);

  useEffect(() => {
    if (activeTab === "catalog" && canManageCatalog && !catalog && !catalogLoading) {
      onCatalogVisible();
    }
  }, [activeTab, canManageCatalog, catalog, catalogLoading]);

  useEffect(() => {
    if (activeTab !== "sandbox") {
      sandboxPodAutoLoadAttempted.current = false;
      return;
    }
    if (canManageSandboxPod && !sandboxPodAutoLoadAttempted.current) {
      sandboxPodAutoLoadAttempted.current = true;
      void loadSandboxPod();
    }
  }, [activeTab, canManageSandboxPod]);

  useEffect(() => {
    setUserForm(adminUserFormFrom(selectedUser));
  }, [selectedUserId, users]);

  useEffect(() => {
    const roles = adminRoleOptions(permissionGovernance);
    if (!roles.length) {
      setSelectedRoleCode("");
      setRolePermissionDraft([]);
      return;
    }
    const nextRole = roles.find((item) => item.code === selectedRoleCode) || roles[0];
    if (nextRole.code !== selectedRoleCode) {
      setSelectedRoleCode(nextRole.code);
    }
    setRolePermissionDraft([...(nextRole.permissionCodes || [])]);
  }, [permissionGovernance, selectedRoleCode]);

  async function loadAdminData() {
    setLoading(true);
    setNotice("");
    try {
      const [userResponse, permissionResponse, workflowResponse] = await Promise.all([
        canManageUsers ? apiClient.adminUsers() : Promise.resolve(null),
        canManagePermissions && !canManageUsers ? apiClient.adminPermissions() : Promise.resolve(null),
        canManageWorkflows ? apiClient.adminWorkflows() : Promise.resolve(null)
      ]);
      const nextPermissionGovernance = userResponse?.permissionGovernance || permissionResponse || null;
      setUsers(userResponse?.items || []);
      setWorkflows(workflowResponse?.items || []);
      setPermissionGovernance(nextPermissionGovernance);
      const roles = adminRoleOptions(nextPermissionGovernance);
      if (roles.length && !selectedRoleCode) {
        setSelectedRoleCode(roles[0].code);
      }
      if (canManageUsers && !selectedUserId) {
        setSelectedUserId(userResponse?.items?.[0]?.id || "");
      }
      if (canManageWorkflows && !selectedAdminWorkflowId) {
        setSelectedAdminWorkflowId(workflowResponse?.items?.[0]?.id || "");
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Admin data load failed");
    } finally {
      setLoading(false);
    }
  }

  async function saveUser() {
    setLoading(true);
    setNotice("");
    try {
      const payload = {
        id: userForm.id,
        name: userForm.name,
        role: userForm.role,
        permissions: adminPermissionsFromText(userForm.permissions),
        isActive: userForm.isActive === "true",
        password: userForm.password
      };
      const response = await apiClient.saveAdminUser(payload, selectedUser?.id);
      setUsers(response.items || []);
      setSelectedUserId(response.user?.id || userForm.id);
      setNotice("사용자 정보를 저장했습니다.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "User save failed");
    } finally {
      setLoading(false);
    }
  }

  function toggleUserPermission(permission: string) {
    const rolePermissions = adminRolePermissionCodes(permissionGovernance, userForm.role);
    if (rolePermissions.includes(permission)) {
      return;
    }
    const current = adminPermissionsFromText(userForm.permissions);
    const next = current.includes(permission)
      ? current.filter((item) => item !== permission)
      : [...current, permission];
    setUserForm({ ...userForm, permissions: adminPermissionsToText(next) });
  }

  function toggleRolePermission(permission: string) {
    if (selectedAdminRole?.code === "SUPER_ADMIN" && permission === "admin:*") {
      return;
    }
    setRolePermissionDraft((current) => current.includes(permission)
      ? current.filter((item) => item !== permission)
      : [...current, permission]);
  }

  async function saveRolePermissions() {
    if (!selectedAdminRole) {
      return;
    }
    setLoading(true);
    setNotice("");
    try {
      const response = await apiClient.saveAdminRolePermissions(selectedAdminRole.code, rolePermissionDraft);
      setPermissionGovernance(response);
      setNotice(`${selectedAdminRole.code} 권한 구성을 저장했습니다.`);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Role permission save failed");
    } finally {
      setLoading(false);
    }
  }

  async function saveWorkflow() {
    setLoading(true);
    setNotice("");
    try {
      const workflowJson = JSON.parse(workflowForm.workflowJson || "{}");
      const paramConfigJson = workflowForm.paramConfigJson.trim() ? JSON.parse(workflowForm.paramConfigJson) : undefined;
      const response = await apiClient.registerAdminWorkflow({
        workflowId: workflowForm.workflowId,
        description: workflowForm.description,
        workflowJson,
        paramConfigJson,
        active: false
      });
      setWorkflows(response.items || []);
      const savedWorkflowId = response.registeredWorkflowId || (workflowForm.workflowId.endsWith(".json") ? workflowForm.workflowId : `${workflowForm.workflowId}.json`);
      setSelectedAdminWorkflowId(savedWorkflowId);
      if (response.paramConfigJson) {
        setWorkflowForm((current) => ({
          ...current,
          workflowId: savedWorkflowId,
          paramConfigJson: JSON.stringify(response.paramConfigJson, null, 2)
        }));
      }
      setNotice(response.paramConfigGenerated
        ? "워크플로우를 등록하고 Param Config, 세그먼트 기본값, Metadata를 자동 갱신했습니다."
        : "워크플로우를 등록하고 세그먼트 기본값과 Metadata를 갱신했습니다. 검토 후 활성화하세요.");
      onWorkflowChanged();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Workflow register failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadWorkflowFile(event: React.ChangeEvent<HTMLInputElement>, target: "workflowJson" | "paramConfigJson") {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }
    setNotice("");
    try {
      const text = await file.text();
      JSON.parse(text);
      setWorkflowForm((current) => ({
        ...current,
        workflowId: target === "workflowJson" && !current.workflowId ? file.name : current.workflowId,
        [target]: text
      }));
      setSelectedAdminWorkflowId("");
      setNotice(target === "workflowJson" ? "워크플로우 JSON을 불러왔습니다. 내용을 확인 후 저장하세요." : "Param Config JSON을 불러왔습니다.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "JSON file load failed");
    }
  }

  function startNewWorkflowRegistration() {
    setSelectedAdminWorkflowId("");
    setWorkflowForm({
      workflowId: "",
      description: "",
      workflowJson: "",
      paramConfigJson: ""
    });
    setNotice("워크플로우 JSON 파일을 불러온 뒤 저장하세요.");
  }

  async function setWorkflowActive(workflowId: string, active: boolean) {
    setLoading(true);
    setNotice("");
    try {
      const response = active
        ? await apiClient.activateAdminWorkflow(workflowId)
        : await apiClient.deactivateAdminWorkflow(workflowId);
      setWorkflows(response.items || []);
      setNotice(active ? "워크플로우를 활성화했습니다." : "워크플로우를 비활성화했습니다.");
      onWorkflowChanged(active ? workflowId : undefined);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Workflow status update failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadSandboxPod() {
    setSandboxPodLoading(true);
    setNotice("");
    try {
      setSandboxPod(await apiClient.sandboxPodStatus());
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Sandbox Pod status load failed");
    } finally {
      setSandboxPodLoading(false);
    }
  }

  async function controlSandboxPod(action: "start" | "stop") {
    setSandboxPodLoading(true);
    setNotice("");
    try {
      const response = action === "start" ? await apiClient.startSandboxPod() : await apiClient.stopSandboxPod();
      setSandboxPod(response);
      setNotice(response.message || (action === "start" ? "Sandbox Pod 시작을 요청했습니다." : "Sandbox Pod 중지를 요청했습니다."));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Sandbox Pod control failed");
    } finally {
      setSandboxPodLoading(false);
    }
  }

  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="adminTitle" onMouseDown={(event) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    }}>
      <section className="admin-modal">
        <div className="modal-header">
          <div>
            <h2 id="adminTitle">Admin Console</h2>
            <p>사용자, 워크플로우, Prompt Catalog 및 Sandbox Pod 운영 관리를 수행합니다.</p>
          </div>
          <div className="modal-actions">
            <button className="icon-button" type="button" onClick={onClose}>x</button>
          </div>
        </div>
        {notice ? <p className="modal-notice">{notice}</p> : null}
        <div className="detail-tabs admin-tabs" role="tablist" aria-label="Admin sections">
          {canManageUsers ? <button className={activeTab === "users" ? "is-active" : ""} type="button" onClick={() => setActiveTab("users")}>Users</button> : null}
          {canManagePermissions ? <button className={activeTab === "permissions" ? "is-active" : ""} type="button" onClick={() => setActiveTab("permissions")}>Roles & Permissions</button> : null}
          {canManageWorkflows ? <button className={activeTab === "workflows" ? "is-active" : ""} type="button" onClick={() => setActiveTab("workflows")}>Workflows</button> : null}
          {canManageCatalog ? <button className={activeTab === "catalog" ? "is-active" : ""} type="button" onClick={() => setActiveTab("catalog")}>Prompt Catalog</button> : null}
          {canManageSandboxPod ? <button className={activeTab === "sandbox" ? "is-active" : ""} type="button" onClick={() => setActiveTab("sandbox")}>Sandbox Pod</button> : null}
        </div>
        {!availableAdminTabs.length ? <p className="modal-notice">사용 가능한 Admin 관리 권한이 없습니다.</p> : null}
        {activeTab === "users" && canManageUsers ? (
          <div className="admin-layout admin-user-layout">
            <aside className="admin-list">
              <div className="section-title"><h3>사용자</h3><span>{users.length}</span></div>
              <button className="secondary-button" type="button" onClick={() => {
                setSelectedUserId("");
                setUserForm(adminUserFormFrom(null));
              }}>New User</button>
              <div className="admin-user-list-header" aria-hidden="true">
                <span>Name</span>
                <span>Role</span>
                <span>State</span>
              </div>
              {users.map((item) => (
                <button className={`admin-user-row ${selectedUserId === item.id ? "is-selected" : ""}`} type="button" key={item.id} onClick={() => setSelectedUserId(item.id)}>
                  <strong>{item.name || item.id}</strong>
                  <span>{item.role}</span>
                  <small className={`admin-status-badge ${item.isActive === false ? "is-inactive" : "is-active"}`}>{item.isActive === false ? "INACTIVE" : "ACTIVE"}</small>
                </button>
              ))}
            </aside>
            <section className="admin-form admin-user-form">
              <div className="section-title">
                <h3>{selectedUser ? "사용자 정보" : "사용자 등록"}</h3>
                <span>{selectedUser?.isActive === false ? "INACTIVE" : selectedUser ? "ACTIVE" : "NEW"}</span>
              </div>
              <div className="admin-user-field-grid">
                <label><span>ID</span><input value={userForm.id} disabled={Boolean(selectedUser)} onChange={(event) => setUserForm({ ...userForm, id: event.target.value })} /></label>
                <label><span>Name</span><input value={userForm.name} onChange={(event) => setUserForm({ ...userForm, name: event.target.value })} /></label>
                <label><span>Password</span><input type="password" value={userForm.password} placeholder={selectedUser ? "변경 시에만 입력" : "초기 비밀번호"} onChange={(event) => setUserForm({ ...userForm, password: event.target.value })} /></label>
                <label><span>Role</span><select value={userForm.role} onChange={(event) => setUserForm({ ...userForm, role: event.target.value, permissions: adminPermissionsToText(adminPermissionsFromText(userForm.permissions).filter((permission) => !adminRolePermissionCodes(permissionGovernance, event.target.value).includes(permission))) })}>
                  {adminRoleOptions(permissionGovernance).map((role) => <option value={role.code} key={role.code}>{role.code}</option>)}
                </select></label>
                <label><span>State</span><select value={selectedUserIsDefaultAdmin ? "true" : userForm.isActive} disabled={selectedUserIsDefaultAdmin} onChange={(event) => setUserForm({ ...userForm, isActive: event.target.value })}>
                  <option value="true">ACTIVE</option>
                  <option value="false">INACTIVE</option>
                </select></label>
              </div>
              {selectedUserIsDefaultAdmin ? <p className="muted-text">기본 SUPER_ADMIN 계정은 시스템 잠금 방지를 위해 비활성화할 수 없습니다.</p> : null}
              <section className="admin-role-guide">
                <h4>Role Guide</h4>
                <dl>
                  {adminRoleOptions(permissionGovernance).map((item) => (
                    <div className={userForm.role === item.code ? "is-selected" : ""} key={item.code}>
                      <dt>{item.code}</dt>
                      <dd>{item.description || item.name}</dd>
                    </div>
                  ))}
                </dl>
              </section>
              <section className="admin-permission-guide">
                <div className="section-title">
                  <h4>Role Default Permissions</h4>
                  <span>{adminRolePermissionCodes(permissionGovernance, userForm.role).length}</span>
                </div>
                <div className="admin-permission-chip-grid">
                  {adminRolePermissionCodes(permissionGovernance, userForm.role).map((permission) => (
                    <span className="permission-chip is-role" key={permission}><strong>{permission}</strong>{adminPermissionLabel(permissionGovernance, permission)}</span>
                  ))}
                  {!adminRolePermissionCodes(permissionGovernance, userForm.role).length ? <p className="muted-text">선택한 role의 기본 권한이 없습니다.</p> : null}
                </div>
              </section>
              <section className="admin-permission-guide">
                <div className="section-title">
                  <h4>Extra Permissions</h4>
                  <span>{adminPermissionsFromText(userForm.permissions).length} selected</span>
                </div>
                <div className="admin-permission-options">
                  {adminPermissionOptions(permissionGovernance).map((item) => {
                    const rolePermission = adminRolePermissionCodes(permissionGovernance, userForm.role).includes(item.value);
                    const selected = adminPermissionsFromText(userForm.permissions).includes(item.value);
                    return (
                      <button className={`${selected ? "is-selected" : ""} ${rolePermission ? "is-disabled" : ""}`} disabled={rolePermission} key={item.value} type="button" onClick={() => toggleUserPermission(item.value)}>
                        <strong>{item.value}</strong>
                        <span>{rolePermission ? "Role 기본 권한" : `${item.label} · ${item.description}`}</span>
                      </button>
                    );
                  })}
                </div>
                <p className="muted-text">Role 기본 권한은 여기서 중복 선택하지 않습니다. 사용자 예외 권한만 추가로 선택합니다.</p>
              </section>
              <section className="admin-permission-guide">
                <div className="section-title">
                  <h4>Effective Permissions</h4>
                  <span>{Array.from(new Set([...adminRolePermissionCodes(permissionGovernance, userForm.role), ...adminPermissionsFromText(userForm.permissions)])).length}</span>
                </div>
                <div className="admin-permission-chip-grid">
                  {Array.from(new Set([...adminRolePermissionCodes(permissionGovernance, userForm.role), ...adminPermissionsFromText(userForm.permissions)])).map((permission) => (
                    <span className="permission-chip" key={permission}><strong>{permission}</strong>{adminPermissionLabel(permissionGovernance, permission)}</span>
                  ))}
                </div>
              </section>
              <div className="modal-actions">
                <button className="primary-button" type="button" disabled={loading || !canUse(user, "users:write") || !userForm.id || !userForm.name} onClick={() => void saveUser()}>Save User</button>
              </div>
            </section>
          </div>
        ) : null}
        {activeTab === "permissions" && canManagePermissions ? (
          <div className="admin-layout admin-permissions-layout">
            <aside className="admin-list">
              <div className="section-title"><h3>Roles</h3><span>{permissionGovernance?.roles?.length || 0}</span></div>
              {adminRoleOptions(permissionGovernance).map((role) => (
                <button
                  className={`admin-row ${selectedAdminRole?.code === role.code ? "is-selected" : ""} ${role.isActive ? "is-active" : ""}`}
                  key={role.code}
                  type="button"
                  onClick={() => {
                    setSelectedRoleCode(role.code);
                    setRolePermissionDraft([...(role.permissionCodes || [])]);
                  }}
                >
                  <strong>{role.code}</strong>
                  <span>{role.description || role.name}</span>
                  <small className={`admin-status-badge ${role.isActive ? "is-active" : "is-inactive"}`}>{role.isActive ? "ACTIVE" : "INACTIVE"}</small>
                </button>
              ))}
            </aside>
            <section className="admin-form admin-role-permission-form">
              {selectedAdminRole ? (
                <>
                  <div className="section-title">
                    <h3>{selectedAdminRole.code}</h3>
                    <span>{rolePermissionDraft.length} permission(s)</span>
                  </div>
                  <p className="muted-text">{selectedAdminRole.description || selectedAdminRole.name}</p>
                  <section className="admin-permission-guide is-wide">
                    <div className="section-title">
                      <h4>Role Permission Assignment</h4>
                      <span>{canUse(user, "roles:write") ? "Editable" : "Read only"}</span>
                    </div>
                    <div className="admin-permission-options role-permission-options">
                      {adminPermissionOptions(permissionGovernance).map((item) => {
                        const selected = rolePermissionDraft.includes(item.value);
                        const locked = selectedAdminRole.code === "SUPER_ADMIN" && item.value === "admin:*";
                        return (
                          <button
                            className={`${selected ? "is-selected" : ""} ${locked ? "is-disabled" : ""}`}
                            disabled={!canUse(user, "roles:write") || locked}
                            key={item.value}
                            type="button"
                            onClick={() => toggleRolePermission(item.value)}
                          >
                            <strong>{item.value}</strong>
                            <span>{item.label} · {item.description}</span>
                          </button>
                        );
                      })}
                    </div>
                    <p className="muted-text">Role 권한은 해당 Role 사용자 전체에 적용됩니다. 사용자별 예외 권한은 Users 탭의 Extra Permissions에서만 관리합니다.</p>
                  </section>
                  <div className="admin-permission-support-grid">
                    <section className="admin-detail-card">
                      <div className="section-title"><h3>Permission Catalog</h3><span>{permissionGovernance?.permissions?.length || 0}</span></div>
                      <table>
                        <tbody>
                          {(permissionGovernance?.permissions || []).map((permission) => (
                            <tr key={permission.code}>
                              <td>{permission.code}</td>
                              <td>{permission.name}</td>
                              <td>{permission.description || `${permission.domain}:${permission.action}`}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </section>
                    <section className="admin-detail-card">
                      <div className="section-title"><h3>Feature Resource Mapping</h3><span>{permissionGovernance?.resources?.length || 0}</span></div>
                      <table>
                        <tbody>
                          {(permissionGovernance?.resources || []).map((resource) => (
                            <tr key={resource.resourceKey}>
                              <td>{resource.resourceType}</td>
                              <td>{resource.resourceKey}</td>
                              <td>{resource.requiredPermissionCode}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </section>
                  </div>
                  <div className="modal-actions">
                    <button className="primary-button" type="button" disabled={loading || !canUse(user, "roles:write")} onClick={() => void saveRolePermissions()}>Save Role Permissions</button>
                  </div>
                </>
              ) : <p className="muted-text">Role 정보가 없습니다.</p>}
            </section>
          </div>
        ) : null}
        {activeTab === "workflows" && canManageWorkflows ? (
          <div className="admin-layout">
            <aside className="admin-list">
              <div className="section-title"><h3>워크플로우</h3><span>{workflows.length}</span></div>
              {canUse(user, "workflows:write") ? <button className="secondary-button" type="button" onClick={startNewWorkflowRegistration}>New Workflow</button> : null}
              {workflows.map((item) => (
                <button
                  className={`admin-row ${selectedAdminWorkflowId === item.id ? "is-selected" : ""} ${item.active ? "is-active" : ""}`}
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedAdminWorkflowId(item.id)}
                >
                  <strong>{item.label || item.name || item.id}</strong>
                  <span>{item.id} · {item.keyframeCount || 0} image(s)</span>
                  <small className={`admin-status-badge ${item.active ? "is-active" : "is-inactive"}`}>{item.active ? "ACTIVE" : "INACTIVE"}</small>
                </button>
              ))}
            </aside>
            <section className="admin-form">
              {selectedAdminWorkflow ? (
                <>
                  <div className="section-title">
                    <h3>워크플로우 상세</h3>
                    <span>{selectedAdminWorkflow.active ? "ACTIVE" : "INACTIVE"}</span>
                  </div>
                  <div className="admin-detail-card">
                    <table>
                      <tbody>
                        <tr><td>Workflow ID</td><td>{selectedAdminWorkflow.id}</td></tr>
                        <tr><td>Name</td><td>{selectedAdminWorkflow.label || selectedAdminWorkflow.name || "-"}</td></tr>
                        <tr><td>Mode</td><td>{selectedAdminWorkflow.mode || "-"}</td></tr>
                        <tr><td>Input Images</td><td>{selectedAdminWorkflow.keyframeCount || 0}</td></tr>
                        <tr><td>Subgraphs</td><td>{selectedAdminWorkflow.segmentCount || 0}</td></tr>
                        <tr><td>Workflow File</td><td>{selectedAdminWorkflow.fileExists ? "EXISTS" : "MISSING"}</td></tr>
                        <tr><td>Param Config</td><td>{selectedAdminWorkflow.paramConfigExists ? "EXISTS" : "MISSING"}</td></tr>
                        <tr><td>Param Config Source</td><td>{selectedAdminWorkflow.paramConfigGenerated ? "AUTO-GENERATED" : selectedAdminWorkflow.paramConfigExists ? "UPLOADED / EXISTING" : "-"}</td></tr>
                        <tr><td>Metadata</td><td>{selectedAdminWorkflow.metadataExists ? `READY · ${selectedAdminWorkflow.metadataNodeCount ?? "-"} nodes · ${selectedAdminWorkflow.metadataSubgraphCount ?? "-"} subgraphs` : "MISSING"}</td></tr>
                        <tr><td>Segment Defaults</td><td>{selectedAdminWorkflow.segmentCount ? `${selectedAdminWorkflow.segmentCount} segment(s)` : "-"}</td></tr>
                        <tr><td>Description</td><td>{selectedAdminWorkflow.description || "-"}</td></tr>
                        <tr><td>Registered At</td><td>{selectedAdminWorkflow.registeredAt || "-"}</td></tr>
                        <tr><td>Updated At</td><td>{selectedAdminWorkflow.updatedAt || "-"}</td></tr>
                      </tbody>
                    </table>
                  </div>
                  <div className="modal-actions">
                    {canUse(user, "workflows:activate") ? <button className="primary-button" type="button" disabled={loading || selectedAdminWorkflow.active} onClick={() => void setWorkflowActive(selectedAdminWorkflow.id, true)}>Activate</button> : null}
                    {canUse(user, "workflows:activate") ? <button className="secondary-button" type="button" disabled={loading || !selectedAdminWorkflow.active} onClick={() => void setWorkflowActive(selectedAdminWorkflow.id, false)}>Deactivate</button> : null}
                    {canUse(user, "workflows:write") ? <button className="secondary-button" type="button" onClick={startNewWorkflowRegistration}>New Workflow</button> : null}
                  </div>
                </>
              ) : (
                <>
                  <div className="section-title"><h3>워크플로우 등록</h3><span>Load & Save</span></div>
                  <div className="workflow-import-grid">
                    <label className="workflow-file-loader">
                      <span>Workflow JSON 불러오기</span>
                      <input type="file" accept="application/json,.json" onChange={(event) => void loadWorkflowFile(event, "workflowJson")} />
                      <strong>{workflowForm.workflowJson ? workflowForm.workflowId || "loaded workflow" : "파일 선택"}</strong>
                    </label>
                    <label className="workflow-file-loader">
                      <span>Param Config JSON 불러오기</span>
                      <input type="file" accept="application/json,.json" onChange={(event) => void loadWorkflowFile(event, "paramConfigJson")} />
                      <strong>{workflowForm.paramConfigJson ? "loaded/generated param config" : "비우면 자동 생성"}</strong>
                    </label>
                  </div>
                  <div className="catalog-form-grid compact">
                    <label>Workflow ID<input value={workflowForm.workflowId} placeholder="new-workflow.json" onChange={(event) => setWorkflowForm({ ...workflowForm, workflowId: event.target.value })} /></label>
                    <label>Description<input value={workflowForm.description} onChange={(event) => setWorkflowForm({ ...workflowForm, description: event.target.value })} /></label>
                  </div>
                  <div className="admin-detail-card">
                    <table>
                      <tbody>
                        <tr><td>Workflow JSON</td><td>{workflowForm.workflowJson ? "LOADED" : "NOT LOADED"}</td></tr>
                        <tr><td>Param Config JSON</td><td>{workflowForm.paramConfigJson ? "LOADED" : "AUTO-GENERATE ON SAVE"}</td></tr>
                        <tr><td>Segment Defaults</td><td>저장 시 자동 생성/갱신</td></tr>
                        <tr><td>Metadata</td><td>저장 시 자동 갱신</td></tr>
                      </tbody>
                    </table>
                  </div>
                  <details className="workflow-json-preview">
                    <summary>Loaded JSON Preview</summary>
                    <pre>{workflowForm.workflowJson || "Workflow JSON 파일을 불러오세요."}</pre>
                  </details>
                  <div className="modal-actions">
                    <button className="primary-button" type="button" disabled={loading || !canUse(user, "workflows:write") || !workflowForm.workflowId || !workflowForm.workflowJson} onClick={() => void saveWorkflow()}>Save Workflow</button>
                  </div>
                </>
              )}
            </section>
          </div>
        ) : null}
        {activeTab === "sandbox" && canManageSandboxPod ? (
          <div className="admin-sandbox-layout">
            <section className="admin-form sandbox-pod-panel">
              <div className="section-title">
                <h3>Sandbox Pod</h3>
                <span>{sandboxPod?.runtimeStatus || sandboxPod?.desiredStatus || "NOT CHECKED"}</span>
              </div>
              <p className="muted-text">일상적인 영상 생성용 Serverless와 분리된 전용 Pod입니다. 여기서는 Pod 상태와 노출된 HTTP 서비스만 관리합니다.</p>
              {!sandboxPod && sandboxPodLoading ? <p className="muted-text">Sandbox Pod 상태를 확인 중입니다.</p> : null}
              {sandboxPod ? (
                <>
                  <dl className="sandbox-pod-details">
                    <div><dt>Pod ID</dt><dd>{sandboxPod.podId || "-"}</dd></div>
                    <div><dt>Pod Name</dt><dd>{sandboxPod.podName || "-"}</dd></div>
                    <div><dt>Resolved By</dt><dd>{sandboxPod.resolvedBy || "Pod ID (legacy)"}</dd></div>
                    <div><dt>Status</dt><dd>{sandboxPod.desiredStatus || "UNKNOWN"}</dd></div>
                    <div><dt>Service Status</dt><dd>{sandboxPod.runtimeStatus || "NOT CHECKED"}</dd></div>
                    <div><dt>Last Started</dt><dd>{sandboxPod.lastStartedAt || "-"}</dd></div>
                    <div><dt>Last Status Change</dt><dd>{sandboxPod.lastStatusChange || "-"}</dd></div>
                  </dl>
                  <section className="sandbox-service-list">
                    <div className="section-title"><h4>HTTP Services</h4><span>{sandboxPod.httpServices.length}</span></div>
                    {sandboxPod.httpServices.length ? sandboxPod.httpServices.map((service) => (
                      <a className="sandbox-service-link" href={service.url} key={service.url} rel="noreferrer" target="_blank">
                        <strong>{service.label || `HTTP ${service.internalPort}`}</strong><span>{service.url}</span>
                      </a>
                    )) : <p className="muted-text">{sandboxPod.message || "노출된 HTTP 서비스가 없습니다."}</p>}
                  </section>
                </>
              ) : null}
              <div className="modal-actions">
                <button className="secondary-button" disabled={sandboxPodLoading} type="button" onClick={() => void loadSandboxPod()}>Refresh Status</button>
                {canUse(user, "sandbox:control") && ["EXITED", "TERMINATED"].includes(sandboxPod?.desiredStatus || "") ? <button className="primary-button" disabled={sandboxPodLoading || !sandboxPod || sandboxPod.configured === false} type="button" onClick={() => setSandboxPodPendingAction("start")}>Deploy Sandbox Pod</button> : null}
                {canUse(user, "sandbox:control") ? <button className="danger-button" disabled={sandboxPodLoading || !sandboxPod || sandboxPod.configured === false || sandboxPod.desiredStatus === "EXITED" || sandboxPod.desiredStatus === "TERMINATED"} type="button" onClick={() => setSandboxPodPendingAction("stop")}>Stop Pod</button> : null}
              </div>
            </section>
          </div>
        ) : null}
        {activeTab === "catalog" && canManageCatalog ? (
          <section className="admin-catalog-panel">
            <div className="admin-catalog-toolbar">
              <div>
                <h3>Prompt Catalog</h3>
                <p>Positive/Negative fixed scope 아래의 카테고리, 서브 카테고리, key word를 관리합니다.</p>
              </div>
            </div>
            <PromptCatalogAdminContent
              catalog={catalog}
              loading={catalogLoading}
              notice={catalogNotice}
              onSaveCategoryGroup={onSaveCategoryGroup}
              onDeactivateCategoryGroup={onDeactivateCategoryGroup}
              onSaveCategory={onSaveCategory}
              onDeactivateCategory={onDeactivateCategory}
              onSaveTerm={onSaveTerm}
              onDeactivateTerm={onDeactivateTerm}
            />
          </section>
        ) : null}
        {sandboxPodPendingAction ? (
          <SandboxPodConfirmModal
            action={sandboxPodPendingAction}
            status={sandboxPod?.desiredStatus || "UNKNOWN"}
            onCancel={() => setSandboxPodPendingAction(null)}
            onConfirm={() => {
              const action = sandboxPodPendingAction;
              setSandboxPodPendingAction(null);
              void controlSandboxPod(action);
            }}
          />
        ) : null}
      </section>
    </div>
  );
}

function PromptBuilderModal({
  catalog,
  loading,
  notice,
  selectedTermIds,
  activePanel,
  systemPrompt,
  systemPromptText,
  scene,
  generated,
  sceneDescription,
  workflowName,
  segmentName,
  baseNegativePrompt,
  onClose,
  onRefreshBuilder,
  onReloadSystemPrompt,
  onSaveSystemPrompt,
  onSystemPromptTextChange,
  onPanelChange,
  onToggleTerm,
  onSceneDescriptionChange,
  onClearSelection,
  onGenerate,
  onApply
}: {
  catalog: PromptCatalogResponse | null;
  loading: boolean;
  notice: string;
  selectedTermIds: number[];
  activePanel: "keywords" | "systemPrompt";
  systemPrompt: PromptSystemPromptResponse | null;
  systemPromptText: string;
  scene: PromptSceneResponse | null;
  generated: PromptGenerateResponse | null;
  sceneDescription: string;
  workflowName: string;
  segmentName: string;
  baseNegativePrompt: string;
  onClose: () => void;
  onRefreshBuilder: () => void;
  onReloadSystemPrompt: () => void;
  onSaveSystemPrompt: () => void;
  onSystemPromptTextChange: (value: string) => void;
  onPanelChange: (panel: "keywords" | "systemPrompt") => void;
  onToggleTerm: (termId: number) => void;
  onSceneDescriptionChange: (value: string) => void;
  onClearSelection: (termIds?: number[]) => void;
  onGenerate: () => void;
  onApply: (promptOverride?: {
    positivePrompt?: string;
    negativePrompt?: string;
    negativePromptAddition?: string;
    source?: string;
  }) => void;
}) {
  const categories = promptCatalogCategories(catalog);
  const renderScopes = promptCatalogRenderScopes(categories);
  const selectedTerms = allPromptCatalogTerms(categories).filter((term) => selectedTermIds.includes(term.id));
  const selectedKeywords = selectedPromptKeywordsByScope(categories, selectedTermIds);
  const hasTerms = categories.some((category) => category.terms?.length);
  const positiveKeywordDraft = promptKeywordText(selectedKeywords.positive);
  const negativeKeywordDraft = promptKeywordText(selectedKeywords.negative);
  const sceneDetailDraft = sceneDescription.trim();
  const hasPositiveInput = Boolean(positiveKeywordDraft || sceneDetailDraft);
  const canBuildScene = hasPositiveInput;
  const positivePrompt = generated?.positivePrompt || positiveKeywordDraft || sceneDetailDraft;
  const negativePromptAddition = generated?.negativePrompt || negativeKeywordDraft;
  const negativePrompt = combinePromptText(baseNegativePrompt, negativePromptAddition);
  // C-01: 용어 검증·관계 적용·prompt_rules 평가·필수값 누락 경고는
  // buildPromptScene()(POST /prompts/scene)의 응답(scene.warnings)에 담기고,
  // generatePrompt()(POST /prompts/generate)의 응답(generated.warnings)에는
  // LLM 생성 자체의 경고(예: missing_scene_detail)만 담긴다 - 화면 2b 설계가
  // 보여주는 "용어 규칙 위반"/"필수 값 누락" 예시는 scene.warnings 쪽이라 두
  // 소스를 합쳐야 실제로 존재하는 경고가 전부 드러난다.
  const warnings = [...(scene?.warnings || []), ...(generated?.warnings || [])];
  // 화면 `2b` 설계대로 "용어 규칙 위반"(error) 심각도가 있으면 적용을 막는다 -
  // BLOCK 배지만 그리고 실제로는 막지 않으면 라벨과 동작이 어긋난다.
  const warningGroups = groupPromptWarningsBySeverity(warnings);
  const hasBlockingWarning = warningGroups.some((group) => group.severity === "error");
  const sceneStructure = toPromptSceneStructure(scene?.scene);
  const applyLabel = generated ? "Apply Generated Prompt" : "Apply Keyword / Scene Draft";
  const [expandedCatalogKeys, setExpandedCatalogKeys] = useState<Set<string>>(new Set());
  const applyDescription = hasBlockingWarning
    ? "용어 규칙 위반(BLOCK)이 있어 적용할 수 없습니다 · 위 경고를 해결하세요."
    : generated
      ? "Generate Prompt 결과가 현재 segment에 적용됩니다."
      : "선택한 key word draft가 현재 segment에 바로 적용됩니다.";

  useEffect(() => {
    setExpandedCatalogKeys(promptAccordionDefaultKeys());
  }, [catalog]);

  function isCatalogExpanded(key: string) {
    return expandedCatalogKeys.has(key);
  }

  function toggleCatalogAccordion(key: string) {
    setExpandedCatalogKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  async function copyPromptText(text: string) {
    if (!text) return;
    try {
      await navigator.clipboard?.writeText(text);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
  }

  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="promptBuilderTitle" onMouseDown={(event) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    }}>
      <section className="prompt-builder-modal">
        <div className="modal-header">
          <div>
            <h2 id="promptBuilderTitle">Prompt Builder</h2>
            <p>{workflowName || "-"} · {segmentName || "선택된 서브그래프"}</p>
          </div>
          <div className="modal-actions">
            <button className="secondary-button" type="button" disabled={loading} onClick={onRefreshBuilder}>리프레시 빌더</button>
            <button className="icon-button" type="button" onClick={onClose}>x</button>
          </div>
        </div>
        {notice ? <p className="modal-notice">{notice}</p> : null}
        <div className="prompt-builder-layout">
          <div className="prompt-category-list">
            <div className="prompt-builder-side-nav">
              <button
                className={activePanel === "keywords" ? "is-active" : ""}
                type="button"
                onClick={() => onPanelChange("keywords")}
              >
                Key Words
              </button>
              <button
                className={activePanel === "systemPrompt" ? "is-active" : ""}
                type="button"
                onClick={() => {
                  onPanelChange("systemPrompt");
                  if (!systemPrompt) {
                    onReloadSystemPrompt();
                  }
                }}
              >
                System Prompt
              </button>
            </div>
            {loading && !catalog ? <p className="muted-text">Prompt catalog를 불러오는 중입니다.</p> : null}
            {activePanel === "keywords" && !loading && !hasTerms ? <p className="muted-text">등록된 key word가 없습니다. Admin Console에서 카테고리와 key word를 등록하세요.</p> : null}
            <div className="prompt-taxonomy-tree" aria-label="Prompt catalog tree">
              {activePanel === "keywords" ? renderScopes.map((scope) => (
                <section className={`prompt-tree-root prompt-scope-${scope.key}`} key={scope.key}>
                  <button
                    aria-expanded={isCatalogExpanded(promptScopeAccordionKey(scope.key))}
                    className="prompt-accordion-trigger prompt-tree-root-heading"
                    type="button"
                    onClick={() => toggleCatalogAccordion(promptScopeAccordionKey(scope.key))}
                  >
                    <h3>{scope.label} Prompt</h3>
                    <span className="prompt-accordion-meta"><b>{scope.termCount}</b> Fixed {isCatalogExpanded(promptScopeAccordionKey(scope.key)) ? "-" : "+"}</span>
                  </button>
                  {isCatalogExpanded(promptScopeAccordionKey(scope.key)) ? scope.groups.map((group) => (
                    <section className="prompt-tree-group" key={`${scope.key}-${group.key}`}>
                      <button
                        aria-expanded={isCatalogExpanded(promptGroupAccordionKey(scope.key, group.key))}
                        className="prompt-accordion-trigger prompt-tree-group-heading"
                        type="button"
                        onClick={() => toggleCatalogAccordion(promptGroupAccordionKey(scope.key, group.key))}
                      >
                        <h4>{group.label}</h4>
                        <span className="prompt-accordion-meta"><b>{group.categories.length}</b> {isCatalogExpanded(promptGroupAccordionKey(scope.key, group.key)) ? "-" : "+"}</span>
                      </button>
                      {isCatalogExpanded(promptGroupAccordionKey(scope.key, group.key)) ? group.categories.map((category) => {
                        const categoryKey = promptCategoryAccordionKey(scope.key, group.key, category.code);
                        return (
                          <div className="prompt-tree-category" key={category.code}>
                            <button
                              aria-expanded={isCatalogExpanded(categoryKey)}
                              className="prompt-accordion-trigger prompt-tree-category-heading"
                              type="button"
                              onClick={() => toggleCatalogAccordion(categoryKey)}
                            >
                              <strong>{category.nameKo || category.nameEn || category.code}</strong>
                              <span>{category.selectionMode === "single" ? "Single" : "Multi"} {isCatalogExpanded(categoryKey) ? "-" : "+"}</span>
                            </button>
                            {isCatalogExpanded(categoryKey) ? (
                              <div className="prompt-tree-terms">
                                {(category.terms || []).map((term) => (
                                  <PromptTermButton
                                    key={term.id}
                                    term={term}
                                    selected={selectedTermIds.includes(term.id)}
                                    onToggle={() => onToggleTerm(term.id)}
                                  />
                                ))}
                              </div>
                            ) : null}
                          </div>
                        );
                      }) : null}
                    </section>
                  )) : null}
                </section>
              )) : (
                <section className="prompt-tree-root prompt-system-prompt-summary">
                  <h3>Qwen System Prompt</h3>
                  <p>{systemPrompt?.name || "Qwen WAN I2V Positive Prompt Composer"}</p>
                  <span>{systemPrompt?.updatedAt ? `Updated: ${systemPrompt.updatedAt}` : "Default prompt"}</span>
                </section>
              )}
            </div>
          </div>
          {activePanel === "systemPrompt" ? (
            <SystemPromptEditor
              loading={loading}
              systemPrompt={systemPrompt}
              value={systemPromptText}
              onChange={onSystemPromptTextChange}
              onReload={onReloadSystemPrompt}
              onSave={onSaveSystemPrompt}
            />
          ) : (
          <aside className="prompt-builder-preview">
            <div className="section-title">
              <h3>Selected Key Words</h3>
              <span>{selectedTerms.length}</span>
            </div>
            <div className="selected-keyword-grid">
              <SelectedKeywordBox
                title="Positive"
                keywords={selectedKeywords.positive}
                loading={loading}
                onClear={() => onClearSelection(selectedKeywords.positive.map((keyword) => keyword.id))}
              />
              <SelectedKeywordBox
                title="Negative"
                keywords={selectedKeywords.negative}
                loading={loading}
                tone="negative"
                onClear={() => onClearSelection(selectedKeywords.negative.map((keyword) => keyword.id))}
              />
            </div>
            <div className="prompt-scene-settings-card">
              <div className="section-title">
                <h3>Scene Detail</h3>
                <span>Optional</span>
              </div>
              <p className="muted-text">선택한 key word만으로 부족한 장면 설명을 입력합니다. 이 값은 Generate Prompt 실행 시 자동 생성되는 Scene JSON에 반영됩니다.</p>
              <p className="scene-detail-order">권장 순서: 대상/관계 → 주요 동작 → 보조 동작·상호작용 → 카메라 → 표현·분위기</p>
              <textarea
                className="scene-detail-textarea"
                placeholder={"주체/관계: 여성 1명, 남성 1명\n주요 동작: 여성은 고개를 들고 손으로 바닥을 짚는다\n보조 동작/상호작용: 남성은 옆에서 바라본다\n카메라: 측면 미디엄 샷, 아이레벨, 고정 카메라\n표현/분위기: 긴장된 표정, 자연스러운 실내 조명"}
                value={sceneDescription}
                rows={4}
                onChange={(event) => onSceneDescriptionChange(event.target.value)}
              />
              <details className="scene-detail-example">
                <summary>입력 예시 보기</summary>
                <p>원본 이미지의 외형·의상·배경은 유지하고, 새로 움직일 대상·동작·카메라 변화 중심으로 입력하세요. 자연스러운 영문 프롬프트는 Generate Prompt로 생성합니다.</p>
              </details>
            </div>
            <button className="primary-button" type="button" disabled={loading || !canBuildScene} onClick={onGenerate}>
              {loading ? "GENERATING..." : "Generate Prompt"}
            </button>
            <div className={`prompt-draft-card ${generated ? "is-generated" : ""}`}>
              <div className="section-title">
                <h3>{generated ? "Generated Prompt" : "Prompt Draft"}</h3>
                <span>{generated ? `Provider: ${generated.provider}` : "Builder"}</span>
              </div>
              <PromptTextBox
                title="Positive Prompt"
                value={positivePrompt}
                onCopy={() => void copyPromptText(positivePrompt)}
              />
              <PromptTextBox
                title="Negative Prompt"
                value={negativePrompt}
                tone="negative"
                onCopy={() => void copyPromptText(negativePrompt)}
              />
              {warningGroups.length ? (
                <div className="prompt-warning-list">
                  <h3>Warnings</h3>
                  {warningGroups.map((group) => (
                    <div className={`prompt-warning-group severity-${group.severity}`} key={group.severity}>
                      {group.items.map((warning, index) => (
                        <div className="prompt-warning-item" key={`${warning.code || group.severity}-${index}`}>
                          <span className="prompt-warning-dot" aria-hidden="true" />
                          <span className="prompt-warning-message">{warning.message || warning.code}</span>
                          <span className="prompt-warning-badge">
                            {group.severity === "error" ? "BLOCK · 적용 비활성" : group.severity === "warning" ? "WARN · 진행 가능" : "INFO"}
                          </span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
            <PromptSceneStructurePreview structure={sceneStructure} />
            <div className="prompt-scene-json">
              <h3>Scene JSON</h3>
              <pre>{scene ? JSON.stringify(scene.scene, null, 2) : "{}"}</pre>
            </div>
            <p className="prompt-apply-hint">{applyDescription}</p>
            <button
              className="primary-button"
              type="button"
              disabled={(!hasPositiveInput && !generated) || hasBlockingWarning}
              onClick={() => onApply({
                positivePrompt,
                negativePrompt,
                negativePromptAddition,
                source: generated ? "Generated Prompt" : "Prompt Builder"
              })}
            >
              {applyLabel}
            </button>
          </aside>
          )}
        </div>
      </section>
    </div>
  );
}

function SystemPromptEditor({
  loading,
  systemPrompt,
  value,
  onChange,
  onReload,
  onSave
}: {
  loading: boolean;
  systemPrompt: PromptSystemPromptResponse | null;
  value: string;
  onChange: (value: string) => void;
  onReload: () => void;
  onSave: () => void;
}) {
  return (
    <aside className="prompt-builder-preview system-prompt-editor">
      <div className="section-title">
        <div>
          <h3>System Prompt</h3>
          <p className="muted-text">{systemPrompt?.name || "Qwen WAN I2V Positive Prompt Composer"}</p>
        </div>
        <span>{systemPrompt?.modelFamily || "qwen"}</span>
      </div>
      <div className="system-prompt-meta">
        <span>Code</span>
        <strong>{systemPrompt?.code || "qwen_wan_i2v_positive"}</strong>
        <span>Provider</span>
        <strong>{systemPrompt?.provider || "runpod_vllm"}</strong>
      </div>
      <p className="muted-text">
        이 값은 RunPod vLLM/Qwen prompt generation의 system prompt로 사용됩니다.
        Negative prompt는 앱의 기본값과 선택 key word로 별도 관리됩니다.
      </p>
      <textarea
        className="system-prompt-textarea"
        value={value}
        spellCheck={false}
        onChange={(event) => onChange(event.target.value)}
      />
      <div className="system-prompt-actions">
        <button className="secondary-button" type="button" disabled={loading} onClick={onReload}>
          Reload
        </button>
        <button className="primary-button" type="button" disabled={loading || !value.trim()} onClick={onSave}>
          Save System Prompt
        </button>
      </div>
    </aside>
  );
}

function PromptTextBox({
  title,
  value,
  tone,
  onCopy
}: {
  title: string;
  value: string;
  tone?: "negative";
  onCopy: () => void;
}) {
  return (
    <section className={`prompt-text-box ${tone === "negative" ? "is-negative" : ""}`}>
      <div className="prompt-text-box-heading">
        <h4>{title}</h4>
        <button className="copy-button" type="button" disabled={!value} onClick={onCopy}>Copy</button>
      </div>
      <div className="prompt-text-scroll">
        <p>{value || "-"}</p>
      </div>
    </section>
  );
}

function SelectedKeywordBox({
  title,
  keywords,
  loading,
  tone,
  onClear
}: {
  title: string;
  keywords: PromptTerm[];
  loading: boolean;
  tone?: "negative";
  onClear: () => void;
}) {
  const keywordText = keywords.map((keyword) => keyword.labelEn || keyword.code).join(", ");

  return (
    <section className={`selected-keyword-box ${tone === "negative" ? "is-negative" : ""}`}>
      <div className="selected-keyword-heading">
        <h4>{title}</h4>
        <span>{keywords.length}</span>
      </div>
      <div className="selected-keyword-scroll">
        {keywords.length ? (
          <p className="selected-keyword-text">{keywordText}</p>
        ) : (
          <p className="muted-text">선택된 key word가 없습니다.</p>
        )}
      </div>
      <button className="secondary-button" type="button" disabled={loading || !keywords.length} onClick={onClear}>
        Clear Selection
      </button>
    </section>
  );
}

type PromptCatalogAdminContentProps = {
  catalog: PromptCatalogResponse | null;
  loading: boolean;
  notice: string;
  onSaveCategoryGroup: (payload: Record<string, unknown>, groupId?: number) => void;
  onDeactivateCategoryGroup: (groupId: number) => void;
  onSaveCategory: (payload: Record<string, unknown>, categoryId?: number) => void;
  onDeactivateCategory: (categoryId: number) => void;
  onSaveTerm: (payload: Record<string, unknown>, termId?: number) => void;
  onDeactivateTerm: (termId: number) => void;
};

type PromptCatalogAdminModalProps = PromptCatalogAdminContentProps & {
  onClose: () => void;
};

function PromptCatalogAdminModal({
  onClose,
  ...contentProps
}: PromptCatalogAdminModalProps) {
  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="promptCatalogAdminTitle" onMouseDown={(event) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    }}>
      <section className="catalog-admin-modal">
        <div className="modal-header">
          <div>
            <h2 id="promptCatalogAdminTitle">Prompt Catalog Admin</h2>
            <p>Prompt Builder와 동일한 분류 구조에서 카테고리, 서브 카테고리, key word를 관리합니다.</p>
          </div>
          <div className="modal-actions">
            <button className="icon-button" type="button" onClick={onClose}>x</button>
          </div>
        </div>
        <PromptCatalogAdminContent {...contentProps} />
      </section>
    </div>
  );
}

function PromptCatalogAdminContent({
  catalog,
  loading,
  notice,
  onSaveCategoryGroup,
  onDeactivateCategoryGroup,
  onSaveCategory,
  onDeactivateCategory,
  onSaveTerm,
  onDeactivateTerm
}: PromptCatalogAdminContentProps) {
  const groups = catalog?.groups || [];
  const scopes = promptCatalogAdminScopes(groups);
  const [selectedScopeKey, setSelectedScopeKey] = useState<"positive" | "negative">("positive");
  const [activeCatalogAdminLevel, setActiveCatalogAdminLevel] = useState<"none" | "category" | "subcategory" | "keyword">("none");
  const [selectedGroupId, setSelectedGroupId] = useState<number | "new">("new");
  const selectedGroup = selectedGroupId === "new" ? null : groups.find((group) => group.id === selectedGroupId) || null;
  const [groupForm, setGroupForm] = useState<Record<string, string>>(categoryGroupFormFrom(selectedGroup, selectedScopeKey));
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | "new">("new");
  const selectedCategory = selectedCategoryId === "new"
    ? null
    : selectedGroup?.subcategories.find((category) => category.id === selectedCategoryId) || null;
  const [categoryForm, setCategoryForm] = useState<Record<string, string | boolean>>(categoryFormFrom(selectedCategory, selectedGroup?.code || "", undefined, selectedGroup?.id));
  const [selectedTermId, setSelectedTermId] = useState<number | "new">("new");
  const selectedTerm = selectedTermId === "new" ? null : selectedCategory?.terms.find((term) => term.id === selectedTermId) || null;
  const [termForm, setTermForm] = useState<Record<string, string>>(termFormFrom(selectedTerm, selectedCategory));
  const [expandedAdminTreeKeys, setExpandedAdminTreeKeys] = useState<Set<string>>(new Set());

  useEffect(() => {
    const nextScope = scopes.find((scope) => scope.key === selectedScopeKey) || scopes[0] || null;
    if (nextScope && nextScope.key !== selectedScopeKey) {
      setSelectedScopeKey(nextScope.key);
      return;
    }
    const nextGroup = selectedGroupId === "new" ? null : nextScope?.groups.find((group) => group.id === selectedGroupId) || null;
    if (selectedGroupId !== "new" && !nextGroup) {
      setSelectedGroupId("new");
      setSelectedCategoryId("new");
      setSelectedTermId("new");
      setActiveCatalogAdminLevel("none");
      return;
    }
    const nextCategory = selectedCategoryId === "new" ? null : nextGroup?.subcategories.find((category) => category.id === selectedCategoryId) || null;
    if (selectedCategoryId !== "new" && !nextCategory) {
      setSelectedCategoryId("new");
      setSelectedTermId("new");
      setActiveCatalogAdminLevel(nextGroup ? "category" : "none");
      return;
    }
    const nextTerm = selectedTermId === "new" ? null : nextCategory?.terms.find((term) => term.id === selectedTermId) || null;
    if (selectedTermId !== "new" && !nextTerm) {
      setSelectedTermId("new");
      setActiveCatalogAdminLevel(nextCategory ? "subcategory" : "none");
    }
  }, [catalog]);

  useEffect(() => {
    setGroupForm(categoryGroupFormFrom(selectedGroup, selectedScopeKey));
  }, [selectedGroupId, selectedScopeKey, catalog]);

  useEffect(() => {
    setCategoryForm(categoryFormFrom(selectedCategory, selectedGroup?.code || "", undefined, selectedGroup?.id));
  }, [selectedCategoryId, catalog, selectedGroup?.code, selectedGroup?.id]);

  useEffect(() => {
    setTermForm(termFormFrom(selectedTerm, selectedCategory));
  }, [selectedTermId, selectedCategoryId, catalog]);

  const groupCode = categoryGroupCodeFromForm(groupForm, selectedScopeKey, selectedGroup);
  const subcategoryCode = subcategoryCodeFromForm(categoryForm, selectedCategory);
  const categoryPayload = {
    ...categoryForm,
    code: subcategoryCode,
    required: Boolean(categoryForm.required),
    maxSelectCount: categoryForm.maxSelectCount ? Number(categoryForm.maxSelectCount) : null,
    groupId: selectedGroup?.id || categoryForm.groupId || null,
    groupCode: selectedGroup?.code || categoryForm.groupCode || "positive_work_style",
    sortOrder: categoryForm.sortOrder ? Number(categoryForm.sortOrder) : 100
  };
  const groupPayload = {
    ...groupForm,
    code: groupCode,
    scopeType: selectedScopeKey === "negative" ? "NEGATIVE" : "POSITIVE",
    sortOrder: groupForm.sortOrder ? Number(groupForm.sortOrder) : 100
  };
  const termCode = promptTermCodeFromForm(termForm, selectedTerm, selectedCategory);
  const termPayload = {
    ...termForm,
    code: termCode,
    canonicalKey: termForm.canonicalKey || termCode,
    // B-06 3단계: categoryId 페이로드 키는 이제 PromptSubcategory.id를 가리킨다
    // (upsert_prompt_keyword 참조) - 더 이상 legacyCategoryId를 우선하지 않는다.
    categoryId: Number(termForm.categoryId || selectedCategory?.id || 0),
    riskLevel: termForm.riskLevel || "NONE",
    sortOrder: termForm.sortOrder ? Number(termForm.sortOrder) : 100
  };
  const canSaveGroup = Boolean(String(groupForm.nameKo || "").trim() && String(groupForm.nameEn || "").trim());
  const canSaveCategory = Boolean(selectedGroup && String(categoryForm.nameKo || "").trim() && String(categoryForm.nameEn || "").trim());
  const canSaveTerm = Boolean(selectedCategory && String(termForm.labelKo || "").trim() && String(termForm.labelEn || "").trim());

  function isAdminTreeExpanded(key: string) {
    return expandedAdminTreeKeys.has(key);
  }

  function toggleAdminTreeAccordion(key: string) {
    setExpandedAdminTreeKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  return (
    <>
      {notice ? <p className="modal-notice">{notice}</p> : null}
      <div className="catalog-admin-layout">
          <aside className="catalog-admin-tree prompt-category-list">
            <div className="section-title">
              <h3>Catalog Tree</h3>
              <span>{groups.length}</span>
            </div>
            <div className="prompt-taxonomy-tree">
            {scopes.map((scope) => (
              <section className={`prompt-tree-root prompt-scope-${scope.key}`} key={scope.key}>
                <button
                  aria-expanded={isAdminTreeExpanded(promptAdminScopeAccordionKey(scope.key))}
                  className={`prompt-accordion-trigger prompt-tree-root-heading ${selectedScopeKey === scope.key ? "is-selected" : ""}`}
                  type="button"
                  onClick={() => {
                    setSelectedScopeKey(scope.key);
                    toggleAdminTreeAccordion(promptAdminScopeAccordionKey(scope.key));
                  }}
                >
                  <h3>{scope.label} Prompt</h3>
                  <span className="prompt-accordion-meta"><b>{scope.groups.length}</b> Fixed {isAdminTreeExpanded(promptAdminScopeAccordionKey(scope.key)) ? "-" : "+"}</span>
                </button>
                {isAdminTreeExpanded(promptAdminScopeAccordionKey(scope.key)) ? scope.groups.map((group) => (
                  <section className="prompt-tree-group" key={`${scope.key}-${group.id}`}>
                    <button
                      aria-expanded={isAdminTreeExpanded(promptAdminGroupAccordionKey(scope.key, group.id))}
                      className={`prompt-accordion-trigger prompt-tree-group-heading ${selectedScopeKey === scope.key && selectedGroupId === group.id ? "is-selected" : ""}`}
                      type="button"
                      onClick={() => {
                        setSelectedScopeKey(scope.key);
                        setSelectedGroupId(group.id);
                        setSelectedCategoryId("new");
                        setSelectedTermId("new");
                        setActiveCatalogAdminLevel("category");
                        toggleAdminTreeAccordion(promptAdminGroupAccordionKey(scope.key, group.id));
                      }}
                    >
                      <h4>{group.nameKo || group.code}</h4>
                      <span className="prompt-accordion-meta"><b>{group.subcategories.length}</b> {isAdminTreeExpanded(promptAdminGroupAccordionKey(scope.key, group.id)) ? "-" : "+"}</span>
                    </button>
                    {isAdminTreeExpanded(promptAdminGroupAccordionKey(scope.key, group.id)) ? (
                    <div className="catalog-admin-subcategory-list">
                      {group.subcategories.map((category) => (
                        <div className="prompt-tree-category catalog-admin-subcategory-node" key={category.id}>
                        <button
                          aria-expanded={isAdminTreeExpanded(promptAdminSubcategoryAccordionKey(category.id))}
                          className={`prompt-accordion-trigger prompt-tree-category-heading ${selectedCategoryId === category.id ? "is-selected" : ""}`}
                          type="button"
                          onClick={() => {
                            setSelectedScopeKey(scope.key);
                            setSelectedGroupId(group.id);
                            setSelectedCategoryId(category.id);
                            setSelectedTermId("new");
                            setActiveCatalogAdminLevel("subcategory");
                            toggleAdminTreeAccordion(promptAdminSubcategoryAccordionKey(category.id));
                          }}
                        >
                          <strong>{category.nameKo || category.code}</strong>
                          <span className="prompt-accordion-meta"><b>{(category.terms || []).length}</b> {isAdminTreeExpanded(promptAdminSubcategoryAccordionKey(category.id)) ? "-" : "+"}</span>
                        </button>
                        {isAdminTreeExpanded(promptAdminSubcategoryAccordionKey(category.id)) ? (
                          <div className="prompt-tree-terms">
                            {(category.terms || []).map((term) => (
                              <button
                                className={`prompt-term ${selectedTermId === term.id ? "is-selected" : ""}`}
                                type="button"
                                key={term.id}
                                onClick={() => {
                                  setSelectedScopeKey(scope.key);
                                  setSelectedGroupId(group.id);
                                  setSelectedCategoryId(category.id);
                                  setSelectedTermId(term.id);
                                  setActiveCatalogAdminLevel("keyword");
                                }}
                              >
                                <strong>{term.labelKo || term.code}</strong>
                                <span>{term.labelEn || term.code}</span>
                              </button>
                            ))}
                          </div>
                        ) : null}
                        </div>
                      ))}
                    </div>
                    ) : null}
                  </section>
                )) : null}
              </section>
            ))}
            </div>
          </aside>
          <section className="catalog-admin-form">
            {activeCatalogAdminLevel === "none" ? (
              <div className="catalog-admin-empty">
                <h3>관리할 항목을 선택하세요.</h3>
                <p>좌측 tree에서 카테고리, 서브 카테고리 또는 key word를 선택하면 해당 정보만 표시됩니다.</p>
                <button className="secondary-button" type="button" onClick={() => {
                  setSelectedGroupId("new");
                  setSelectedCategoryId("new");
                  setSelectedTermId("new");
                  setActiveCatalogAdminLevel("category");
                }}>New Category</button>
              </div>
            ) : null}

            {activeCatalogAdminLevel !== "none" ? (
              <div className="catalog-admin-level-card">
                <span>상위 카테고리 정보</span>
                <strong>{selectedGroup?.nameKo || "새 카테고리"}</strong>
                <p>{selectedGroup?.nameEn || "-"}</p>
                {selectedGroup?.description ? <p>{selectedGroup.description}</p> : null}
              </div>
            ) : null}

            {activeCatalogAdminLevel === "category" ? (
              <>
                <div className="section-title">
                  <h3>카테고리 관리</h3>
                  <button className="inline-action-button" type="button" onClick={() => {
                    setSelectedGroupId("new");
                    setSelectedCategoryId("new");
                    setSelectedTermId("new");
                    setActiveCatalogAdminLevel("category");
                  }}>New Category</button>
                </div>
                <div className="catalog-form-grid compact">
                  <label>Name KO<input value={String(groupForm.nameKo || "")} onChange={(event) => setGroupForm({ ...groupForm, nameKo: event.target.value })} /></label>
                  <label>Name EN<input value={String(groupForm.nameEn || "")} onChange={(event) => setGroupForm({ ...groupForm, nameEn: event.target.value })} /></label>
                </div>
                <label>Description<textarea rows={2} value={String(groupForm.description || "")} onChange={(event) => setGroupForm({ ...groupForm, description: event.target.value })} /></label>
                <div className="modal-actions">
                  <button className="primary-button" type="button" disabled={loading || !canSaveGroup} onClick={() => onSaveCategoryGroup(groupPayload, selectedGroup?.id)}>
                    Save Category
                  </button>
                  {selectedGroup ? <button className="secondary-button" type="button" onClick={() => {
                    setSelectedCategoryId("new");
                    setSelectedTermId("new");
                    setActiveCatalogAdminLevel("subcategory");
                  }}>New Sub Category</button> : null}
                  {selectedGroup ? <button className="secondary-button" type="button" disabled={loading} onClick={() => onDeactivateCategoryGroup(selectedGroup.id)}>Delete Category</button> : null}
                </div>
              </>
            ) : null}

            {activeCatalogAdminLevel === "subcategory" || activeCatalogAdminLevel === "keyword" ? (
              <>
                <div className="catalog-admin-level-card">
                  <span>선택 서브 카테고리 정보</span>
                  <strong>{selectedCategory?.nameKo || "새 서브 카테고리"}</strong>
                  <p>{selectedCategory?.nameEn || "-"}</p>
                  {selectedCategory?.description ? <p>{selectedCategory.description}</p> : null}
                </div>
                {activeCatalogAdminLevel === "subcategory" ? (
                  <>
                    <div className="section-title">
                      <h3>서브 카테고리 관리</h3>
                      <button className="inline-action-button" type="button" disabled={!selectedGroup} onClick={() => {
                        setSelectedCategoryId("new");
                        setSelectedTermId("new");
                        setActiveCatalogAdminLevel("subcategory");
                      }}>New Sub Category</button>
                    </div>
                    <div className="catalog-form-grid compact">
                      <label>Name KO<input value={String(categoryForm.nameKo || "")} onChange={(event) => setCategoryForm({ ...categoryForm, nameKo: event.target.value })} /></label>
                      <label>Name EN<input value={String(categoryForm.nameEn || "")} onChange={(event) => setCategoryForm({ ...categoryForm, nameEn: event.target.value })} /></label>
                    </div>
                    <label>Description<textarea rows={2} value={String(categoryForm.description || "")} onChange={(event) => setCategoryForm({ ...categoryForm, description: event.target.value })} /></label>
                    <div className="modal-actions">
                      <button className="primary-button" type="button" disabled={loading || !canSaveCategory} onClick={() => onSaveCategory(categoryPayload, selectedCategory?.id)}>
                        Save Sub Category
                      </button>
                      {selectedCategory ? <button className="secondary-button" type="button" onClick={() => {
                        setSelectedTermId("new");
                        setActiveCatalogAdminLevel("keyword");
                      }}>New Key Word</button> : null}
                      {selectedCategory ? <button className="secondary-button" type="button" disabled={loading} onClick={() => onDeactivateCategory(selectedCategory.id)}>Delete Sub Category</button> : null}
                    </div>
                  </>
                ) : null}
              </>
            ) : null}

            {activeCatalogAdminLevel === "keyword" ? (
              <>
                <div className="section-title">
                  <h3>키워드 관리</h3>
                  <button className="inline-action-button" type="button" disabled={!selectedCategory} onClick={() => {
                    setSelectedTermId("new");
                    setActiveCatalogAdminLevel("keyword");
                  }}>New Key Word</button>
                </div>
                {selectedCategory ? (
                  <div className="catalog-term-layout">
                    <div className="catalog-admin-list compact">
                      {selectedCategory.terms.map((term) => (
                        <button
                          className={`catalog-admin-row ${selectedTermId === term.id ? "is-selected" : ""}`}
                          type="button"
                          key={term.id}
                          onClick={() => {
                            setSelectedTermId(term.id);
                            setActiveCatalogAdminLevel("keyword");
                          }}
                        >
                          <strong>{term.labelKo || term.code}</strong>
                          <span>{term.code}</span>
                        </button>
                      ))}
                    </div>
                    <div className="catalog-term-form">
                      <div className="catalog-form-grid compact">
                        <label>Label KO<input value={termForm.labelKo || ""} onChange={(event) => setTermForm({ ...termForm, labelKo: event.target.value })} /></label>
                        <label>Label EN<input value={termForm.labelEn || ""} onChange={(event) => setTermForm({ ...termForm, labelEn: event.target.value })} /></label>
                      </div>
                      <label>Prompt Text<textarea rows={2} value={termForm.promptText || ""} onChange={(event) => setTermForm({ ...termForm, promptText: event.target.value })} /></label>
                      <label>Negative Text<textarea rows={2} value={termForm.negativeText || ""} onChange={(event) => setTermForm({ ...termForm, negativeText: event.target.value })} /></label>
                      <label>Description<textarea rows={2} value={termForm.description || ""} onChange={(event) => setTermForm({ ...termForm, description: event.target.value })} /></label>
                      <div className="modal-actions">
                        <button className="primary-button" type="button" disabled={loading || !canSaveTerm} onClick={() => onSaveTerm(termPayload, selectedTerm?.id)}>Save Key Word</button>
                        {selectedTerm ? <button className="secondary-button" type="button" disabled={loading} onClick={() => onDeactivateTerm(selectedTerm.id)}>Delete Key Word</button> : null}
                      </div>
                    </div>
                  </div>
                ) : <p className="muted-text">서브 카테고리를 선택하거나 먼저 저장한 후 key word를 추가하세요.</p>}
              </>
            ) : null}
          </section>
      </div>
    </>
  );
}

function categoryGroupFormFrom(group: PromptCategoryGroup | null, scopeKey: "positive" | "negative"): Record<string, string> {
  return {
    code: group?.code || (scopeKey === "negative" ? "negative_" : "positive_"),
    nameKo: group?.nameKo || "",
    nameEn: group?.nameEn || "",
    description: group?.description || "",
    sortOrder: group?.sortOrder ? String(group.sortOrder) : "100"
  };
}

function categoryGroupCodeFromForm(form: Record<string, string>, scopeKey: "positive" | "negative", group: PromptCategoryGroup | null) {
  if (group?.code) {
    return group.code;
  }
  const prefix = scopeKey === "negative" ? "negative" : "positive";
  return `${prefix}_${adminCodeSlug(form.nameEn || form.nameKo || "category")}`;
}

function categoryFormFrom(category: PromptCategory | null, groupKey = "", parentCategoryId?: number, groupId?: number): Record<string, string | boolean> {
  return {
    code: category?.code || "",
    groupId: category?.groupId ? String(category.groupId) : groupId ? String(groupId) : "",
    groupCode: category?.groupCode || groupKey || "positive_work_style",
    parentCategoryId: category?.parentCategoryId ? String(category.parentCategoryId) : parentCategoryId ? String(parentCategoryId) : "",
    nameKo: category?.nameKo || "",
    nameEn: category?.nameEn || "",
    scopeType: category?.scopeType || "SCENE",
    selectionMode: category?.selectionMode || "multi",
    maxSelectCount: category?.maxSelectCount ? String(category.maxSelectCount) : "",
    sortOrder: category?.sortOrder ? String(category.sortOrder) : "100",
    required: Boolean(category?.required),
    description: category?.description || ""
  };
}

function subcategoryCodeFromForm(form: Record<string, string | boolean>, category: PromptCategory | null) {
  if (category?.code) {
    return category.code;
  }
  return adminCodeSlug(String(form.nameEn || form.nameKo || "subcategory")).toUpperCase();
}

function adminCodeSlug(value: string) {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return slug || `item_${Date.now()}`;
}

function promptTermCodeFromForm(form: Record<string, string>, term: PromptTerm | null | undefined, category: PromptCategory | null) {
  if (term?.code) {
    return term.code;
  }
  const rawCode = String(form.code || "").trim();
  if (rawCode) {
    return rawCode;
  }
  const slug = adminCodeSlug(String(form.labelEn || form.labelKo || form.promptText || "keyword"));
  const prefix = category?.code ? `${category.code.toLowerCase()}_` : "keyword_";
  return `${prefix}${slug}`;
}

function termFormFrom(term: PromptTerm | null | undefined, category: PromptCategory | null): Record<string, string> {
  return {
    // B-06 3단계: categoryId는 PromptSubcategory.id를 가리킨다 - legacyCategoryId는
    // 더 이상 우선순위를 갖지 않는다.
    categoryId: category?.id ? String(category.id) : "",
    code: term?.code || "",
    canonicalKey: term?.canonicalKey || "",
    labelKo: term?.labelKo || "",
    labelEn: term?.labelEn || "",
    promptText: term?.promptText || "",
    negativeText: term?.negativeText || "",
    description: term?.description || "",
    riskLevel: term?.riskLevel || "NONE",
    sortOrder: term?.sortOrder ? String(term.sortOrder) : "100"
  };
}

type PromptSceneStructure = {
  workflowId: string;
  segmentIndex: string;
  language: string;
  genres: string[];
  contentRating: string[];
  scenes: Array<{
    sequenceNo: string;
    summary: string;
    description: string;
    camera: Record<string, string[]>;
    environment: Record<string, string[]>;
    style: Record<string, string[]>;
    motion: Record<string, string[]>;
    quality: string[];
    negativeTerms: string[];
  }>;
};

function PromptSceneStructurePreview({ structure }: { structure: PromptSceneStructure | null }) {
  if (!structure) {
    return (
      <div className="prompt-structure-card">
        <div className="section-title">
          <h3>Scene Structure</h3>
          <span>v1</span>
        </div>
        <p className="muted-text">Generate Prompt 실행 후 자동 생성된 scene detail과 key word 기반 구조가 표시됩니다.</p>
      </div>
    );
  }
  return (
    <div className="prompt-structure-card">
      <div className="section-title">
        <h3>Scene Structure</h3>
        <span>{structure.scenes.length} scene</span>
      </div>
      <dl className="prompt-structure-meta">
        <div><dt>Workflow</dt><dd>{structure.workflowId}</dd></div>
        <div><dt>Segment</dt><dd>{structure.segmentIndex}</dd></div>
        <div><dt>Language</dt><dd>{structure.language}</dd></div>
      </dl>
      <PromptTagRow label="Genre" values={structure.genres} />
      <PromptTagRow label="Rating" values={structure.contentRating} />
      {structure.scenes.map((sceneItem) => (
        <section className="prompt-scene-summary" key={sceneItem.sequenceNo}>
          <h4>Scene {sceneItem.sequenceNo}</h4>
          <p>{sceneItem.summary || "No summary"}</p>
          {sceneItem.description ? <p className="muted-text">{sceneItem.description}</p> : null}
          <PromptTagRow label="Camera" values={flattenNamedLists(sceneItem.camera)} />
          <PromptTagRow label="Environment" values={flattenNamedLists(sceneItem.environment)} />
          <PromptTagRow label="Style" values={flattenNamedLists(sceneItem.style)} />
          <PromptTagRow label="Motion" values={flattenNamedLists(sceneItem.motion)} />
          <PromptTagRow label="Quality" values={sceneItem.quality} />
          <PromptTagRow label="Negative" values={sceneItem.negativeTerms} tone="warning" />
        </section>
      ))}
    </div>
  );
}

function PromptTagRow({ label, values, tone }: { label: string; values: string[]; tone?: "warning" }) {
  const cleanValues = values.filter(Boolean);
  if (!cleanValues.length) {
    return null;
  }
  return (
    <div className="prompt-tag-row">
      <span>{label}</span>
      <div>
        {cleanValues.map((value) => (
          <small className={tone === "warning" ? "is-warning" : ""} key={`${label}-${value}`}>{value}</small>
        ))}
      </div>
    </div>
  );
}

function toPromptSceneStructure(value: Record<string, unknown> | undefined): PromptSceneStructure | null {
  if (!value || !Array.isArray(value.scenes)) {
    return null;
  }
  return {
    workflowId: stringValue(value.workflowId, "-"),
    segmentIndex: stringValue(value.segmentIndex, "-"),
    language: stringValue(value.language, "-"),
    genres: stringList(value.genres),
    contentRating: stringList(value.contentRating),
    scenes: value.scenes.map((sceneItem, index) => {
      const item = objectValue(sceneItem);
      return {
        sequenceNo: stringValue(item.sequenceNo, String(index + 1)),
        summary: stringValue(item.summary, ""),
        description: stringValue(item.description, ""),
        camera: namedStringLists(item.camera),
        environment: namedStringLists(item.environment),
        style: namedStringLists(item.style),
        motion: namedStringLists(item.motion),
        quality: stringList(item.quality),
        negativeTerms: stringList(item.negativeTerms)
      };
    })
  };
}

function objectValue(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function stringValue(value: unknown, fallback = ""): string {
  if (value === null || value === undefined) {
    return fallback;
  }
  const text = String(value).trim();
  return text || fallback;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => String(item || "").trim()).filter(Boolean);
}

function namedStringLists(value: unknown): Record<string, string[]> {
  const source = objectValue(value);
  return Object.fromEntries(Object.entries(source).map(([key, item]) => [key, stringList(item)]));
}

function flattenNamedLists(value: Record<string, string[]>): string[] {
  return Object.entries(value).flatMap(([key, items]) => items.map((item) => `${key}: ${item}`));
}

function PromptTermButton({ term, selected, onToggle }: { term: PromptTerm; selected: boolean; onToggle: () => void }) {
  return (
    <button className={`prompt-term ${selected ? "is-selected" : ""}`} type="button" onClick={onToggle}>
      <strong>{term.labelKo || term.labelEn || term.code}</strong>
      <span>{term.labelEn || term.code}</span>
    </button>
  );
}

function findPromptTermCategory(catalog: PromptCatalogResponse | null, termId: number) {
  return promptCatalogCategories(catalog).find((category) => (category.terms || []).some((term) => term.id === termId));
}

function HistoryModal({
  history,
  page,
  pageCount,
  pageSize,
  total,
  loading,
  selectedItem,
  selectedTaskId,
  activeTab,
  notice,
  promptReviewItems,
  promptReviewLoading,
  promptReviewNotice,
  onClose,
  onPageChange,
  onPageSizeChange,
  onSelect,
  onTabChange,
  onCopyPrompt,
  onDownload,
  onRework,
  onDelete,
  onSavePromptReview,
  onSavePromptFeedback,
  canRework,
  canDelete,
  canReview,
  canGiveFeedback
}: {
  history: HistoryItem[];
  page: number;
  pageCount: number;
  pageSize: 20 | 50;
  total: number;
  loading: boolean;
  selectedItem: HistoryItem | null;
  selectedTaskId: string;
  activeTab: "overview" | "images" | "config" | "video" | "review";
  notice: string;
  promptReviewItems: TaskPromptItem[];
  promptReviewLoading: boolean;
  promptReviewNotice: string;
  onClose: () => void;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: 20 | 50) => void;
  onSelect: (item: HistoryItem) => void;
  onTabChange: (tab: "overview" | "images" | "config" | "video" | "review") => void;
  onCopyPrompt: (prompts: PromptEntry[] | undefined) => void;
  onDownload: (item: HistoryItem) => void;
  onRework: (item: HistoryItem) => void;
  onDelete: (item: HistoryItem) => void;
  onSavePromptReview: (segmentIndex: number, payload: Record<string, unknown>) => void;
  onSavePromptFeedback: (outputId: string, payload: { rating?: number; notes?: string }) => void;
  canRework: boolean;
  canDelete: boolean;
  canReview: boolean;
  canGiveFeedback: boolean;
}) {
  const pageStart = total ? (page - 1) * pageSize + 1 : 0;
  const pageEnd = Math.min(total, page * pageSize);

  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="historyTitle" onMouseDown={(event) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    }}>
      <section className="history-modal">
        <div className="modal-header">
          <h2 id="historyTitle">Task History & Result List</h2>
          <button className="icon-button" type="button" onClick={onClose}>x</button>
        </div>
        {notice ? <p className="modal-notice">{notice}</p> : null}
        <div className="history-layout">
          <div className="history-list">
            <table className="history-table">
              <thead>
                <tr>
                  <th>No</th>
                  <th>Timestamp</th>
                  <th>Worker</th>
                  <th>Positive Prompt</th>
                  <th>Negative Prompt</th>
                  <th>Status</th>
                  <th>View</th>
                  <th>Download</th>
                  {canRework ? <th>Rework</th> : null}
                  {canDelete ? <th>Delete</th> : null}
                </tr>
              </thead>
              <tbody>
                {history.map((item, index) => {
                  const sequence = (page - 1) * pageSize + index + 1;
                  const selected = item.taskId === selectedTaskId;
                  return (
                    <tr className={selected ? "is-selected" : ""} key={item.taskId} onClick={() => onSelect(item)}>
                      <td>{sequence}</td>
                      <td>{formatTimestamp(item.timestamp)}</td>
                      <td>{item.workerName || item.user?.name || "-"}</td>
                      <td><PromptCell prompts={positivePromptEntries(item)} onCopy={() => onCopyPrompt(positivePromptEntries(item))} /></td>
                      <td><PromptCell prompts={negativePromptEntries(item)} onCopy={() => onCopyPrompt(negativePromptEntries(item))} /></td>
                      <td><span className={`status-tag ${isSuccessStatus(item.status) ? "completed" : "failed"}`}>{item.status || "-"}</span></td>
                      <td><button className="view-button" type="button" onClick={(event) => { event.stopPropagation(); onSelect(item); onTabChange("video"); }}>□</button></td>
                      <td><button className="secondary-button" type="button" onClick={(event) => { event.stopPropagation(); onDownload(item); }}>Download MP4</button></td>
                      {canRework ? <td><button className="rework-button" type="button" onClick={(event) => { event.stopPropagation(); onRework(item); }}>재작업</button></td> : null}
                      {canDelete ? <td><button className="danger-button" type="button" onClick={(event) => { event.stopPropagation(); onDelete(item); }}>삭제</button></td> : null}
                    </tr>
                  );
                })}
                {!history.length ? (
                  <tr>
                    <td colSpan={8 + (canRework ? 1 : 0) + (canDelete ? 1 : 0)}>{loading ? "작업 이력을 불러오는 중입니다." : "작업 이력이 없습니다."}</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
            <div className="history-pagination">
              <span>{pageStart}-{pageEnd} / {total}</span>
              <div className="history-pagination-controls">
                <div>
                  <button className="secondary-button" type="button" disabled={page <= 1 || loading} onClick={() => onPageChange(page - 1)}>Prev</button>
                  {Array.from({ length: pageCount }, (_, index) => index + 1).map((pageNumber) => (
                    <button
                      className={`secondary-button ${pageNumber === page ? "is-active" : ""}`}
                      key={pageNumber}
                      type="button"
                      disabled={loading}
                      onClick={() => onPageChange(pageNumber)}
                    >
                      {pageNumber}
                    </button>
                  ))}
                  <button className="secondary-button" type="button" disabled={page >= pageCount || loading} onClick={() => onPageChange(page + 1)}>Next</button>
                </div>
                <label className="history-page-size">
                  <span>페이지당</span>
                  <select
                    value={pageSize}
                    disabled={loading}
                    onChange={(event) => onPageSizeChange(Number(event.target.value) === 50 ? 50 : 20)}
                  >
                    <option value={20}>20건</option>
                    <option value={50}>50건</option>
                  </select>
                </label>
              </div>
            </div>
          </div>
          <HistoryDetail
            item={selectedItem}
            activeTab={activeTab}
            promptReviewItems={promptReviewItems}
            promptReviewLoading={promptReviewLoading}
            promptReviewNotice={promptReviewNotice}
            onTabChange={onTabChange}
            onDownload={onDownload}
            onRework={onRework}
            onSavePromptReview={onSavePromptReview}
            onSavePromptFeedback={onSavePromptFeedback}
            canRework={canRework}
            canReview={canReview}
            canGiveFeedback={canGiveFeedback}
          />
        </div>
      </section>
    </div>
  );
}

function PromptCell({ prompts, onCopy }: { prompts: PromptEntry[]; onCopy: () => void }) {
  if (!prompts.length) {
    return <span className="muted-text">-</span>;
  }
  return (
    <div className="prompt-cell" title={formatPromptList(prompts)}>
      <ol>
        {prompts.map((prompt, index) => (
          <li key={`${prompt.index || index}-${prompt.text}`}>{compactText(promptText(prompt), index === 0 ? 48 : 36)}</li>
        ))}
      </ol>
      <button className="copy-button" type="button" onClick={(event) => { event.stopPropagation(); onCopy(); }}>Copy</button>
    </div>
  );
}

function HistoryDetail({
  item,
  activeTab,
  promptReviewItems,
  promptReviewLoading,
  promptReviewNotice,
  onTabChange,
  onDownload,
  onRework,
  onSavePromptReview,
  onSavePromptFeedback,
  canRework,
  canReview,
  canGiveFeedback
}: {
  item: HistoryItem | null;
  activeTab: "overview" | "images" | "config" | "video" | "review";
  promptReviewItems: TaskPromptItem[];
  promptReviewLoading: boolean;
  promptReviewNotice: string;
  onTabChange: (tab: "overview" | "images" | "config" | "video" | "review") => void;
  onDownload: (item: HistoryItem) => void;
  onRework: (item: HistoryItem) => void;
  onSavePromptReview: (segmentIndex: number, payload: Record<string, unknown>) => void;
  onSavePromptFeedback: (outputId: string, payload: { rating?: number; notes?: string }) => void;
  canRework: boolean;
  canReview: boolean;
  canGiveFeedback: boolean;
}) {
  const output = item ? historyOutputAsset(item) : null;
  const inputImages = item ? historyInputImages(item) : [];
  const outputMediaUrl = useProtectedAssetUrl(output?.downloadUrl || output?.url || item?.outputUrl || "");
  if (!item) {
    return <aside className="history-detail"><p className="muted-text">작업 이력이 없습니다.</p></aside>;
  }
  const tabs: Array<["overview" | "images" | "config" | "video" | "review", string]> = [
    ["overview", "Task Overview"],
    ["images", "Input Images"],
    ["config", "Node Config"],
    ["video", "Output Video"]
  ];
  if (canReview) {
    tabs.push(["review", "Prompt Review"]);
  }

  return (
    <aside className="history-detail">
      <div className="detail-tabs">
        {tabs.map(([tab, label]) => (
          <button className={activeTab === tab ? "is-active" : ""} key={tab} type="button" onClick={() => onTabChange(tab)}>
            {label}
          </button>
        ))}
      </div>
      {activeTab === "review" && canReview ? (
        <PromptReviewPanel
          prompts={promptReviewItems}
          loading={promptReviewLoading}
          notice={promptReviewNotice}
          onSave={onSavePromptReview}
          onSaveFeedback={onSavePromptFeedback}
          canReview={canReview}
          canGiveFeedback={canGiveFeedback}
        />
      ) : activeTab === "images" ? (
        <div className="detail-card">
          <h3>Input Images</h3>
          <div className="detail-image-grid">
            {inputImages.map((image) => (
              <figure key={`${image.index}-${image.assetId}`}>
                {image.assetId ? <ProtectedImage src={`/api/files/${image.assetId}`} alt={image.fileName || `Input ${image.index}`} /> : null}
                <figcaption>{image.assetId || "-"}<br /><span>({image.fileName || "-"})</span></figcaption>
              </figure>
            ))}
            {!inputImages.length ? <p className="muted-text">저장된 입력 이미지가 없습니다.</p> : null}
          </div>
        </div>
      ) : activeTab === "config" ? (
        <div className="detail-card">
          <h3>Wan Node Config JSON</h3>
          <pre>{JSON.stringify(item.wanNodeConfig || item.configJson || item.config || {}, null, 2)}</pre>
        </div>
      ) : activeTab === "video" ? (
        <div className="detail-card">
          {output?.downloadUrl || output?.url || item.outputUrl ? (
            <video src={outputMediaUrl} controls playsInline />
          ) : (
            <div className="empty-video">생성된 MP4 파일이 없습니다.</div>
          )}
          <p>File: {output?.fileName || item.outputFile || "-"}<br />Applied Seed: {item.generationSeed || item.seed || item.configJson?.seed || "-"}<br />FPS: {item.fps || item.configJson?.fps || "-"}<br />Segments: {item.segmentCount || item.segments?.length || 1}</p>
          <button className="secondary-button" type="button" onClick={() => onDownload(item)}>Download MP4</button>
        </div>
      ) : (
        <div className="detail-card">
          <h3>Task Overview</h3>
          <table>
            <tbody>
              <tr><td>Workflow</td><td>{item.workflowId || item.workflowName || item.workflow || "-"}</td></tr>
              <tr><td>Worker</td><td>{item.workerName || item.user?.name || "-"}</td></tr>
              <tr><td>Status</td><td>{item.status || "-"}</td></tr>
              <tr><td>Input Images</td><td>{inputImages.length}</td></tr>
              <tr><td>Output</td><td>{output?.fileName || item.outputUrl || "-"}</td></tr>
            </tbody>
          </table>
          <h3>Positive Prompt</h3>
          <pre>{formatPromptList(positivePromptEntries(item)) || "-"}</pre>
          <h3>Negative Prompt</h3>
          <pre>{formatPromptList(negativePromptEntries(item)) || "-"}</pre>
        </div>
      )}
      <div className="detail-actions">
        {canRework ? <button className="rework-button" type="button" onClick={() => onRework(item)}>재작업</button> : null}
      </div>
    </aside>
  );
}

const PROMPT_REVIEW_FLAGS: Array<[keyof TaskPromptReviewFlags, string]> = [
  ["intentMatched", "프롬프트 의도 반영"],
  ["identityPreserved", "이미지 정체성 유지"],
  ["naturalMotion", "움직임 자연스러움"],
  ["noDistortion", "왜곡/깨짐 없음"],
  ["backgroundStable", "배경 안정성"]
];

function PromptReviewPanel({
  prompts,
  loading,
  notice,
  onSave,
  onSaveFeedback,
  canReview,
  canGiveFeedback
}: {
  prompts: TaskPromptItem[];
  loading: boolean;
  notice: string;
  onSave: (segmentIndex: number, payload: Record<string, unknown>) => void;
  onSaveFeedback: (outputId: string, payload: { rating?: number; notes?: string }) => void;
  canReview: boolean;
  canGiveFeedback: boolean;
}) {
  return (
    <div className="detail-card prompt-review-panel">
      <div className="section-title">
        <h3>Prompt Review</h3>
        <span>{prompts.length} segment(s)</span>
      </div>
      {notice ? <p className="modal-notice">{notice}</p> : null}
      {loading ? <p className="muted-text">작업 프롬프트 정보를 불러오는 중입니다.</p> : null}
      {!loading && !prompts.length ? <p className="muted-text">저장된 작업 프롬프트가 없습니다.</p> : null}
      {prompts.map((prompt) => (
        <div className="prompt-review-group" key={`${prompt.taskId}-${prompt.segmentIndex}`}>
          <PromptReviewCard prompt={prompt} loading={loading} onSave={onSave} canReview={canReview} />
          <PromptFeedbackCard prompt={prompt} loading={loading} onSave={onSaveFeedback} canGiveFeedback={canGiveFeedback} />
        </div>
      ))}
    </div>
  );
}

function PromptReviewCard({
  prompt,
  loading,
  onSave,
  canReview
}: {
  prompt: TaskPromptItem;
  loading: boolean;
  onSave: (segmentIndex: number, payload: Record<string, unknown>) => void;
  canReview: boolean;
}) {
  const [rating, setRating] = useState(String(prompt.qualityRating || ""));
  const [comment, setComment] = useState(prompt.qualityComment || "");
  const [reuseEligible, setReuseEligible] = useState(Boolean(prompt.reuseEligible));
  const [flags, setFlags] = useState<TaskPromptReviewFlags>(prompt.reviewFlags || {});

  useEffect(() => {
    setRating(String(prompt.qualityRating || ""));
    setComment(prompt.qualityComment || "");
    setReuseEligible(Boolean(prompt.reuseEligible));
    setFlags(prompt.reviewFlags || {});
  }, [prompt.id, prompt.qualityRating, prompt.qualityComment, prompt.reuseEligible, prompt.reviewStatus, prompt.reviewFlags]);

  function toggleFlag(key: keyof TaskPromptReviewFlags) {
    setFlags((current) => ({ ...current, [key]: !current[key] }));
  }

  const hasReuseReason = Object.values(flags).some(Boolean);
  const derivedReviewStatus = rating ? "reviewed" : "unreviewed";
  const saveDisabled = loading || !canReview || (reuseEligible && !hasReuseReason);

  return (
    <section className={`prompt-review-card ${reuseEligible ? "is-reusable" : ""}`}>
      <div className="section-title">
        <h4>Segment {prompt.segmentIndex}</h4>
        <span>{derivedReviewStatus}</span>
      </div>
      <div className="prompt-review-media">
        <AssetThumbs title="Input" assets={prompt.inputAssets || []} />
        <AssetThumbs title="Output" assets={prompt.outputAssets || []} />
      </div>
      <PromptTextBox title="Positive Prompt" value={prompt.positivePrompt} onCopy={() => copyText(prompt.positivePrompt)} />
      <PromptTextBox title="Negative Prompt" value={prompt.negativePrompt} tone="negative" onCopy={() => copyText(prompt.negativePrompt)} />
      <div className="prompt-review-form">
        <label>
          <span>품질 등급</span>
          <select value={rating} onChange={(event) => setRating(event.target.value)}>
            <option value="">미평가</option>
            <option value="5">5 - 매우 좋음</option>
            <option value="4">4 - 재사용 적합</option>
            <option value="3">3 - 보통</option>
            <option value="2">2 - 낮음</option>
            <option value="1">1 - 부적합</option>
          </select>
        </label>
        <label className="checkbox-row">
          <input type="checkbox" checked={reuseEligible} onChange={(event) => setReuseEligible(event.target.checked)} />
          <span>재사용 가능</span>
        </label>
      </div>
      <div className="prompt-review-flags">
        {PROMPT_REVIEW_FLAGS.map(([key, label]) => (
          <label key={key}>
            <input type="checkbox" checked={Boolean(flags[key])} onChange={() => toggleFlag(key)} />
            <span>{label}</span>
          </label>
        ))}
      </div>
      {reuseEligible && !hasReuseReason ? (
        <p className="modal-notice is-alert">재사용 가능으로 저장하려면 5개 사유 중 하나 이상을 체크해야 합니다.</p>
      ) : null}
      <label className="prompt-review-comment">
        <span>코멘트</span>
        <textarea value={comment} rows={3} onChange={(event) => setComment(event.target.value)} placeholder="품질 판단, 재사용 조건, 보완점을 입력" />
      </label>
      <button
        className="primary-button"
        type="button"
        disabled={saveDisabled}
        onClick={() => onSave(prompt.segmentIndex, {
          qualityRating: rating,
          qualityComment: comment,
          reuseEligible,
          reviewFlags: flags
        })}
      >
        Save Review
      </button>
    </section>
  );
}

// B-02: "프롬프트 생성 품질" 평가(prompt_feedback) 전용 카드. PromptReviewCard(위,
// task_prompts 기반 "영상 결과 평가")와 역할을 분리해 별도로 저장한다 - 같은 화면(3f)
// 안에서 두 평가가 섞이지 않도록 저장 버튼과 API 호출을 완전히 나눴다. 세그먼트 편집
// 화면(PromptBuilderModal)에는 이 카드를 넣지 않는다(설계에서 의도적으로 제거된 부분).
function PromptFeedbackCard({
  prompt,
  loading,
  onSave,
  canGiveFeedback
}: {
  prompt: TaskPromptItem;
  loading: boolean;
  onSave: (outputId: string, payload: { rating?: number; notes?: string }) => void;
  canGiveFeedback: boolean;
}) {
  const existing = prompt.promptFeedback || null;
  const [rating, setRating] = useState(String(existing?.rating || ""));
  const [notes, setNotes] = useState(existing?.notes || "");

  useEffect(() => {
    setRating(String(existing?.rating || ""));
    setNotes(existing?.notes || "");
  }, [prompt.id, existing?.id, existing?.rating, existing?.notes]);

  const outputId = prompt.promptGenerationOutputId;

  return (
    <section className="prompt-review-card prompt-feedback-card">
      <div className="section-title">
        <h4>프롬프트 생성 품질</h4>
        <span>{existing ? `평가됨 · ${existing.rating ?? "-"}` : "미평가"}</span>
      </div>
      {!outputId ? (
        <p className="muted-text">AI로 생성된 프롬프트가 아니라(직접 입력) 평가 대상이 없습니다.</p>
      ) : (
        <>
          <div className="prompt-review-form">
            <label>
              <span>생성 품질</span>
              <select value={rating} disabled={!canGiveFeedback} onChange={(event) => setRating(event.target.value)}>
                <option value="">미평가</option>
                <option value="5">5 - 매우 좋음</option>
                <option value="4">4 - 좋음</option>
                <option value="3">3 - 보통</option>
                <option value="2">2 - 낮음</option>
                <option value="1">1 - 부적합</option>
              </select>
            </label>
          </div>
          <label className="prompt-review-comment">
            <span>코멘트</span>
            <textarea
              value={notes}
              rows={2}
              disabled={!canGiveFeedback}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="생성된 프롬프트 자체의 품질(관계 적용, 문구 정확도 등)에 대한 메모"
            />
          </label>
          {!canGiveFeedback ? <p className="modal-notice">프롬프트 생성 품질 평가를 저장하려면 프롬프트 생성 권한이 필요합니다.</p> : null}
          <button
            className="primary-button"
            type="button"
            disabled={loading || !canGiveFeedback}
            onClick={() => onSave(outputId, { rating: rating ? Number(rating) : undefined, notes: notes.trim() || undefined })}
          >
            프롬프트 품질 평가 저장
          </button>
        </>
      )}
    </section>
  );
}

function AssetThumbs({ title, assets }: { title: string; assets: OutputAsset[] }) {
  return (
    <div className="prompt-review-assets">
      <strong>{title}</strong>
      {assets.length ? assets.slice(0, 4).map((asset) => (
        <figure key={asset.assetId || asset.fileName}>
          <ProtectedAssetPreview
            src={asset.downloadUrl || asset.url || `/api/files/${asset.assetId}`}
            isVideo={asset.kind === "videos" || asset.mimeType?.startsWith("video/")}
            alt={asset.fileName || asset.assetId || title}
          />
          <figcaption>{asset.fileName || asset.assetId}</figcaption>
        </figure>
      )) : <p className="muted-text">No asset</p>}
    </div>
  );
}

function PromptReuseModal({
  keyword,
  items,
  loading,
  notice,
  workflowName,
  onKeywordChange,
  onSearch,
  onClose,
  onApply
}: {
  keyword: string;
  items: TaskPromptItem[];
  loading: boolean;
  notice: string;
  workflowName: string;
  onKeywordChange: (value: string) => void;
  onSearch: () => void;
  onClose: () => void;
  onApply: (prompt: TaskPromptItem) => void;
}) {
  function reviewReasons(prompt: TaskPromptItem) {
    const flags = prompt.reviewFlags || {};
    return PROMPT_REVIEW_FLAGS.filter(([key]) => Boolean(flags[key])).map(([, label]) => label);
  }

  function assetLabel(asset: OutputAsset) {
    return [asset.assetId, asset.fileName].filter(Boolean).join(" / ") || "-";
  }

  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="promptReuseTitle" onMouseDown={(event) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    }}>
      <section className="prompt-reuse-modal">
        <div className="modal-header">
          <div>
            <h2 id="promptReuseTitle">Prompt Reuse</h2>
            <p>전체 작업 · 재사용 가능 프롬프트 검색</p>
          </div>
          <button className="icon-button" type="button" onClick={onClose}>x</button>
        </div>
        <div className="prompt-reuse-search">
          <input
            value={keyword}
            onChange={(event) => onKeywordChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                onSearch();
              }
            }}
            placeholder="프롬프트, 코멘트, 재사용 사유, asset, task 검색"
          />
          <button className="primary-button" type="button" disabled={loading} onClick={onSearch}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
        {notice ? <p className="modal-notice">{notice}</p> : null}
        <div className="prompt-reuse-list">
          {items.map((prompt) => {
            const reasons = reviewReasons(prompt);
            return (
              <article className="prompt-reuse-card" key={prompt.id}>
                <div className="section-title">
                  <h3>{prompt.workflowId} · Segment {prompt.segmentIndex}</h3>
                  <span>Rating {prompt.qualityRating || "-"}</span>
                </div>
                <dl className="prompt-reuse-info-grid">
                  <div><dt>Task ID</dt><dd>{prompt.taskId}</dd></div>
                  <div><dt>Model</dt><dd>{prompt.modelName || prompt.modelProfileId || "-"}</dd></div>
                  <div><dt>Status</dt><dd>{prompt.reviewStatus || "unreviewed"}</dd></div>
                  <div><dt>Reuse</dt><dd>{prompt.reuseEligible ? "Reusable" : "-"}</dd></div>
                  <div><dt>Created</dt><dd>{prompt.createdAt || "-"}</dd></div>
                  <div><dt>Updated</dt><dd>{prompt.updatedAt || "-"}</dd></div>
                </dl>
                <div className="prompt-reuse-reasons">
                  <strong>Reuse Reasons</strong>
                  <div>
                    {reasons.length ? reasons.map((reason) => <span key={reason}>{reason}</span>) : <span>-</span>}
                  </div>
                </div>
                <div className="prompt-reuse-asset-grid">
                  <section>
                    <strong>Input Assets</strong>
                    {(prompt.inputAssets || []).length ? (
                      <ul>{(prompt.inputAssets || []).map((asset) => <li key={asset.assetId || asset.fileName}>{assetLabel(asset)}</li>)}</ul>
                    ) : <p>-</p>}
                  </section>
                  <section>
                    <strong>Output Assets</strong>
                    {(prompt.outputAssets || []).length ? (
                      <ul>{(prompt.outputAssets || []).map((asset) => <li key={asset.assetId || asset.fileName}>{assetLabel(asset)}</li>)}</ul>
                    ) : <p>-</p>}
                  </section>
                </div>
                <PromptTextBox title="Positive Prompt" value={prompt.positivePrompt} onCopy={() => copyText(prompt.positivePrompt)} />
                <PromptTextBox title="Negative Prompt" value={prompt.negativePrompt} tone="negative" onCopy={() => copyText(prompt.negativePrompt)} />
                <div className="prompt-reuse-comment">
                  <strong>Comment</strong>
                  <p>{prompt.qualityComment || "-"}</p>
                </div>
                <button className="primary-button" type="button" onClick={() => onApply(prompt)}>Apply Prompt</button>
              </article>
            );
          })}
          {!items.length && !loading ? <p className="muted-text">검색 결과가 없습니다. Task History의 Prompt Review에서 재사용 가능으로 저장한 프롬프트가 검색됩니다.</p> : null}
        </div>
      </section>
    </div>
  );
}

function SandboxPodConfirmModal({
  action,
  status,
  onCancel,
  onConfirm
}: {
  action: "start" | "stop";
  status: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const deploy = action === "start";
  const title = action === "stop" ? "Sandbox Pod 중지" : "Sandbox Pod 배포";
  const message = action === "stop"
    ? "Sandbox Pod를 중지하시겠습니까? HTTP 서비스가 즉시 사용할 수 없게 됩니다."
    : deploy
      ? "중지된 Pod 대신 새 Sandbox Pod를 생성하시겠습니까? GPU 할당이 시작되며 비용이 발생할 수 있습니다."
      : "새 Sandbox Pod를 배포하시겠습니까? GPU 할당이 시작되며 비용이 발생할 수 있습니다.";
  const confirmLabel = action === "stop" ? "중지" : "배포";

  return (
    <div className="modal-layer confirm-layer" role="dialog" aria-modal="true" aria-labelledby="sandboxPodConfirmTitle">
      <section className="confirm-modal">
        <div className="modal-header">
          <h2 id="sandboxPodConfirmTitle">{title}</h2>
          <button className="icon-button" type="button" aria-label="닫기" onClick={onCancel}>x</button>
        </div>
        <p>{message}</p>
        <div className="confirm-actions">
          <button className="secondary-button" type="button" onClick={onCancel}>취소</button>
          <button className={action === "stop" ? "danger-button" : "primary-button"} type="button" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </section>
    </div>
  );
}

function ConfirmDeleteModal({
  item,
  onCancel,
  onConfirm
}: {
  item: HistoryItem;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="deleteHistoryTitle">
      <section className="confirm-modal">
        <div className="modal-header">
          <h2 id="deleteHistoryTitle">작업 내역 삭제</h2>
        </div>
        <p>삭제한 모든 자료(이미지, 영상 등)가 모두 삭제 됩니다. 삭제후 복구되지 않습니다. 삭제하시겠습니까?</p>
        <small>{item.taskId}</small>
        <div className="confirm-actions">
          <button className="secondary-button" type="button" onClick={onCancel}>취소</button>
          <button className="danger-button" type="button" onClick={onConfirm}>삭제</button>
        </div>
      </section>
    </div>
  );
}

// 임시 403 화면. design_handoff_dobedub_v3의 정식 화면 `7g`(차단·만료·오류)가
// E-05에서 구현되면 이 컴포넌트는 제거하고 그쪽으로 대체한다. 그 전까지 최소한
// "권한이 없다"는 사실을 사용자에게 알리기 위한 자리다 - 이전에는 이 상황에서
// 아무 안내 없이 빈 화면(history/status/metadata/manual)이거나 조용한 리다이렉트
// (admin)만 있었다.
function AccessDeniedModal({
  routeLabel,
  onClose
}: {
  routeLabel: string;
  onClose: () => void;
}) {
  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="accessDeniedTitle">
      <section className="confirm-modal">
        <div className="modal-header">
          <h2 id="accessDeniedTitle">권한이 없습니다</h2>
        </div>
        <p>"{routeLabel}" 화면을 사용할 권한이 없습니다. 필요한 경우 관리자에게 권한을 요청하십시오.</p>
        <div className="confirm-actions">
          <button className="secondary-button" type="button" onClick={onClose}>확인</button>
        </div>
      </section>
    </div>
  );
}

function StatusModal({
  status,
  connection,
  loading,
  notice,
  onClose,
  onRefresh,
  onTestRunpod
}: {
  status: SystemStatusResponse | null;
  connection: RunpodConnectionResponse | null;
  loading: boolean;
  notice: string;
  onClose: () => void;
  onRefresh: () => void;
  onTestRunpod: () => void;
}) {
  const segmentDefaults = status?.segmentDefaults || {};
  const metadata = status?.metadata || {};
  const workflows = status?.workflows || {};
  const storage = status?.storage || {};
  const defaultsOk = Boolean((segmentDefaults.workflowCount || 0) > 0 && segmentDefaults.matchedCount === segmentDefaults.workflowCount);
  const metadataOk = Boolean(metadata.manifest?.exists && metadata.workflowWidgetMap?.exists && metadata.models?.exists);
  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="statusTitle" onMouseDown={(event) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    }}>
      <section className="status-modal">
        <div className="modal-header">
          <h2 id="statusTitle">System Status</h2>
          <div className="modal-actions">
            <button className="secondary-button" type="button" disabled={loading} onClick={onTestRunpod}>Test ComfyUI</button>
            <button className="secondary-button" type="button" disabled={loading} onClick={onRefresh}>Refresh</button>
            <button className="icon-button" type="button" onClick={onClose}>x</button>
          </div>
        </div>
        {notice ? <p className="modal-notice">{notice}</p> : null}
        {connection ? <p className={`modal-notice ${connection.ok ? "is-ok" : "is-alert"}`}>{connection.message || "ComfyUI RunPod checked."}</p> : null}
        <div className="status-grid">
          <StatusCard title="Execution" value={status?.dryRun ? "Dry-run mode" : "RunPod live mode"} detail={status?.dryRun ? "Actual RunPod calls are disabled." : "Jobs will be submitted to RunPod."} ok={Boolean(status?.ok && !status?.dryRun)} />
          <StatusCard title="ComfyUI RunPod" value={status?.runpod?.configured ? "ONLINE" : "CHECK"} detail={`Endpoint: ${status?.runpod?.endpointId || "-"}\nBase: ${status?.runpod?.baseUrl || "-"}\nPurpose: video generation workflow execution`} ok={Boolean(status?.runpod?.configured)} />
          <StatusCard title="Qwen Prompt LLM" value={qwenStatusLabel(status?.promptLlm, "")} detail={`Provider: ${status?.promptLlm?.provider || "mock"}\nEndpoint: ${status?.promptLlm?.endpointId || status?.promptLlm?.endpointUrl || "-"}\nModel: ${status?.promptLlm?.model || "-"}\nMode: ${status?.promptLlm?.runpodInputMode || "-"}\nAPI key: ${status?.promptLlm?.apiKeyConfigured ? "Configured" : "Not configured"}`} ok={Boolean(status?.promptLlm?.configured && status?.promptLlm?.apiKeyConfigured && status?.promptLlm?.provider !== "mock")} />
          <StatusCard title="Workflows" value={`${workflows.count || 0} files`} detail={`${workflows.dir || "-"}\n${(workflows.items || []).slice(0, 6).join(", ") || "No workflow files found."}`} ok={Boolean(workflows.exists && (workflows.count || 0) > 0)} />
          <StatusCard title="Segment Defaults" value={`${segmentDefaults.matchedCount || 0}/${segmentDefaults.workflowCount || 0} matched`} detail={`${segmentDefaults.bundledPath?.path || "-"}\n${defaultsOk ? "All workflow defaults are available." : `Missing: ${(segmentDefaults.missingWorkflows || []).join(", ") || "-"}`}`} ok={defaultsOk} />
          <StatusCard title="Metadata" value={metadataOk ? "Ready" : "Check files"} detail={`Manifest: ${metadata.manifest?.exists ? "OK" : "Missing"}\nWidget map: ${metadata.workflowWidgetMap?.exists ? "OK" : "Missing"}\nModels: ${metadata.models?.exists ? "OK" : "Missing"}`} ok={metadataOk} />
          <StatusCard title="Storage" value={storage.outputsDir?.writable ? "Writable" : "Check path"} detail={`Data: ${storage.dataDir?.path || "-"}\nOutputs: ${storage.outputsDir?.path || "-"}`} ok={Boolean(storage.dataDir?.writable && storage.outputsDir?.writable)} />
        </div>
        <p className="status-timestamp">Last checked: {status?.checkedAt || "-"}</p>
      </section>
    </div>
  );
}

function StatusCard({ title, value, detail, ok }: { title: string; value: string; detail: string; ok: boolean }) {
  return (
    <section className={`status-card ${ok ? "is-ok" : "is-alert"}`}>
      <span />
      <h3>{title}</h3>
      <strong>{value}</strong>
      <p>{detail}</p>
    </section>
  );
}

function ManualModal({
  html,
  loading,
  error,
  onClose
}: {
  html: string;
  loading: boolean;
  error: string;
  onClose: () => void;
}) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const hitsRef = useRef<HTMLElement[]>([]);
  const hitIndexRef = useRef(-1);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchStatus, setSearchStatus] = useState("");

  function clearHighlights() {
    const document = iframeRef.current?.contentDocument;
    if (!document) return;
    document.querySelectorAll<HTMLElement>("mark.manual-hit").forEach((mark) => {
      const text = document.createTextNode(mark.textContent || "");
      mark.replaceWith(text);
      text.parentNode?.normalize();
    });
    hitsRef.current = [];
    hitIndexRef.current = -1;
  }

  function moveToHit(index: number) {
    const hits = hitsRef.current;
    if (!hits.length) {
      setSearchStatus("검색 결과가 없습니다.");
      return;
    }
    hits.forEach((hit) => hit.classList.remove("is-current"));
    hitIndexRef.current = (index + hits.length) % hits.length;
    const current = hits[hitIndexRef.current];
    current.classList.add("is-current");
    current.scrollIntoView({ behavior: "smooth", block: "center" });
    setSearchStatus(`${hitIndexRef.current + 1} / ${hits.length} 검색 결과`);
  }

  function searchManual() {
    const document = iframeRef.current?.contentDocument;
    clearHighlights();
    const query = searchQuery.trim();
    if (!document || !query) {
      setSearchStatus("검색어를 입력하세요.");
      return;
    }

    const needle = query.toLocaleLowerCase();
    const nodes: Text[] = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue?.trim() || node.parentElement?.closest("style, script, mark")) {
          return NodeFilter.FILTER_REJECT;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    while (walker.nextNode()) nodes.push(walker.currentNode as Text);

    nodes.forEach((node) => {
      const value = node.nodeValue || "";
      const lower = value.toLocaleLowerCase();
      let cursor = 0;
      let found = false;
      const fragment = document.createDocumentFragment();
      while (true) {
        const index = lower.indexOf(needle, cursor);
        if (index === -1) break;
        found = true;
        if (index > cursor) fragment.appendChild(document.createTextNode(value.slice(cursor, index)));
        const mark = document.createElement("mark");
        mark.className = "manual-hit";
        mark.textContent = value.slice(index, index + query.length);
        fragment.appendChild(mark);
        cursor = index + query.length;
      }
      if (!found) return;
      if (cursor < value.length) fragment.appendChild(document.createTextNode(value.slice(cursor)));
      node.replaceWith(fragment);
    });

    hitsRef.current = Array.from(document.querySelectorAll<HTMLElement>("mark.manual-hit"));
    if (!hitsRef.current.length) {
      setSearchStatus(`"${query}" 검색 결과가 없습니다.`);
      return;
    }
    moveToHit(0);
  }

  function handleManualLoad() {
    clearHighlights();
    setSearchStatus("");
    const document = iframeRef.current?.contentDocument;
    document?.addEventListener("click", (event) => {
      const target = event.target as HTMLElement | null;
      const link = target?.closest?.('a[href^="#"]');
      const anchorId = decodeURIComponent(link?.getAttribute("href")?.slice(1) || "");
      const section = anchorId ? document.getElementById(anchorId) : null;
      if (!section) return;
      event.preventDefault();
      section.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  useEffect(() => {
    hitsRef.current = [];
    hitIndexRef.current = -1;
    setSearchQuery("");
    setSearchStatus("");
  }, [html]);

  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="manualTitle" onMouseDown={(event) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    }}>
      <section className="manual-modal">
        <div className="modal-header">
          <h2 id="manualTitle">dobedub studio 사용자 매뉴얼</h2>
          <div className="modal-actions">
            <button className="icon-button" type="button" onClick={onClose}>x</button>
          </div>
        </div>
        <form className="manual-search-toolbar" onSubmit={(event) => {
          event.preventDefault();
          searchManual();
        }}>
          <label>
            매뉴얼 검색
            <input
              type="search"
              value={searchQuery}
              placeholder="검색어 입력 후 Enter"
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </label>
          <button className="primary-button" type="submit">검색</button>
          <button className="secondary-button" type="button" onClick={() => moveToHit(hitIndexRef.current + 1)}>다음</button>
          <p aria-live="polite">{searchStatus}</p>
        </form>
        <div className="manual-frame">
          {loading ? (
            <p>사용자 매뉴얼을 불러오는 중입니다.</p>
          ) : error ? (
            <div className="manual-error">
              <h3>사용자 매뉴얼을 불러오지 못했습니다.</h3>
              <p>{error}</p>
            </div>
          ) : (
            <iframe
              ref={iframeRef}
              title="dobedub studio 사용자 매뉴얼"
              sandbox="allow-same-origin"
              onLoad={handleManualLoad}
              srcDoc={html}
            />
          )}
        </div>
      </section>
    </div>
  );
}

function MetadataModal({
  workflows,
  workflowId,
  activeTab,
  status,
  metadata,
  models,
  loading,
  notice,
  onClose,
  onWorkflowChange,
  onTabChange,
  onRebuild
}: {
  workflows: WorkflowItem[];
  workflowId: string;
  activeTab: "summary" | "subgraphs" | "parameters" | "models" | "nodes";
  status: MetadataStatusResponse | null;
  metadata: WorkflowWidgetMetadata | null;
  models: ModelMetadataResponse | null;
  loading: boolean;
  notice: string;
  onClose: () => void;
  onWorkflowChange: (workflowId: string) => void;
  onTabChange: (tab: "summary" | "subgraphs" | "parameters" | "models" | "nodes") => void;
  onRebuild: () => void;
}) {
  const tabs: Array<["summary" | "subgraphs" | "parameters" | "models" | "nodes", string]> = [
    ["summary", "Summary"],
    ["subgraphs", "Subgraphs"],
    ["parameters", "Parameters"],
    ["models", "Models"],
    ["nodes", "Nodes"]
  ];
  return (
    <div className="modal-layer" role="dialog" aria-modal="true" aria-labelledby="metadataTitle" onMouseDown={(event: React.MouseEvent<HTMLDivElement>) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    }}>
      <section className="metadata-modal">
        <div className="modal-header">
          <h2 id="metadataTitle">Workflow Metadata</h2>
          <button className="icon-button" type="button" onClick={onClose}>x</button>
        </div>
        <div className="metadata-toolbar">
          <label>
            <span>Workflow</span>
            <select value={workflowId} onChange={(event: React.ChangeEvent<HTMLSelectElement>) => onWorkflowChange(event.target.value)}>
              {workflows.map((workflow) => (
                <option key={workflow.id} value={workflow.id}>{workflow.name || workflow.label || workflow.id}</option>
              ))}
            </select>
          </label>
          <button className="secondary-button" type="button" disabled={loading} onClick={onRebuild}>
            {loading ? "Rebuilding..." : "Rebuild Metadata"}
          </button>
        </div>
        <div className="detail-tabs">
          {tabs.map(([tab, label]) => (
            <button className={activeTab === tab ? "is-active" : ""} key={tab} type="button" onClick={() => onTabChange(tab)}>{label}</button>
          ))}
        </div>
        {notice ? <p className="modal-notice">{notice}</p> : null}
        <div className="metadata-body">
          {loading && !metadata ? <p className="muted-text">Metadata를 불러오는 중입니다.</p> : renderMetadataTab(activeTab, status, metadata, models)}
        </div>
      </section>
    </div>
  );
}

function ConfigRow({
  control,
  value,
  onChange
}: {
  control: ConfigControl;
  value: string | number | null;
  onChange: (value: string) => void;
}) {
  const stringValue = String(value ?? "");
  const isText = ["string", "text"].includes(control.type);
  const options = control.options || [];
  const min = control.min ?? 0;
  const max = control.max ?? Math.max(Number(value || 1) * 2, 1);
  return (
    <div className="config-row">
      <span>{control.label}</span>
      <strong>{formatConfigValue(value, control.type)}</strong>
      {options.length > 1 ? (
        <select value={stringValue} onChange={(event: React.ChangeEvent<HTMLSelectElement>) => onChange(event.target.value)}>
          {options.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      ) : isText ? (
        <input type="text" value={stringValue} onChange={(event: React.ChangeEvent<HTMLInputElement>) => onChange(event.target.value)} />
      ) : (
        <input
          type="range"
          min={min}
          max={max}
          step={control.type === "int" ? 1 : 0.1}
          value={stringValue}
          onChange={(event: React.ChangeEvent<HTMLInputElement>) => onChange(event.target.value)}
        />
      )}
      <small>{isText || options.length > 1 ? "ComfyUI" : `${min}-${max}`}</small>
      {control.description ? <em>{control.description}</em> : null}
    </div>
  );
}

function createSegmentsFromSchema(schema: WorkflowSchema): SegmentState[] {
  return (schema.segments || []).map((segment, index) => ({
    index: segment.index || index + 1,
    nodeId: segment.nodeId || "",
    subgraphName: segment.subgraphName || "Subgraph",
    displayName: segment.displayName || `${segment.subgraphName || "Subgraph"}_${segment.index || index + 1}`,
    startImageIndex: Number(segment.startImageIndex || index + 1),
    endImageIndex: Number(segment.endImageIndex || index + 2),
    progress: 0,
    positivePrompt: segment.defaultPositivePrompt || "",
    defaultNegativePrompt: segment.defaultNegativePrompt || "",
    negativePrompt: segment.defaultNegativePrompt || "",
    negativePromptAddition: "",
    config: segment.config || {},
    configControls: segment.configControls || []
  }));
}

function createSegmentsFromHistory(schema: WorkflowSchema, item: HistoryItem): SegmentState[] {
  const baseSegments = createSegmentsFromSchema(schema);
  const sourceSegments = item.segments || [];
  const wanSegments = item.wanNodeConfig?.segments || [];
  return baseSegments.map((segment, index) => {
    const source = sourceSegments[index] || sourceSegments.find((candidate) => Number(candidate.index) === segment.index) || {};
    const wanSource = wanSegments[index] || wanSegments.find((candidate) => Number(candidate.index) === segment.index) || {};
    const positive = promptForSegment(positivePromptEntries(item), segment.index) || source.positivePrompt || item.prompt || segment.positivePrompt;
    const negative =
      promptForSegment(negativePromptEntries(item), segment.index) ||
      source.negativePromptAddition ||
      source.negativePrompt ||
      item.negativePrompt ||
      segment.negativePrompt;
    const { seed: _baseSeed, Seed: _legacyBaseSeed, ...baseConfig } = segment.config;
    const { seed: _historySeed, Seed: _legacyHistorySeed, ...historyConfig } = item.configJson || {};
    const { seed: _sourceSeed, Seed: _legacySourceSeed, ...sourceConfig } = source.config || {};
    const wanConfig = configFromWanNodeSegment(wanSource);
    const { seed: _wanSeed, Seed: _legacyWanSeed, ...wanConfigWithoutSeed } = wanConfig;
    return {
      ...segment,
      positivePrompt: positive,
      defaultNegativePrompt: segment.defaultNegativePrompt,
      negativePrompt: negative,
      negativePromptAddition: source.negativePromptAddition || negative,
      config: {
        ...baseConfig,
        ...historyConfig,
        ...sourceConfig,
        ...wanConfigWithoutSeed
      }
    };
  });
}

function configFromWanNodeSegment(segment: HistorySegment & { params?: Array<{ uiKey?: string; value?: string | number }> }) {
  const config: Record<string, string | number> = { ...(segment?.config || {}) };
  (segment?.params || []).forEach((param) => {
    if (param.uiKey && param.value !== undefined && param.value !== null) {
      config[param.uiKey] = param.value;
    }
  });
  return config;
}

function createKeyframe(index: number): KeyframeState {
  return {
    index,
    file: null,
    upload: null,
    previewUrl: "",
    metaText: "Image: 1024x1024",
    uploading: false,
    error: ""
  };
}

function createKeyframes(count: number): KeyframeState[] {
  return Array.from({ length: Math.max(1, count || 1) }, (_, index) => createKeyframe(index + 1));
}

function createKeyframesFromHistory(schema: WorkflowSchema, item: HistoryItem): KeyframeState[] {
  const images = historyInputImages(item);
  return createKeyframes(schema.keyframeCount || images.length || 1).map((keyframe) => {
    const image = images.find((candidate) => Number(candidate.index) === keyframe.index) || images[keyframe.index - 1];
    if (!image?.assetId) {
      return keyframe;
    }
    const fileName = image.fileName || image.filename || `history-image-${keyframe.index}.png`;
    return {
      ...keyframe,
      file: null,
      upload: {
        assetId: image.assetId,
        fileName,
        mimeType: "image/*",
        sizeBytes: 0,
        downloadUrl: `/api/files/${image.assetId}`
      },
      previewUrl: `/api/files/${image.assetId}`,
      metaText: `${image.assetId} (${fileName})`,
      uploading: false,
      error: ""
    };
  });
}

function releaseKeyframePreviews(items: KeyframeState[]) {
  items.forEach((keyframe) => {
    if (keyframe.previewUrl.startsWith("blob:")) {
      URL.revokeObjectURL(keyframe.previewUrl);
    }
  });
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });
}

function formatConfigValue(value: string | number | null, type = "float") {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return String(value ?? "");
  }
  return type === "int" ? String(Math.round(number)) : String(Number(number.toFixed(2)));
}

function renderMetadataTab(
  activeTab: "summary" | "subgraphs" | "parameters" | "models" | "nodes",
  status: MetadataStatusResponse | null,
  metadata: WorkflowWidgetMetadata | null,
  modelMetadata: ModelMetadataResponse | null
) {
  if (!metadata && activeTab !== "models") {
    return <p className="muted-text">Metadata가 없습니다.</p>;
  }
  if (activeTab === "summary") {
    const manifest = status?.manifest || {};
    return (
      <div className="metadata-summary">
        <table>
          <tbody>
            <tr><td>Workflow ID</td><td>{metadata?.workflowId || "-"}</td></tr>
            <tr><td>Node Count</td><td>{metadata?.nodeCount ?? "-"}</td></tr>
            <tr><td>Subgraphs</td><td>{metadata?.segments?.length || 0}</td></tr>
            <tr><td>Generated At</td><td>{String(manifest.generatedAt || "-")}</td></tr>
            <tr><td>Object Info Snapshot</td><td>{manifest.hasObjectInfoSnapshot ? "YES" : "NO"}</td></tr>
            <tr><td>Fingerprint</td><td><code>{String(manifest.fingerprint || "-").slice(0, 32)}</code></td></tr>
          </tbody>
        </table>
      </div>
    );
  }
  if (activeTab === "subgraphs") {
    const segments = metadata?.segments || [];
    return segments.length ? (
      <>
        {segments.map((segment, index) => (
          <article className="metadata-card" key={`${recordText(segment, "nodeId")}-${index}`}>
            <h3>{recordText(segment, "displayName") || `Subgraph_${index + 1}`}</h3>
            <table>
              <tbody>
                <tr><td>Node ID</td><td>{recordText(segment, "nodeId") || "-"}</td></tr>
                <tr><td>Class Type</td><td>{recordText(segment, "classType") || "-"}</td></tr>
                <tr><td>Positive Node</td><td>{recordText(segment, "positiveNode") || "-"}</td></tr>
                <tr><td>Negative Node</td><td>{recordText(segment, "negativeNode") || "-"}</td></tr>
                <tr><td>Start Image</td><td>{recordText(segment, "startImageNode") || "-"}</td></tr>
                <tr><td>End Image</td><td>{recordText(segment, "endImageNode") || "-"}</td></tr>
              </tbody>
            </table>
          </article>
        ))}
      </>
    ) : <p className="muted-text">Subgraph metadata가 없습니다.</p>;
  }
  if (activeTab === "parameters") {
    const segments = metadata?.segments || [];
    return segments.length ? (
      <>
        {segments.map((segment, index) => {
          const params = Array.isArray(segment.params) ? segment.params as Record<string, unknown>[] : [];
          return (
            <article className="metadata-card" key={`${recordText(segment, "nodeId")}-${index}`}>
              <h3>{recordText(segment, "displayName") || `Subgraph_${index + 1}`}</h3>
              {params.length ? params.map((param, paramIndex) => (
                <section className="metadata-param" key={`${recordText(param, "param")}-${paramIndex}`}>
                  <strong>{recordText(param, "label") || recordText(param, "param") || "-"}</strong>
                  <small>{recordText(param, "param") || "-"} · default {recordText(param, "default") || "-"}</small>
                  <pre>{JSON.stringify(param.targets || [], null, 2)}</pre>
                </section>
              )) : <p className="muted-text">No parameters.</p>}
            </article>
          );
        })}
      </>
    ) : <p className="muted-text">Parameter metadata가 없습니다.</p>;
  }
  if (activeTab === "models") {
    const modelGroups = metadata?.models || modelMetadata?.models || {};
    const entries = Object.entries(modelGroups);
    return entries.length ? (
      <>
        {entries.map(([group, values]) => (
          <article className="metadata-card" key={group}>
            <h3>{group}</h3>
            <ul>{(values || []).map((value) => <li key={value}>{value}</li>)}</ul>
          </article>
        ))}
      </>
    ) : <p className="muted-text">Model metadata가 없습니다.</p>;
  }
  const nodes = metadata?.nodes || [];
  return nodes.length ? (
    <div className="metadata-node-list">
      {nodes.map((node, index) => (
        <details className="metadata-node" key={`${recordText(node, "nodeId")}-${index}`}>
          <summary><strong>{recordText(node, "nodeId") || "-"}</strong> {recordText(node, "title") || recordText(node, "classType")}</summary>
          <p>Class: <code>{recordText(node, "classType") || "-"}</code></p>
          <pre>{JSON.stringify({ inputs: node.inputs || [], links: node.links || [] }, null, 2)}</pre>
        </details>
      ))}
    </div>
  ) : <p className="muted-text">Node metadata가 없습니다.</p>;
}

function recordText(record: Record<string, unknown>, key: string) {
  const value = record[key];
  if (value === undefined || value === null) {
    return "";
  }
  return typeof value === "string" || typeof value === "number" || typeof value === "boolean"
    ? String(value)
    : JSON.stringify(value);
}

function workflowIdFromHistoryItem(item: HistoryItem, workflows: WorkflowItem[], fallbackWorkflowId: string) {
  const candidates = [item.workflowId, item.workflowName, item.workflow].filter(Boolean).map(String);
  const exact = candidates.find((candidate) => workflows.some((workflow) => workflow.id === candidate));
  if (exact) {
    return exact;
  }
  const keyText = candidates.join(" ");
  const keyMatch = keyText.match(/(\d+)\s*[-_]?key/i);
  if (keyMatch) {
    const workflowId = `${keyMatch[1]}-images.json`;
    if (workflows.some((workflow) => workflow.id === workflowId)) {
      return workflowId;
    }
  }
  const imageCount = historyInputImages(item).length || item.keyframes?.length;
  if (imageCount) {
    const workflowId = `${imageCount}-images.json`;
    if (workflows.some((workflow) => workflow.id === workflowId)) {
      return workflowId;
    }
  }
  return fallbackWorkflowId;
}

function historyInputImages(item: HistoryItem): InputImage[] {
  if (item.inputImages?.length) {
    return item.inputImages.map((image, index) => ({
      index: Number(image.index || index + 1),
      assetId: image.assetId || "",
      fileName: image.fileName || image.filename || "-"
    }));
  }
  const inputAssets = item.inputAssets || [];
  const keyframes = item.keyframes || [];
  const count = Math.max(inputAssets.length, keyframes.length);
  return Array.from({ length: count }, (_, index) => {
    const keyframe = keyframes[index] || {};
    return {
      index: Number(keyframe.index || index + 1),
      assetId: keyframe.uploadId || inputAssets[index] || "",
      fileName: keyframe.fileName || "-"
    };
  }).filter((image) => image.assetId || image.fileName !== "-");
}

function historyOutputAsset(item: HistoryItem): OutputAsset | null {
  const assets = item.outputAssets || [];
  return (
    assets.find((asset) => asset.outputRole === "final") ||
    assets.find((asset) => !asset.segmentIndex) ||
    assets[0] ||
    (item.outputUrl ? { downloadUrl: item.outputUrl, fileName: item.outputFile || "remote output", outputRole: "final" } : null)
  );
}

async function openOutputAsset(item: HistoryItem) {
  const output = historyOutputAsset(item);
  const rawUrl = output?.downloadUrl || output?.url || item.outputUrl || "";
  if (!rawUrl) {
    return;
  }
  await downloadProtectedAsset(fileUrlWithMode(rawUrl, "download"), output?.fileName || item.outputFile || "generated-output.mp4");
}

function useProtectedAssetUrl(rawUrl: string): string {
  const [mediaUrl, setMediaUrl] = useState("");

  useEffect(() => {
    let active = true;
    let objectUrl = "";
    if (!rawUrl) {
      setMediaUrl("");
      return undefined;
    }
    if (!rawUrl.startsWith("/api/files/")) {
      setMediaUrl(rawUrl);
      return undefined;
    }
    apiClient.assetBlob(rawUrl)
      .then((blob) => {
        if (!active) {
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        setMediaUrl(objectUrl);
      })
      .catch(() => {
        if (active) {
          setMediaUrl("");
        }
      });
    return () => {
      active = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [rawUrl]);

  return mediaUrl;
}

function ProtectedImage({ src, alt }: { src: string; alt: string }) {
  const mediaUrl = useProtectedAssetUrl(src);
  return mediaUrl ? <img src={mediaUrl} alt={alt} /> : null;
}

function ProtectedAssetPreview({ src, isVideo, alt }: { src: string; isVideo?: boolean; alt: string }) {
  const mediaUrl = useProtectedAssetUrl(src);
  if (!mediaUrl) {
    return null;
  }
  return isVideo
    ? <video src={mediaUrl} controls playsInline preload="metadata" />
    : <img src={mediaUrl} alt={alt} />;
}

async function downloadProtectedAsset(rawUrl: string, fileName: string): Promise<void> {
  if (!rawUrl) {
    throw new Error("다운로드할 영상이 없습니다.");
  }
  if (!rawUrl.startsWith("/api/files/")) {
    window.open(rawUrl, "_blank", "noopener");
    return;
  }
  const blob = await apiClient.assetBlob(rawUrl);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = fileName || "generated-output.mp4";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

function selectedOutputAsset(assets: OutputAsset[], selectedSegmentIndex: number): OutputAsset | null {
  return (
    assets.find((asset) => asset.outputRole === "segment" && Number(asset.segmentIndex) === selectedSegmentIndex) ||
    assets.find((asset) => asset.outputRole === "final") ||
    assets[0] ||
    null
  );
}

function finalOutputAsset(assets: OutputAsset[]): OutputAsset | null {
  return (
    assets.find((asset) => asset.outputRole === "final") ||
    assets.find((asset) => !asset.segmentIndex) ||
    assets[0] ||
    null
  );
}

function previewSegmentDetailRows(
  workflowId: string,
  segment: SegmentState,
  segmentCount: number,
  selectedOutput: OutputAsset | null,
  finalOutput: OutputAsset | null
): Array<[string, string]> {
  const config = segment.config || {};
  const segmentOutput =
    selectedOutput?.outputRole === "segment" || selectedOutput?.segmentIndex
      ? selectedOutput.fileName || selectedOutput.assetId || "Segment output"
      : finalOutput
        ? "Not saved separately"
        : "Waiting for generated video";
  return [
    ["Workflow", workflowToken(workflowId)],
    ["View Subgraph", `${segment.displayName || `Subgraph_${segment.index}`} / ${segmentCount || 1}`],
    ["Frames", config.durationSeconds ? `${formatConfigValue(config.durationSeconds, "int")}s` : formatConfigValue(config.frames, "int")],
    ["Steps / CFG", `${formatConfigValue(config.steps, "int")} / ${formatConfigValue(config.cfgScale, "float")}`],
    ["Motion", formatConfigValue(config.motionShift, "float")],
    ["Subgraph Output", segmentOutput],
    ["Final Output", finalOutput?.fileName || finalOutput?.assetId || "-"]
  ];
}

function workflowToken(workflowId: string) {
  const match = String(workflowId || "").match(/(\d+)\s*[-_]?images/i);
  return match ? `${match[1]}-images` : String(workflowId || "workflow").replace(/\.json$/, "");
}

function segmentTitleParts(displayName: string) {
  const value = String(displayName || "Subgraph").trim();
  const match = value.match(/^(.*?)\s*(\([^)]*\))?(_\d+)?$/);
  if (!match) {
    return [value];
  }
  const main = match[1]?.trim();
  const detail = `${match[2] || ""}${match[3] || ""}`.trim();
  return [main, detail].filter(Boolean);
}

function positivePromptEntries(item: HistoryItem): PromptEntry[] {
  return normalizePromptEntries(item.positivePrompts, item.segments, "positive", item.positivePrompt || item.prompt || "");
}

function negativePromptEntries(item: HistoryItem): PromptEntry[] {
  return normalizePromptEntries(item.negativePrompts, item.segments, "negative", item.negativePrompt || "");
}

function normalizePromptEntries(
  entries: PromptEntry[] | undefined,
  segments: HistorySegment[] | undefined,
  type: "positive" | "negative",
  fallback: string
): PromptEntry[] {
  if (entries?.length) {
    return entries
      .map((entry, index) => ({ index: Number(entry.index || index + 1), text: promptText(entry) }))
      .filter((entry) => entry.text);
  }
  const fromSegments = (segments || [])
    .map((segment, index) => ({
      index: Number(segment.index || index + 1),
      text: String(
        type === "positive"
          ? segment.positivePrompt || ""
          : segment.negativePromptAddition || segment.negativePrompt || ""
      ).trim()
    }))
    .filter((entry) => entry.text);
  if (fromSegments.length) {
    return fromSegments;
  }
  return splitPromptList(fallback);
}

function splitPromptList(value: string): PromptEntry[] {
  const text = String(value || "").trim();
  if (!text) {
    return [];
  }
  const parts = text.split("|").map((part) => part.trim()).filter(Boolean);
  return (parts.length ? parts : [text]).map((part, index) => ({
    index: index + 1,
    text: part.replace(/^\s*\d+\s*[:.)-]\s*/, "").trim()
  }));
}

function promptText(prompt: PromptEntry | string | undefined) {
  return String(typeof prompt === "string" ? prompt : prompt?.text || prompt?.prompt || "").trim();
}

function promptForSegment(prompts: PromptEntry[], segmentIndex: number) {
  return promptText(prompts.find((prompt) => Number(prompt.index) === segmentIndex) || prompts[segmentIndex - 1]);
}

function promptKeywordText(keywords: PromptTerm[]) {
  return keywords.map((keyword) => keyword.labelEn || keyword.code).filter(Boolean).join(", ");
}

function combinePromptText(...parts: Array<string | undefined | null>) {
  const seen = new Set<string>();
  const tokens = parts
    .flatMap((part) => String(part || "").split(","))
    .map((part) => part.trim())
    .filter(Boolean)
    .filter((part) => {
      const key = part.toLowerCase();
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  return tokens.join(", ");
}

// C-01: generate_prompt가 반환하는 {code, message, severity} 경고를 화면 2b
// 설계대로 심각도별로 묶는다. 백엔드는 severity로 "info"/"warning"/"error"만
// 사용하므로(prompt_builder_service.py), 알 수 없는 값은 "warning"으로 취급한다.
type PromptWarningSeverity = "error" | "warning" | "info";

function normalizePromptWarningSeverity(severity?: string): PromptWarningSeverity {
  if (severity === "error") return "error";
  if (severity === "info") return "info";
  return "warning";
}

function groupPromptWarningsBySeverity(
  warnings: Array<{ code?: string; message?: string; severity?: string }>,
) {
  const order: PromptWarningSeverity[] = ["error", "warning", "info"];
  return order
    .map((severity) => ({
      severity,
      items: warnings.filter((warning) => normalizePromptWarningSeverity(warning.severity) === severity),
    }))
    .filter((group) => group.items.length > 0);
}

function formatPromptList(prompts: PromptEntry[] | undefined) {
  return (prompts || [])
    .filter((prompt) => promptText(prompt))
    .map((prompt, index) => `${prompt.index || index + 1}. ${promptText(prompt)}`)
    .join("\n");
}

function compactText(value: string, maxLength: number) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}...` : text;
}

function formatTimestamp(value?: string) {
  return String(value || "-").replace(" ", "\n");
}

function isSuccessStatus(status?: string) {
  return ["completed", "success"].includes(String(status || "").toLowerCase());
}

function fileUrlWithMode(url: string, mode: "download" | "inline") {
  if (!url || !url.startsWith("/api/files/")) {
    return url;
  }
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}download=${mode === "download" ? "1" : "0"}`;
}

function formatElapsed(totalSeconds: number) {
  const seconds = Math.max(0, Math.round(totalSeconds || 0));
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `00:${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function loadSessionUser(): User | null {
  clearLoginSession(RESTORE_LOGIN_SESSION_ON_REFRESH);
  if (LOGIN_DISABLED_FOR_DEV) {
    sessionStorage.setItem(SESSION_USER_STORAGE_KEY, JSON.stringify({ user: DEV_USER, accessToken: "" }));
    return DEV_USER;
  }
  if (!RESTORE_LOGIN_SESSION_ON_REFRESH) {
    return null;
  }
  try {
    const raw = sessionStorage.getItem(SESSION_USER_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<AuthSession> & User;
    return parsed.user || parsed;
  } catch {
    return null;
  }
}

function clearLoginSession(keepCurrent = false) {
  if (typeof sessionStorage !== "undefined") {
    [...LEGACY_SESSION_USER_STORAGE_KEYS, ...(keepCurrent ? [] : [SESSION_USER_STORAGE_KEY])]
      .forEach((key) => sessionStorage.removeItem(key));
    for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
      const key = sessionStorage.key(index);
      if (key?.startsWith("dobedub.react.user") && !(keepCurrent && key === SESSION_USER_STORAGE_KEY)) {
        sessionStorage.removeItem(key);
      }
    }
  }
  if (typeof localStorage !== "undefined") {
    for (let index = localStorage.length - 1; index >= 0; index -= 1) {
      const key = localStorage.key(index);
      if (key?.startsWith("dobedub.react.user")) {
        localStorage.removeItem(key);
      }
    }
  }
}

createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
