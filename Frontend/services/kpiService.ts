export type KpiChatResponse = {
  html_response: string;
};

export type KpiApiError = {
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
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalizedPath}`;
}

type UnknownJson = unknown;

async function readJsonSafeUnknown(res: Response): Promise<UnknownJson> {
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return (await res.json()) as unknown;
  }
  const text = await res.text();
  return { raw: text } as unknown;
}

export async function sendChatMessage(message: string, language: string = "en"): Promise<KpiChatResponse> {
  const res = await fetch(buildUrl("/api/kpi/chat/"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message, language }),
  });

  const data = (await readJsonSafeUnknown(res)) as KpiChatResponse & KpiApiError;

  if (!res.ok) {
    const msg =
      data?.error?.message ||
      `Chat request failed with status ${res.status}.`;
    throw new Error(msg);
  }

  if (!data || typeof data.html_response !== "string") {
    throw new Error("Invalid response from server (missing html_response). ");
  }

  return { html_response: data.html_response };
}

export async function uploadCsv(formData: FormData, language: string = "en"): Promise<KpiChatResponse> {
  formData.append("language", language);
  const res = await fetch(buildUrl("/api/kpi/upload/"), {
    method: "POST",
    body: formData,
  });

  const data = (await readJsonSafeUnknown(res)) as KpiChatResponse & KpiApiError;

  if (!res.ok) {
    const msg =
      data?.error?.message ||
      `Upload request failed with status ${res.status}.`;
    throw new Error(msg);
  }

  if (!data || typeof data.html_response !== "string") {
    throw new Error("Invalid response from server (missing html_response). ");
  }

  return { html_response: data.html_response };
}
