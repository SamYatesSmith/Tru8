const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Backend API Client
 *
 * For client components: Pass token from useAuth().getToken()
 * For server components: Pass token from auth().getToken()
 *
 * Backend Integration:
 * - Base URL: http://localhost:8000/api/v1
 * - Auth: Bearer token from Clerk
 * - Endpoints:
 *   - GET /users/me - Auto-creates user if not exists (3 credits)
 *   - POST /checks - Create fact-check
 *   - GET /checks - Get user's checks
 *   - POST /payments/create-checkout-session - Stripe checkout
 */
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  /**
   * Generic request method with JWT injection
   * @param token - Optional Clerk JWT token for authenticated requests
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    token?: string | null
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add auth token if available
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
  }

  /**
   * GET /api/v1/users/me
   * Returns user profile with credits
   * Auto-creates user if doesn't exist (first login)
   *
   * Backend Logic (backend/app/api/v1/users.py:10-31):
   * - Verifies Clerk JWT token
   * - Finds user by Clerk ID
   * - If not found, creates user with 3 credits
   * - Returns user object with credits, subscription status
   */
  async getCurrentUser(token?: string | null) {
    return this.request('/api/v1/users/me', {}, token);
  }

  /**
   * GET /api/v1/users/profile
   * Returns detailed user profile with usage stats
   */
  async getUserProfile(token?: string | null) {
    return this.request('/api/v1/users/profile', {}, token);
  }

  /**
   * POST /api/v1/checks
   * Create a new fact-check
   */
  async createCheck(
    data: {
      input_type: 'url' | 'text' | 'image' | 'video';
      content?: string;
      url?: string;
      file_path?: string;
    },
    token?: string | null
  ) {
    return this.request('/api/v1/checks', {
      method: 'POST',
      body: JSON.stringify(data),
    }, token);
  }

  /**
   * GET /api/v1/checks
   * Get user's fact-check history
   */
  async getChecks(token?: string | null) {
    return this.request('/api/v1/checks', {}, token);
  }

  /**
   * POST /api/v1/payments/create-checkout-session
   * Create Stripe checkout session for Professional plan
   *
   * Request: { price_id: string, plan: "professional" }
   * Response: { session_id: string, url: string }
   *
   * After payment:
   * - Stripe webhook creates Subscription record
   * - User upgraded to Professional tier (40 credits/month)
   */
  async createCheckoutSession(
    data: {
      price_id: string;
      plan: string;
    },
    token?: string | null
  ) {
    return this.request('/api/v1/payments/create-checkout-session', {
      method: 'POST',
      body: JSON.stringify(data),
    }, token);
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
