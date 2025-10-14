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
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
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
   * GET /api/v1/users/profile
   * Returns user profile with credits and stats
   * Auto-creates user if doesn't exist (first login)
   *
   * Backend Logic (backend/app/api/v1/users.py:12-69):
   * - Verifies Clerk JWT token
   * - Finds user by Clerk ID
   * - If not found, creates user with 3 credits
   * - Returns user object with credits, subscription status, stats
   */
  async getCurrentUser(token?: string | null) {
    return this.request('/api/v1/users/profile', {}, token);
  }

  /**
   * GET /api/v1/users/usage
   * Returns detailed usage statistics
   */
  async getUsage(token?: string | null) {
    return this.request('/api/v1/users/usage', {}, token);
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
   * Get user's fact-check history with pagination
   */
  async getChecks(token?: string | null, skip: number = 0, limit: number = 20) {
    return this.request(`/api/v1/checks?skip=${skip}&limit=${limit}`, {}, token);
  }

  /**
   * GET /api/v1/checks/{id}
   * Get single check with full details (claims, evidence)
   */
  async getCheckById(checkId: string, token?: string | null) {
    return this.request(`/api/v1/checks/${checkId}`, {}, token);
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

  /**
   * GET /api/v1/payments/subscription-status
   * Get current subscription details
   */
  async getSubscriptionStatus(token?: string | null) {
    return this.request('/api/v1/payments/subscription-status', {}, token);
  }

  /**
   * POST /api/v1/payments/create-portal-session
   * Create Stripe billing portal session
   */
  async createBillingPortalSession(token?: string | null) {
    return this.request('/api/v1/payments/create-portal-session', {
      method: 'POST',
    }, token);
  }

  /**
   * POST /api/v1/checks/{id}/sse-token
   * Generate short-lived token for SSE connection (GAP #16)
   * NEW ENDPOINT - Requires backend implementation
   */
  async createSSEToken(checkId: string, token?: string | null) {
    return this.request(`/api/v1/checks/${checkId}/sse-token`, {
      method: 'POST',
    }, token);
  }

  /**
   * GET /api/v1/payments/invoices
   * Fetch last 5 Stripe invoices (GAP #17)
   * NEW ENDPOINT - Requires backend implementation
   */
  async getInvoices(token?: string | null) {
    return this.request('/api/v1/payments/invoices', {}, token);
  }

  /**
   * DELETE /api/v1/users/me
   * Delete user account and all associated data (GAP #18)
   * NEW ENDPOINT - Requires backend implementation
   */
  async deleteUser(userId: string, token?: string | null) {
    return this.request('/api/v1/users/me', {
      method: 'DELETE',
    }, token);
  }

  /**
   * POST /api/v1/payments/cancel-subscription
   * Cancel subscription at end of billing period (GAP #19)
   * NEW ENDPOINT - Requires backend implementation
   */
  async cancelSubscription(token?: string | null) {
    return this.request('/api/v1/payments/cancel-subscription', {
      method: 'POST',
    }, token);
  }

  /**
   * POST /api/v1/payments/reactivate-subscription
   * Reactivate subscription before period end (GAP #19)
   * NEW ENDPOINT - Requires backend implementation
   */
  async reactivateSubscription(token?: string | null) {
    return this.request('/api/v1/payments/reactivate-subscription', {
      method: 'POST',
    }, token);
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
