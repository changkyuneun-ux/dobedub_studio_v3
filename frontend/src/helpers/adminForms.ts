import { User, canUseAny } from "../auth";
import { AdminUser, PermissionGovernance } from "../api/client";

export const ADMIN_USER_PERMISSIONS = ["users:read"];
export const ADMIN_PERMISSION_PERMISSIONS = ["roles:read"];
export const ADMIN_WORKFLOW_PERMISSIONS = ["workflows:write", "workflows:activate"];
export const ADMIN_CATALOG_PERMISSIONS = ["prompt-catalog:write"];
export const ADMIN_SANDBOX_POD_PERMISSIONS = ["sandbox:read"];
export const ADMIN_CONSOLE_PERMISSIONS = [
  ...ADMIN_USER_PERMISSIONS,
  ...ADMIN_PERMISSION_PERMISSIONS,
  ...ADMIN_WORKFLOW_PERMISSIONS,
  ...ADMIN_CATALOG_PERMISSIONS,
  ...ADMIN_SANDBOX_POD_PERMISSIONS
];

export function canUseAdminConsole(user: User | null) {
  return canUseAny(user, ADMIN_CONSOLE_PERMISSIONS);
}

export function canUseAdminUsers(user: User | null) {
  return canUseAny(user, ADMIN_USER_PERMISSIONS);
}

export function canUseAdminPermissions(user: User | null) {
  return canUseAny(user, ADMIN_PERMISSION_PERMISSIONS);
}

export function canUseAdminWorkflows(user: User | null) {
  return canUseAny(user, ADMIN_WORKFLOW_PERMISSIONS);
}

export function canUseAdminCatalog(user: User | null) {
  return canUseAny(user, ADMIN_CATALOG_PERMISSIONS);
}

export function canUseAdminSandboxPod(user: User | null) {
  return canUseAny(user, ADMIN_SANDBOX_POD_PERMISSIONS);
}

export const ADMIN_ROLE_GUIDE = [
  { role: "SUPER_ADMIN", description: "전체 운영 및 시스템 설정 권한. 기본 관리자 계정에만 권장합니다." },
  { role: "ADMIN", description: "사용자, 워크플로우, Prompt Catalog 등 운영 관리 권한." },
  { role: "OPERATOR", description: "영상 생성, 작업 조회, 프롬프트 리뷰 등 실무 작업 권한." },
  { role: "VIEWER", description: "작업과 결과 조회 중심의 읽기 전용 권한." }
];

export const ADMIN_PERMISSION_OPTIONS = [
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

export function adminUserFormFrom(user: AdminUser | null): Record<string, string> {
  return {
    id: user?.id || "",
    name: user?.name || "",
    role: user?.role || "OPERATOR",
    isActive: user?.isActive === false ? "false" : "true",
    permissions: (user?.extraPermissionCodes || user?.permissions || []).join(", "),
    password: ""
  };
}

export function adminPermissionsFromText(value: string): string[] {
  return value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function adminPermissionsToText(values: string[]) {
  return Array.from(new Set(values.map((item) => item.trim()).filter(Boolean))).join(", ");
}

export function adminPermissionOptions(governance: PermissionGovernance | null) {
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

export function adminRoleOptions(governance: PermissionGovernance | null) {
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

export function adminRolePermissionCodes(governance: PermissionGovernance | null, roleCode: string) {
  return adminRoleOptions(governance).find((item) => item.code === roleCode)?.permissionCodes || [];
}

export function adminPermissionLabel(governance: PermissionGovernance | null, permissionCode: string) {
  return adminPermissionOptions(governance).find((item) => item.value === permissionCode)?.label || permissionCode;
}

