// E-01 후속: design_handoff_dobedub_v3의 업무 흐름(1 Access · 2 Create[S1~S5] ·
// 3 Review · 4 Admin) 기준으로 라우트를 재설계했다. 이전에는 기능 이름을 그대로 쓴
// 평평한 목록(login/studio/history/status/metadata/manual/admin)이었고, 화면
// README의 흐름 구분(예: status·metadata가 실은 "4 Admin.dc.html" 소속, manual이
// "1 Access.dc.html" 소속)과 코드가 어긋나 있었다. 문자열 리터럴 하나로 남긴 이유는
// main.tsx 전역에 `route === "..."` 비교가 많아, flow/screen을 객체로 쪼개면 변경
// 범위가 라우팅과 무관한 곳까지 커지기 때문이다 - 대신 "flow.screen" 접두 규칙으로
// 흐름을 표현한다.
//
// design_handoff 화면 id 대응:
//   access.login      — 6a 로그인
//   access.manual     — 6b 사용자 매뉴얼 ("1 Access.dc.html" 소속)
//   create.load       — 2a · S1 이미지 로드 (신규 구현, E-02)
//   create.workspace  — 2b~2f를 아직 분리하지 않은 구버전 전체 워크스페이스(임시).
//                       E-02가 진행되며 create.prompt/create.segments/create.confirm/
//                       create.progress/create.result로 분할되고 이 값은 제거된다.
//   review.history    — 3a 작업 이력 ("3 Review.dc.html" 소속)
//   admin.console      — 4 Admin의 users/roles/catalog/workflows/sandbox 통합 콘솔
//   admin.status       — 6c 시스템 상태 ("4 Admin.dc.html" 소속, 구버전엔 독립 라우트였음)
//   admin.metadata     — 6d 메타데이터 ("4 Admin.dc.html" 소속, 구버전엔 독립 라우트였음)
export type StudioRoute =
  | "access.login"
  | "access.manual"
  | "create.load"
  | "create.workspace"
  | "review.history"
  | "admin.console"
  | "admin.status"
  | "admin.metadata";

// 구버전 경로(/studio/history 등)로 온 북마크·외부 링크가 깨지지 않도록 옛 경로
// 마지막 세그먼트 → 신규 StudioRoute로 매핑. 신규 경로는 routePath()가 만드는
// flow/screen 2단 경로(/studio/admin/status 등)를 기준으로 한다.
const LEGACY_LAST_SEGMENT_ROUTE: Record<string, StudioRoute> = {
  login: "access.login",
  manual: "access.manual",
  studio: "create.workspace",
  history: "review.history",
  admin: "admin.console",
  status: "admin.status",
  metadata: "admin.metadata"
};

const ROUTE_PATH: Record<StudioRoute, string> = {
  "access.login": "/studio/access/login",
  "access.manual": "/studio/access/manual",
  "create.load": "/studio/create/load",
  "create.workspace": "/studio/create/workspace",
  "review.history": "/studio/review/history",
  "admin.console": "/studio/admin/console",
  "admin.status": "/studio/admin/status",
  "admin.metadata": "/studio/admin/metadata"
};

const PATH_TO_ROUTE: Record<string, StudioRoute> = Object.fromEntries(
  Object.entries(ROUTE_PATH).map(([route, path]) => [path, route as StudioRoute])
) as Record<string, StudioRoute>;

export function routeFromLocation(pathname: string, hasUser: boolean): StudioRoute {
  if (!hasUser) {
    return "access.login";
  }
  const exact = PATH_TO_ROUTE[pathname];
  if (exact) {
    return exact;
  }
  const lastSegment = pathname.split("/").filter(Boolean).pop() || "";
  const legacy = LEGACY_LAST_SEGMENT_ROUTE[lastSegment];
  if (legacy) {
    return legacy;
  }
  return "create.workspace";
}

export function routePath(route: StudioRoute): string {
  return ROUTE_PATH[route];
}
