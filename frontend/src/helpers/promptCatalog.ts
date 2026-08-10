import { PromptCategory, PromptCatalogResponse, PromptTerm } from "../api/client";

export const PROMPT_SCOPE_ORDER = ["positive", "negative"];
export const FIXED_PROMPT_ROOT_CODES = new Set(["POSITIVE_ROOT", "NEGATIVE_ROOT"]);

export type PromptCatalogRenderGroup = {
  key: string;
  label: string;
  sortOrder: number;
  categories: PromptCategory[];
};

export type PromptCatalogRenderScope = {
  key: "positive" | "negative";
  label: string;
  termCount: number;
  groups: PromptCatalogRenderGroup[];
};

export function allPromptCatalogTerms(categories: PromptCategory[]) {
  return categories.flatMap((category) => category.terms || []);
}

export function promptCatalogCategories(catalog: PromptCatalogResponse | null): PromptCategory[] {
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

export function promptCatalogHasTerms(catalog: PromptCatalogResponse | null) {
  return promptCatalogCategories(catalog).some((category) => category.terms?.length);
}

export function selectedPromptKeywordsByScope(categories: PromptCategory[], selectedTermIds: number[]) {
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

export function promptCatalogRenderScopes(categories: PromptCategory[], includeEmptyCategories = false): PromptCatalogRenderScope[] {
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

export function promptCategoryScopeKey(category: PromptCategory): "positive" | "negative" {
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

export function promptCategoryGroupKey(category: PromptCategory) {
  const groupCode = (category.groupCode || "").toLowerCase();
  return groupCode || "uncategorized";
}

export function promptScopeAccordionKey(scopeKey: string) {
  return `scope:${scopeKey}`;
}

export function promptGroupAccordionKey(scopeKey: string, groupKey: string) {
  return `group:${scopeKey}:${groupKey}`;
}

export function promptCategoryAccordionKey(scopeKey: string, groupKey: string, categoryCode: string) {
  return `category:${scopeKey}:${groupKey}:${categoryCode}`;
}

export function promptAccordionDefaultKeys() {
  return new Set<string>();
}


// E-06: `PromptSceneStructure` 타입과 `PromptSceneStructurePreview`/`PromptTagRow`/
// `toPromptSceneStructure`/`objectValue`/`stringValue`/`stringList`/`namedStringLists`/
// `flattenNamedLists`/`PromptTermButton`는 구버전 `PromptBuilderModal`/`SystemPromptEditor`
// 전용이었고 어디서도 JSX로 그려지지 않는(호출부 0건) 고아 코드였다 - 구버전 모달 삭제
// 배치에서 함께 제거됨을 확인하고 뒤늦게 정리했다. `findPromptTermCategory`만 StudioShell
// 안에서 실사용 중이라 남긴다.
export function findPromptTermCategory(catalog: PromptCatalogResponse | null, termId: number) {
  return promptCatalogCategories(catalog).find((category) => (category.terms || []).some((term) => term.id === termId));
}
