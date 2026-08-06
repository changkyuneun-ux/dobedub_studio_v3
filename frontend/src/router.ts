export type StudioRoute = "login" | "studio" | "history" | "status" | "metadata" | "manual" | "admin";

export function routeFromLocation(pathname: string, hasUser: boolean): StudioRoute {
  if (pathname.endsWith("/login")) {
    return "login";
  }
  if (pathname.endsWith("/history")) {
    return hasUser ? "history" : "login";
  }
  if (pathname.endsWith("/status")) {
    return hasUser ? "status" : "login";
  }
  if (pathname.endsWith("/metadata")) {
    return hasUser ? "metadata" : "login";
  }
  if (pathname.endsWith("/manual")) {
    return hasUser ? "manual" : "login";
  }
  if (pathname.endsWith("/admin")) {
    return hasUser ? "admin" : "login";
  }
  if (pathname.endsWith("/app")) {
    return hasUser ? "studio" : "login";
  }
  return hasUser ? "studio" : "login";
}

export function routePath(route: StudioRoute): string {
  if (route === "login") {
    return "/studio/login";
  }
  if (route === "studio") {
    return "/studio/app";
  }
  if (route === "history") {
    return "/studio/history";
  }
  if (route === "status") {
    return "/studio/status";
  }
  if (route === "metadata") {
    return "/studio/metadata";
  }
  if (route === "manual") {
    return "/studio/manual";
  }
  return "/studio/admin";
}
