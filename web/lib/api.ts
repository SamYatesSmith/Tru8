import { API_BASE_URL, API_VERSION } from "@shared/constants";
import type {
  CreateCheckRequest,
  CreateCheckResponse,
  CheckListResponse,
  Check,
  UserProfileResponse,
  UserUsageResponse,
  ApiError as ApiErrorType
} from "@shared/types";

const API_URL = `${API_BASE_URL}/api/${API_VERSION}`;

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

// Case conversion utilities for frontend-backend integration
function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

function toSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

function convertKeysToCamelCase(obj: any): any {
  if (Array.isArray(obj)) {
    return obj.map(convertKeysToCamelCase);
  }
  
  if (obj !== null && typeof obj === 'object') {
    const converted: any = {};
    for (const [key, value] of Object.entries(obj)) {
      const camelKey = toCamelCase(key);
      converted[camelKey] = convertKeysToCamelCase(value);
    }
    return converted;
  }
  
  return obj;
}

function convertKeysToSnakeCase(obj: any): any {
  if (Array.isArray(obj)) {
    return obj.map(convertKeysToSnakeCase);
  }
  
  if (obj !== null && typeof obj === 'object') {
    const converted: any = {};
    for (const [key, value] of Object.entries(obj)) {
      const snakeKey = toSnakeCase(key);
      converted[snakeKey] = convertKeysToSnakeCase(value);
    }
    return converted;
  }
  
  return obj;
}

async function apiRequest(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null
) {
  const url = `${API_URL}${endpoint}`;
  
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  // Convert request body from camelCase to snake_case
  let body = options.body;
  if (body && typeof body === 'string' && headers["Content-Type"]?.includes("application/json")) {
    try {
      const parsed = JSON.parse(body);
      const converted = convertKeysToSnakeCase(parsed);
      body = JSON.stringify(converted);
    } catch {
      // Keep original body if JSON parsing fails
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
    body,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.detail || errorData.message || `HTTP ${response.status}`
    );
  }

  const responseData = await response.json();
  // Convert response from snake_case to camelCase
  return convertKeysToCamelCase(responseData);
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

export async function uploadFile(
  file: File,
  token: string | null
): Promise<{ success: boolean; filePath: string; filename: string; contentType: string; size: number }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/checks/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      // Don't set Content-Type for FormData - browser will set it with boundary
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.detail || errorData.message || `HTTP ${response.status}`
    );
  }

  const responseData = await response.json();
  return convertKeysToCamelCase(responseData);
}

export async function createCheck(
  data: CreateCheckRequest,
  token: string | null
): Promise<CreateCheckResponse> {
  let filePath: string | undefined;
  
  // Step 1: Upload file if present
  if (data.file) {
    const uploadResult = await uploadFile(data.file, token);
    filePath = uploadResult.filePath;
  }

  // Step 2: Create check with JSON data
  return apiRequest(
    "/checks",
    {
      method: "POST",
      body: JSON.stringify({
        inputType: data.inputType, // Will be converted to input_type
        content: data.content,
        url: data.url,
        filePath: filePath, // Will be converted to file_path
      }),
    },
    token
  );
}

export async function getChecks(
  token: string,
  skip: number = 0,
  limit: number = 20
): Promise<CheckListResponse> {
  return apiRequest(
    `/checks?skip=${skip}&limit=${limit}`,
    { method: "GET" },
    token
  );
}

export async function getCheck(checkId: string, token: string): Promise<Check> {
  return apiRequest(`/checks/${checkId}`, { method: "GET" }, token);
}

export async function getCheckProgress(checkId: string, token: string) {
  return apiRequest(`/checks/${checkId}/progress`, { method: "GET" }, token);
}