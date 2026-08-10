import { PromptCategoryGroup, PromptCategory, PromptCatalogResponse, PromptTerm } from "../api/client";

export type PromptCatalogAdminScope = {
  key: "positive" | "negative";
  label: string;
  groups: PromptCategoryGroup[];
};


export function promptCatalogAdminScopes(groups: PromptCategoryGroup[]): PromptCatalogAdminScope[] {
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

export function promptAdminScopeAccordionKey(scopeKey: string) {
  return `admin-scope:${scopeKey}`;
}

export function promptAdminGroupAccordionKey(scopeKey: string, groupId: number) {
  return `admin-group:${scopeKey}:${groupId}`;
}

export function promptAdminSubcategoryAccordionKey(subcategoryId: number) {
  return `admin-subcategory:${subcategoryId}`;
}

export type PromptCatalogAdminContentProps = {
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

export function categoryGroupFormFrom(group: PromptCategoryGroup | null, scopeKey: "positive" | "negative"): Record<string, string> {
  return {
    code: group?.code || (scopeKey === "negative" ? "negative_" : "positive_"),
    nameKo: group?.nameKo || "",
    nameEn: group?.nameEn || "",
    description: group?.description || "",
    sortOrder: group?.sortOrder ? String(group.sortOrder) : "100"
  };
}

export function categoryGroupCodeFromForm(form: Record<string, string>, scopeKey: "positive" | "negative", group: PromptCategoryGroup | null) {
  if (group?.code) {
    return group.code;
  }
  const prefix = scopeKey === "negative" ? "negative" : "positive";
  return `${prefix}_${adminCodeSlug(form.nameEn || form.nameKo || "category")}`;
}

export function categoryFormFrom(category: PromptCategory | null, groupKey = "", parentCategoryId?: number, groupId?: number): Record<string, string | boolean> {
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

export function subcategoryCodeFromForm(form: Record<string, string | boolean>, category: PromptCategory | null) {
  if (category?.code) {
    return category.code;
  }
  return adminCodeSlug(String(form.nameEn || form.nameKo || "subcategory")).toUpperCase();
}

export function adminCodeSlug(value: string) {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return slug || `item_${Date.now()}`;
}

export function promptTermCodeFromForm(form: Record<string, string>, term: PromptTerm | null | undefined, category: PromptCategory | null) {
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

export function termFormFrom(term: PromptTerm | null | undefined, category: PromptCategory | null): Record<string, string> {
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

