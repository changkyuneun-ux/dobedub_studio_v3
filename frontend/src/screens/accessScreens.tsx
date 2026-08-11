import React, { useState } from "react";
import { apiClient, AuthSession, HealthResponse } from "../api/client";
import { serviceStatusLabel, qwenStatusLabel } from "../helpers/format";
import { StudioRoute, routePath } from "../router";
import { User } from "../auth";
import { AppShell } from "../components/AppShell";
import { shellNavigate } from "../helpers/navigation";

// E-05 · 1 Access.dc.html의 접속·안내 흐름 화면들.
// design_handoff_dobedub_v3/1 Access.dc.html: 6a 로그인 / 7g 차단·만료·오류 / 6b 매뉴얼.
// 구버전 `.login-screen`(dark 테마) LoginView를 대체한다 - 재사용한 것은 로그인
// 로직(apiClient.login, 에러 문구 매핑)뿐이고 화면 구조·스타일은 v3 토큰으로 재작성.

// 6a · 로그인 — design_handoff 6a "로그인 · 사내 계정 · 시스템 상태 노출".
// 좌측(흰 배경) 브랜드·소개, 우측 폼 + 시스템 상태 카드의 2열 구성.
// 설계 원본과 다르게 뺀 것(더미 데이터 금지 원칙):
// - 좌측의 WORKFLOWS/이번 주 RUN/재사용 프롬프트 통계 3칸 — 로그인 전에는 인증이
//   없어 이 수치를 줄 API를 호출할 수 없다. 소개 문구만 남기고 통계 타일은 제외.
// - 시스템 상태의 "Sandbox Pod" 행 — 조회에 sandbox:read 권한이 필요해 로그인 전에는
//   알 수 없다. 공개 헬스체크(/api/health)로 알 수 있는 ComfyUI·Qwen 두 줄만 표시.
export function LoginScreen({
  onLogin,
  health,
  healthError
}: {
  onLogin: (session: AuthSession) => void;
  health: HealthResponse | null;
  healthError: string;
}) {
  const [id, setId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const system = health?.system || health?.legacy;
  const comfyStatus = serviceStatusLabel(
    Boolean(system?.runpod?.configured),
    healthError,
    system?.dryRun ? "DRY-RUN" : undefined
  );
  const qwenStatus = qwenStatusLabel(system?.promptLlm, healthError);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = await apiClient.login({ id, password });
      onLogin(response);
    } catch (err) {
      setError(loginErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="v3-login">
      <section className="v3-login-brand">
        <div className="v3-login-brand-top">
          <span className="v3-login-logo" aria-hidden="true" />
          <span className="v3-login-brand-name">DOBEDUB STUDIO</span>
          <span className="v3-login-brand-badge">v3</span>
        </div>
        <div className="v3-login-hero">
          <h1 className="v3-login-hero-title">이미지 사이를 잇는<br />영상 생성 워크스페이스</h1>
          <p className="v3-login-hero-desc">
            키프레임을 올리고 세그먼트별로 프롬프트와 노드 구성값을 설정하면, 하나의 작업으로
            제출돼 구간 영상과 최종 병합본이 생성됩니다.
          </p>
        </div>
        <div className="v3-login-brand-foot">
          <span>사내 전용 · 외부 공유 금지</span>
          <span>문의 · Studio Platform</span>
        </div>
      </section>

      <section className="v3-login-panel">
        <form className="v3-login-form" onSubmit={submit}>
          <div>
            <div className="v3-label">SIGN IN</div>
            <div className="v3-login-title">DOBEDUB STUDIO | 접속</div>
          </div>

          <label className="v3-login-field">
            <span className="v3-label">ID</span>
            <input
              value={id}
              onChange={(event) => setId(event.target.value)}
              placeholder="사번 또는 계정 ID"
              autoComplete="username"
              required
            />
          </label>
          <label className="v3-login-field">
            <span className="v3-label">Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="비밀번호"
              autoComplete="current-password"
              required
            />
          </label>

          <button className="v3-primary-button v3-login-submit" type="submit" disabled={submitting}>
            {submitting ? "접속 중..." : "접속하기"}
          </button>

          {error ? (
            <div className="v3-login-error" role="alert">
              <span className="v3-login-error-dot" aria-hidden="true" />
              <span>{error}</span>
            </div>
          ) : null}

          <div className="v3-login-status">
            <div className="v3-label">시스템 상태</div>
            <div className="v3-login-status-row">
              <span>ComfyUI Serverless</span>
              <strong className={`v3-login-status-value is-${comfyStatus.toLowerCase()}`}>{comfyStatus}</strong>
            </div>
            <div className="v3-login-status-row">
              <span>Qwen LLM</span>
              <strong className={`v3-login-status-value is-${qwenStatus.toLowerCase()}`}>{qwenStatus}</strong>
            </div>
          </div>

          <p className="v3-login-note">
            비활성 계정 · 미입력 오류도 같은 자리에 표시됩니다 · 세션은 탭을 닫으면 종료됩니다
          </p>
        </form>
      </section>
    </main>
  );
}

// 7g · 차단(403 권한 없음) — design_handoff 7g "차단 · 만료 · 오류 3종".
// 설계 원본은 403·401·서버오류를 한 카드 3분할로 그리지만 README는 "실제로는 별개
// 상태"라고 명시한다. 여기서는 그중 403(직접 URL 진입 시 권한 없음)만 정식 화면으로
// 구현한다 - 401 세션 만료는 토큰 만료 시 로그인 화면(6a)으로 되돌아가는 기존 동작이,
// 서버 오류는 각 화면의 인라인 notice가 담당한다.
//
// 구버전 임시 AccessDeniedModal(modal-layer 오버레이)을 대체한다. 인증된 사용자가
// 권한 없는 라우트에 직접 진입한 상황이므로 사이드바가 있는 AppShell 본문에 그린다
// (권한 없는 메뉴는 사이드바에서 이미 숨겨져 있어, 이 화면은 직접 URL 진입으로만 도달).
export function AccessDeniedScreen({
  user,
  route,
  routeLabel,
  requiredPermission,
  onGoTo
}: {
  user: User;
  route: StudioRoute;
  routeLabel: string;
  requiredPermission: string;
  onGoTo: (route: StudioRoute) => void;
}) {
  const area = route.startsWith("admin.") ? "admin" : "generate";
  const role = user.role || "권한 미지정";
  return (
    <AppShell
      user={user}
      area={area}
      activeItem=""
      onNavigate={(key) => shellNavigate(key, onGoTo)}
      headerEyebrow="403 · 권한 없음"
      headerTitle="접근 권한이 없습니다"
    >
      <div className="v3-access-denied">
        <div className="v3-access-denied-badge">403</div>
        <h2 className="v3-access-denied-title">이 화면에 접근할 권한이 없습니다</h2>
        <p className="v3-access-denied-desc">
          {routeLabel}은(는) <code>{requiredPermission}</code> 권한이 필요합니다. 현재 역할{" "}
          <code>{role}</code>에는 포함되어 있지 않습니다.
        </p>
        <div className="v3-access-denied-card">
          <div className="v3-access-denied-row">
            <span>필요 권한</span>
            <code>{requiredPermission}</code>
          </div>
          <div className="v3-access-denied-row">
            <span>내 역할</span>
            <code>{role}</code>
          </div>
          <div className="v3-access-denied-row">
            <span>요청 경로</span>
            <code>{routePath(route)}</code>
          </div>
        </div>
        <div className="v3-access-denied-actions">
          <button className="v3-primary-button" type="button" onClick={() => onGoTo("create.load")}>
            Workspace로 이동
          </button>
        </div>
        <p className="v3-access-denied-note">
          권한이 없는 메뉴는 사이드바에서 숨겨집니다 · 직접 URL 진입만 이 화면에 도달합니다.
          접근이 필요하면 관리자에게 권한을 요청하십시오.
        </p>
      </div>
    </AppShell>
  );
}

export function loginErrorMessage(error: unknown) {
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
