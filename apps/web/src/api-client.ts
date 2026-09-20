export function readSessionValue(key: string) {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeSessionValue(key: string, value: string) {
  try {
    sessionStorage.setItem(key, value);
  } catch {
    // Privacy modes may disable storage; the in-memory session still works.
  }
}

function removeSessionValue(key: string) {
  try {
    sessionStorage.removeItem(key);
  } catch {
    // Privacy modes may disable storage; clear the in-memory value below.
  }
}

let token = readSessionValue("sponge-session") ?? "";

export function getSessionToken() {
  return token;
}

export function setSessionToken(value: string) {
  token = value;
  if (value) writeSessionValue("sponge-session", value);
  else removeSessionValue("sponge-session");
}

let sessionRefresh: Promise<void> | null = null;

async function refreshSession() {
  sessionRefresh ??= (async () => {
    setSessionToken("");
    const response = await fetch("/api/v1/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    if (!response.ok)
      throw new Error((await response.text()).slice(0, 250));
    const session = await response.json();
    if (typeof session.token !== "string" || !session.token)
      throw new Error("Session service returned an invalid token");
    setSessionToken(session.token);
  })().finally(() => {
    sessionRefresh = null;
  });
  return sessionRefresh;
}

function authorizedOptions(options: RequestInit = {}) {
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", "Bearer " + token);
  else headers.delete("Authorization");
  return { ...options, headers };
}

export async function authenticatedFetch(
  input: RequestInfo | URL,
  options: RequestInit = {},
) {
  let response = await fetch(input, authorizedOptions(options));
  if (response.status !== 401) return response;
  await refreshSession();
  response = await fetch(input, authorizedOptions(options));
  return response;
}

function retryDelay(signal: AbortSignal | undefined, attempt: number) {
  return new Promise<void>((resolve, reject) => {
    const onAbort = () => {
      clearTimeout(timer);
      reject(signal?.reason);
    };
    const timer = setTimeout(
      () => {
        signal?.removeEventListener("abort", onAbort);
        resolve();
      },
      150 * (attempt + 1),
    );
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

export async function api(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
  retryTransient = false,
) {
  for (let attempt = 0; ; attempt++) {
    let response: Response;
    try {
      response = await authenticatedFetch("/api/v1" + path, {
        signal,
        method: body === undefined ? "GET" : "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: "Bearer " + token } : {}),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (error) {
      if (signal?.aborted || !retryTransient || attempt === 2) throw error;
      await retryDelay(signal, attempt);
      continue;
    }
    if (response.ok) return response.json();
    if (
      !retryTransient ||
      ![502, 503, 504].includes(response.status) ||
      attempt === 2
    )
      throw new Error((await response.text()).slice(0, 250));
    await retryDelay(signal, attempt);
  }
}

export async function uploadTerrain(
  bundleId: string,
  file: File,
  source: unknown,
) {
  const body = new FormData();
  body.append("file", file);
  body.append("source", JSON.stringify(source));
  const response = await authenticatedFetch(
    "/api/v1/bundles/" + bundleId + "/terrain-import",
    {
      method: "POST",
      headers: { Authorization: "Bearer " + token },
      body,
    },
  );
  if (!response.ok) throw new Error((await response.text()).slice(0, 600));
  return response.json();
}
