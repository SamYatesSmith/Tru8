const API_URL = `${process.env.EXPO_PUBLIC_API_URL}/api/${process.env.EXPO_PUBLIC_API_VERSION}`;

class ApiError extends Error {
  constructor(
    public status: number, 
    message: string,
    public code?: string,
    public retryable: boolean = false
  ) {
    super(message);
    this.name = "ApiError";
  }
}

class NetworkError extends Error {
  constructor(message: string = 'Network request failed') {
    super(message);
    this.name = "NetworkError";
    this.code = 'NETWORK_ERROR';
  }
  
  code: string;
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

interface ApiRequestOptions extends RequestInit {
  retries?: number;
  retryDelay?: number;
}

async function apiRequest(
  endpoint: string,
  options: ApiRequestOptions = {},
  token?: string
): Promise<any> {
  const { retries = 2, retryDelay = 1000, ...requestOptions } = options;
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

  const makeRequest = async (attemptCount: number): Promise<Response> => {
    try {
      const response = await fetch(url, {
        ...requestOptions,
        headers,
        body,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const isRetryable = response.status >= 500 || response.status === 429;
        
        throw new ApiError(
          response.status,
          errorData.detail || `HTTP ${response.status}`,
          errorData.code,
          isRetryable
        );
      }

      return response;
    } catch (error) {
      // Network errors or fetch failures
      if (error instanceof Error && (error.name === 'TypeError' || error.message.includes('Network request failed'))) {
        throw new NetworkError('Unable to connect to server. Please check your internet connection.');
      }
      
      // Re-throw ApiError
      if (error instanceof Error && error.name === 'ApiError') {
        throw error;
      }
      
      // Other errors
      throw new ApiError(500, error instanceof Error ? error.message : 'An unexpected error occurred');
    }
  };

  // Retry logic
  let lastError: Error = new ApiError(500, "Unknown error");
  
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await makeRequest(attempt);
      
      // Success - convert response to camelCase
      const responseText = await response.text();
      if (!responseText) return null;

      try {
        const data = JSON.parse(responseText);
        return convertKeysToCamelCase(data);
      } catch {
        return responseText;
      }
    } catch (error) {
      lastError = error as Error;
      
      // Don't retry for non-retryable errors
      if (error instanceof Error && error.name === 'ApiError' && !(error as ApiError).retryable) {
        break;
      }
      
      // Don't retry on last attempt
      if (attempt === retries) {
        break;
      }
      
      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, retryDelay * Math.pow(2, attempt)));
    }
  }
  
  throw lastError;
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
    // Handle file upload - use the upload endpoint first, then create check
    const uploadData = await uploadFile(data.file, token);
    
    // Create check with uploaded file path
    return apiRequest(
      "/checks",
      {
        method: "POST",
        body: JSON.stringify({
          inputType: data.inputType,
          filePath: uploadData.filePath,
        }),
      },
      token
    );
  } else {
    return apiRequest(
      "/checks",
      {
        method: "POST",
        body: JSON.stringify({
          inputType: data.inputType,
          content: data.content,
          url: data.url,
        }),
      },
      token
    );
  }
}

export async function uploadFile(file: any, token: string) {
  const formData = new FormData();
  formData.append("file", {
    uri: file.uri,
    type: file.type || 'image/jpeg',
    name: file.name || 'image.jpg',
  } as any);

  const response = await fetch(`${API_URL}/checks/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      // Don't set Content-Type for FormData - let the browser set it with boundary
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

  const responseData = await response.json();
  return convertKeysToCamelCase(responseData);
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

export async function getUserProfile(token: string) {
  return apiRequest("/users/profile", { method: "GET" }, token);
}

export async function getUserUsage(token: string) {
  return apiRequest("/users/usage", { method: "GET" }, token);
}