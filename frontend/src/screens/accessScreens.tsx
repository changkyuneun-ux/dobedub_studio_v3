import React, { useState } from "react";
import { apiClient, AuthSession, HealthResponse } from "../api/client";
import { serviceStatusLabel, qwenStatusLabel } from "../helpers/format";

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
