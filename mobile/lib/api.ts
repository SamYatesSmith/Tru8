const API_URL = `${process.env.EXPO_PUBLIC_API_URL}/api/${process.env.EXPO_PUBLIC_API_VERSION}`;

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiRequest(
  endpoint: string,
  options: RequestInit = {},
  token?: string
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

export async function createCheck(
  data: {
    inputType: string;
    content?: string;
    url?: string;
    file?: any; // React Native file object
  },
  token: string
) {
  if (data.file) {
    // Handle file upload
    const formData = new FormData();
    formData.append("input_type", data.inputType);
    formData.append("file", {
      uri: data.file.uri,
      type: data.file.type,
      name: data.file.name,
    } as any);

    const response = await fetch(`${API_URL}/checks`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "multipart/form-data",
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