export type RecipeChatResponse = {
  html_response: string;
};

export type RecipeApiError = {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
    trace_id?: string;
  };
};

function getApiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) {
    throw new Error(
      "Missing NEXT_PUBLIC_API_BASE_URL. Set it in Frontend/.env.local (e.g. http://127.0.0.1:8000)."
    );
  }
  return base.replace(/\/+$/, "");
}

function buildUrl(path: string): string {
  const base = getApiBaseUrl();
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

type UnknownJson = unknown;

async function readJsonSafe(res: Response): Promise<UnknownJson> {
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as unknown;
  const text = await res.text();
  return { raw: text } as unknown;
}

export async function sendChatMessage(message: string, language: string = "en"): Promise<RecipeChatResponse> {
  const res = await fetch(buildUrl("/api/recipe/chat/"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, language }),
  });

  const data = (await readJsonSafe(res)) as RecipeChatResponse & RecipeApiError;

  if (!res.ok) {
    throw new Error(data?.error?.message || `Chat request failed with status ${res.status}.`);
  }
  if (!data || typeof data.html_response !== "string") {
    throw new Error("Invalid response from server (missing html_response).");
  }
  return { html_response: data.html_response };
}

export async function uploadCsv(formData: FormData, language: string = "en"): Promise<RecipeChatResponse> {
  formData.append("language", language);
  const res = await fetch(buildUrl("/api/recipe/upload/"), {
    method: "POST",
    body: formData,
  });

  const data = (await readJsonSafe(res)) as RecipeChatResponse & RecipeApiError;

  if (!res.ok) {
    throw new Error(data?.error?.message || `Upload request failed with status ${res.status}.`);
  }
  if (!data || typeof data.html_response !== "string") {
    throw new Error("Invalid response from server (missing html_response).");
  }
  return { html_response: data.html_response };
}
