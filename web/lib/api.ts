import { API_BASE_URL, API_VERSION } from "@/lib/constants";

const API_URL = `${API_BASE_URL}/api/${API_VERSION}`;

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiRequest(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null
) {
  const url = `${API_URL}${endpoint}`;
  
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.detail || `HTTP ${response.status}`
    );
  }

  return response.json();
}

export async function getCurrentUser(token: string) {
  return apiRequest("/auth/me", { method: "GET" }, token);
}

export async function getUserProfile(token: string) {
  return apiRequest("/users/profile", { method: "GET" }, token);
}

export async function getUserUsage(token: string) {
  return apiRequest("/users/usage", { method: "GET" }, token);
}

export async function createCheck(
  data: {
    inputType: string;
    content?: string;
    url?: string;
    file?: File;
  },
  token: string | null
) {
  if (data.file) {
    // Handle file upload
    const formData = new FormData();
    formData.append("input_type", data.inputType);
    formData.append("file", data.file);

    const response = await fetch(`${API_URL}/checks`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        response.status,
        errorData.detail || `HTTP ${response.status}`
      );
    }

    return response.json();
  } else {
    // Handle JSON data
    return apiRequest(
      "/checks",
      {
        method: "POST",
        body: JSON.stringify({
          input_type: data.inputType,
          content: data.content,
          url: data.url,
        }),
      },
      token
    );
  }
}

export async function getChecks(
  token: string,
  skip: number = 0,
  limit: number = 20
) {
  return apiRequest(
    `/checks?skip=${skip}&limit=${limit}`,
    { method: "GET" },
    token
  );
}

export async function getCheck(checkId: string, token: string) {
  return apiRequest(`/checks/${checkId}`, { method: "GET" }, token);
}

export async function getCheckProgress(checkId: string, token: string) {
  return apiRequest(`/checks/${checkId}/progress`, { method: "GET" }, token);
}