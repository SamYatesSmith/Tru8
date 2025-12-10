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
      cache: 'no-store',  // Prevent caching for real-time status updates
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}: ${response.statusText}` }));
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
   * PATCH /api/v1/users/profile
   * Update user profile (name, etc.)
   */
  async updateUserProfile(
    data: { name?: string },
    token?: string | null
  ) {
    return this.request('/api/v1/users/profile', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }, token);
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
      user_query?: string;  // Search Clarity feature
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
   * TODO: Not implemented - SSE currently uses query param auth
   */
  async createSSEToken(checkId: string, token?: string | null) {
    return this.request(`/api/v1/checks/${checkId}/sse-token`, {
      method: 'POST',
    }, token);
  }

  /**
   * GET /api/v1/payments/invoices
   * Fetch last 5 Stripe invoices (GAP #17)
   * TODO: Not implemented - planned for post-MVP
   */
  async getInvoices(token?: string | null) {
    return this.request('/api/v1/payments/invoices', {}, token);
  }

  /**
   * DELETE /api/v1/users/me
   * Delete user account and all associated data
   * Implements GDPR compliance - backend/app/api/v1/users.py:206
   */
  async deleteUser(userId: string, token?: string | null) {
    return this.request('/api/v1/users/me', {
      method: 'DELETE',
    }, token);
  }

  /**
   * POST /api/v1/payments/cancel-subscription
   * Cancel subscription at end of billing period
   * Backend: backend/app/api/v1/payments.py:321
   */
  async cancelSubscription(token?: string | null) {
    return this.request('/api/v1/payments/cancel-subscription', {
      method: 'POST',
    }, token);
  }

  /**
   * POST /api/v1/payments/reactivate-subscription
   * Reactivate subscription before period end
   * Backend: backend/app/api/v1/payments.py:418
   */
  async reactivateSubscription(token?: string | null) {
    return this.request('/api/v1/payments/reactivate-subscription', {
      method: 'POST',
    }, token);
  }

  // ============================================================================
  // Full Sources List - Pro Feature
  // ============================================================================

  /**
   * GET /api/v1/checks/{check_id}/sources
   * Get all sources reviewed for a check (Pro feature)
   * Backend: backend/app/api/v1/checks.py - get_check_sources
   */
  async getCheckSources(
    checkId: string,
    options?: {
      includeFiltered?: boolean;
      sortBy?: 'relevance' | 'credibility' | 'date';
    },
    token?: string | null
  ): Promise<{
    checkId: string;
    totalSources: number;
    includedCount: number;
    filteredCount: number;
    legacyCheck: boolean;
    message?: string;
    claims?: any[];
    filterBreakdown?: Record<string, number>;
    requiresUpgrade?: boolean;
  }> {
    const params = new URLSearchParams();
    if (options?.includeFiltered !== undefined) {
      params.append('include_filtered', String(options.includeFiltered));
    }
    if (options?.sortBy) {
      params.append('sort_by', options.sortBy);
    }
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request(`/api/v1/checks/${checkId}/sources${query}`, {}, token);
  }

  /**
   * GET /api/v1/checks/{check_id}/sources/export
   * Export sources as CSV, BibTeX, or APA format (Pro feature)
   * Backend: backend/app/api/v1/checks.py - export_check_sources
   */
  async exportCheckSources(
    checkId: string,
    format: 'csv' | 'bibtex' | 'apa',
    includeFiltered: boolean = false,
    token?: string | null
  ): Promise<Blob> {
    const params = new URLSearchParams();
    params.append('format', format);
    params.append('include_filtered', String(includeFiltered));

    const response = await fetch(`${API_BASE_URL}/api/v1/checks/${checkId}/sources/export?${params.toString()}`, {
      method: 'GET',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Export failed');
    }

    return response.blob();
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
