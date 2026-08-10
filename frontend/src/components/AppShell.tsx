import React from "react";
import { User, canUse } from "../auth";

// E-01: 공통 레이아웃 컴포넌트. design_handoff_dobedub_v3의 모든 화면(2a~7c)이
// 공유하는 골격 — 사이드바 212px + 헤더 + 본문 그리드 + 우측 패널(선택) — 을 화면마다
// 새로 짜지 않고 이 컴포넌트 하나가 그린다. README "공통 골격은... 레이아웃
// 컴포넌트로 한 번 만들어 전 화면이 공유하게 하십시오" 지시를 따른다.
//
// 화면 자체(2a~2f, 3a~3f, 4a~7c)는 아직 이 컴포넌트를 사용하지 않는다(E-02~E-05에서
// 순서대로 이관). 지금은 신규 화면을 지을 때 쓸 재사용 가능한 뼈대만 갖춘 상태다.
//
// 사이드바 상단 고정 메뉴는 두 가지 영역(area)으로 나뉜다 - design_handoff의
// "2 Create.dc.html" "3 Review.dc.html"은 GENERATE 영역(Workspace / Prompt Library /
// Task History / Assets)을, "4 Admin.dc.html"은 ADMIN 영역(역할 & 권한 / 사용자 /
// 프롬프트 카탈로그 / 워크플로 정의 / Sandbox Pod / 감사 로그)을 공통으로 반복한다.
// 각 화면이 다르게 그리는 부분(스텝 트래커, 필터, 카탈로그 트리 등)은 sidebarExtra로,
// 화면 하단 고정 정보(서비스 상태, 보관 기한 안내 등)는 sidebarFooter로 화면이 채운다.
//
// 권한이 없는 메뉴 항목은 숨긴다(README "권한이 없는 메뉴는 사이드바에서 숨깁니다").
// "감사 로그"처럼 권한은 있으나 기능이 아직 없는 항목(A-04 미착수)은 숨기지 않고
// `미구현` 배지와 함께 비활성 상태로 보여준다(design_handoff의 표시 방식과 동일).

export type AppShellArea = "generate" | "admin";

type NavItem = {
  key: string;
  label: string;
  /** 없으면 항상 노출(예: Workspace) */
  permission?: string;
  /** 권한은 있지만 백엔드 기능이 아직 없는 항목 - 숨기지 않고 배지와 함께 비활성 처리 */
  unimplemented?: boolean;
};

// GENERATE 영역: design_handoff "2 Create.dc.html" / "3 Review.dc.html" 사이드바 공통 상단.
const GENERATE_NAV_ITEMS: NavItem[] = [
  { key: "workspace", label: "Workspace" },
  { key: "promptLibrary", label: "Prompt Library", permission: "prompts:reuse" },
  { key: "taskHistory", label: "Task History", permission: "history:read" },
  { key: "assets", label: "Assets", permission: "history:read" }
];

// ADMIN 영역: design_handoff "4 Admin.dc.html" 사이드바 공통 상단.
// 감사 로그는 A-04(TASKS.md) 착수 전까지 백엔드가 없어 "미구현" 배지를 유지한다.
const ADMIN_NAV_ITEMS: NavItem[] = [
  { key: "adminRoles", label: "역할 & 권한", permission: "roles:read" },
  { key: "adminUsers", label: "사용자", permission: "users:read" },
  { key: "adminCatalog", label: "프롬프트 카탈로그", permission: "prompt-catalog:read" },
  { key: "adminWorkflows", label: "워크플로 정의", permission: "workflows:read" },
  { key: "adminSandbox", label: "Sandbox Pod", permission: "sandbox:read" },
  { key: "adminAuditLog", label: "감사 로그", permission: "roles:read", unimplemented: true }
];

export type AppShellProps = {
  user: User | null;
  area: AppShellArea;
  /** 현재 활성화된 1차 메뉴 key (GENERATE_NAV_ITEMS/ADMIN_NAV_ITEMS의 key) */
  activeItem: string;
  /** 1차 메뉴 클릭 시 호출. 실제 라우팅 연결은 화면 이관 시점(E-02+)에 결정 */
  onNavigate: (key: string) => void;
  headerEyebrow?: React.ReactNode;
  headerTitle: React.ReactNode;
  headerActions?: React.ReactNode;
  /** 사이드바 1차 메뉴 아래, 화면별 보조 영역(스텝 트래커 · 필터 · 카탈로그 트리 등) */
  sidebarExtra?: React.ReactNode;
  /** 사이드바 최하단 고정 영역(서비스 상태 · 보관 기한 안내 등) */
  sidebarFooter?: React.ReactNode;
  /** 우측 340px 패널(Run Summary 등). 생략하면 본문이 전체 폭을 차지 */
  rightPanel?: React.ReactNode;
  children: React.ReactNode;
};

export function AppShell({
  user,
  area,
  activeItem,
  onNavigate,
  headerEyebrow,
  headerTitle,
  headerActions,
  sidebarExtra,
  sidebarFooter,
  rightPanel,
  children
}: AppShellProps) {
  const navItems = area === "admin" ? ADMIN_NAV_ITEMS : GENERATE_NAV_ITEMS;
  const groupLabel = area === "admin" ? "ADMIN" : "GENERATE";
  const visibleNavItems = navItems.filter((item) => !item.permission || canUse(user, item.permission));

  return (
    <div className="v3-shell">
      <nav className="v3-sidebar" aria-label="주 메뉴">
        <div className="v3-sidebar-brand">
          <img className="v3-sidebar-brand-mark" src="/studio/favicon.png" alt="" aria-hidden="true" />
          <div className="v3-sidebar-brand-name">DOBEDUB</div>
        </div>

        <div className="v3-sidebar-group-label">{groupLabel}</div>
        <div className="v3-sidebar-nav">
          {visibleNavItems.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`v3-sidebar-nav-item${item.key === activeItem ? " is-active" : ""}`}
              disabled={item.unimplemented}
              aria-current={item.key === activeItem ? "page" : undefined}
              onClick={() => {
                if (!item.unimplemented) {
                  onNavigate(item.key);
                }
              }}
            >
              <span>{item.label}</span>
              {item.unimplemented ? <span className="v3-sidebar-nav-item-badge">미구현</span> : null}
            </button>
          ))}
        </div>

        {sidebarExtra ? <div className="v3-sidebar-extra">{sidebarExtra}</div> : null}
        {sidebarFooter ? <div className="v3-sidebar-footer">{sidebarFooter}</div> : null}
      </nav>

      <div className="v3-main">
        <header className="v3-header">
          <div>
            {headerEyebrow ? <div className="v3-header-eyebrow">{headerEyebrow}</div> : null}
            <div className="v3-header-title">{headerTitle}</div>
          </div>
          {headerActions ? <div className="v3-header-actions">{headerActions}</div> : null}
        </header>

        <div className={`v3-body${rightPanel ? " has-right-panel" : ""}`}>
          <div className="v3-content">{children}</div>
          {rightPanel ? <aside className="v3-right-panel">{rightPanel}</aside> : null}
        </div>
      </div>
    </div>
  );
}
