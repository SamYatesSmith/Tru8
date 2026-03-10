const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * SSE Progress event from streaming endpoint
 */
export interface StreamingProgressEvent {
  type: 'progress';
  checkId: string;
  stage: 'starting' | 'ingest' | 'extract' | 'factcheck' | 'retrieve' | 'select' | 'decompose' | 'analyze' | 'query';
  progress: number;
  message: string;
  timeEstimate: string;
}

/**
 * User statistics for dashboard insights
 */
export interface UserStats {
  totalChecks: number;
  checksThisMonth: number;
  totalSourcesAnalyzed: number;
  totalClaimsAnalyzed: number;
  claimTypeBreakdown: Record<string, number>;
  domainBreakdown: Record<string, number>;
  topDomain: string | null;
  memberSince: string | null;
}

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
 *   - POST /checks - Create analysis check
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
   * GET /api/v1/users/stats
   * Returns aggregated user statistics for dashboard insights
   */
  async getUserStats(token?: string | null): Promise<UserStats> {
    return this.request<UserStats>('/api/v1/users/stats', {}, token);
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
   * POST /api/v1/feedback
   * Submit user feedback (testing period)
   */
  async submitFeedback(
    data: {
      type: string;
      message: string;
      checkId?: string | null;
      claimPosition?: number | null;
      claimText?: string | null;
      pageUrl: string;
      userEmail?: string | null;
    },
    token?: string | null
  ) {
    return this.request('/api/v1/feedback', {
      method: 'POST',
      body: JSON.stringify(data),
    }, token);
  }

  /**
   * POST /api/v1/checks
   * Create a new check (Celery-based, legacy)
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
   * POST /api/v1/checks/stream
   * Create a new check with inline SSE streaming.
   *
   * This endpoint runs the pipeline inline and streams progress directly.
   * No Celery worker required - eliminates infrastructure costs.
   *
   * @param data - Check input data
   * @param token - Auth token
   * @param onProgress - Callback for progress events
   * @param onComplete - Callback when check completes
   * @param onError - Callback on error
   * @returns Promise that resolves when stream ends
   */
  async createCheckStreaming(
    data: {
      input_type: 'url' | 'text' | 'image' | 'video';
      content?: string;
      url?: string;
      file_path?: string;
      user_query?: string;
    },
    token: string | null,
    callbacks: {
      onProgress?: (event: StreamingProgressEvent) => void;
      onComplete?: (checkId: string) => void;
      onError?: (error: string, checkId?: string) => void;
      onConnected?: (checkId: string) => void;
    }
  ): Promise<{ checkId: string }> {
    const response = await fetch(`${this.baseUrl}/api/v1/checks/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    // Get check ID from header - this is available immediately
    const checkId = response.headers.get('X-Check-Id') || '';

    // CRITICAL: If we have a checkId from header, trigger onConnected immediately
    // This ensures redirect happens even if SSE stream has buffering issues
    if (checkId && callbacks.onConnected) {
      callbacks.onConnected(checkId);
      // Return early - the page will redirect and we don't need to process the stream
      return { checkId };
    }

    // Parse SSE stream (fallback if header wasn't available)
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';
    let connectedFired = false;

    try {
      while (true) {
        const { done, value } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(line.slice(6));
              const eventCheckId = eventData.checkId || checkId;

              switch (eventData.type) {
                case 'connected':
                  if (!connectedFired) {
                    callbacks.onConnected?.(eventCheckId);
                    connectedFired = true;
                  }
                  break;
                case 'progress':
                  callbacks.onProgress?.({
                    type: 'progress',
                    checkId: eventCheckId,
                    stage: eventData.stage,
                    progress: eventData.progress,
                    message: eventData.message,
                    timeEstimate: eventData.timeEstimate,
                  });
                  break;
                case 'completed':
                  callbacks.onComplete?.(eventCheckId);
                  break;
                case 'error':
                  callbacks.onError?.(eventData.error, eventCheckId);
                  break;
                case 'heartbeat':
                  // Ignore heartbeats
                  break;
              }
            } catch (parseError) {
              // Silently ignore malformed SSE events
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    return { checkId };
  }

  /**
   * PATCH /api/v1/checks/{check_id}/select-claims
   * Submit selected claims for Phase 2 analysis (article mode)
   */
  async selectClaims(
    checkId: string,
    selectedPositions: number[],
    token?: string | null
  ): Promise<{ status: string; checkId: string; selectedPositions: number[]; selectedCount: number }> {
    return this.request(`/api/v1/checks/${checkId}/select-claims`, {
      method: 'PATCH',
      body: JSON.stringify({ selected_positions: selectedPositions }),
    }, token);
  }

  /**
   * PATCH /api/v1/checks/{check_id}/claims/{claim_id}/elements/{element_id}/bounty
   * Update bounty text on a claim element (G01: The Seeker)
   */
  async updateBountyText(
    checkId: string,
    claimId: string,
    elementId: string,
    text: string | null,
    token?: string | null
  ): Promise<{ status: string; bountyText: string | null }> {
    return this.request(`/api/v1/checks/${checkId}/claims/${claimId}/elements/${elementId}/bounty`, {
      method: 'PATCH',
      body: JSON.stringify({ text }),
    }, token);
  }

  /**
   * POST /api/v1/checks/{check_id}/claims/{claim_id}/elements/{element_id}/research
   * Start targeted re-search for a single element (G02)
   */
  async startElementResearch(
    checkId: string,
    claimId: string,
    elementId: string,
    token?: string | null
  ): Promise<{ status: string; message: string; elementId: string }> {
    return this.request(`/api/v1/checks/${checkId}/claims/${claimId}/elements/${elementId}/research`, {
      method: 'POST',
    }, token);
  }

  /**
   * GET /api/v1/checks/{check_id}/claims/{claim_id}/elements/{element_id}/research/status
   * Get re-search status for a single element (G02)
   */
  async getResearchStatus(
    checkId: string,
    claimId: string,
    elementId: string,
    token?: string | null
  ): Promise<{ status: string; message: string; newEvidenceCount?: number }> {
    return this.request(`/api/v1/checks/${checkId}/claims/${claimId}/elements/${elementId}/research/status`, {}, token);
  }

  /**
   * GET /api/v1/checks
   * Get user's check history with pagination
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
   * GET /api/v1/checks/{checkId}/videos
   * Get video recommendations for a check, optionally filtered by claim.
   */
  async getCheckVideos(checkId: string, claimId?: string | null, token?: string | null) {
    const params = claimId ? `?claim_id=${claimId}` : '';
    return this.request(`/api/v1/checks/${checkId}/videos${params}`, {}, token);
  }

  /**
   * POST /api/v1/payments/create-checkout-session
   * Create Stripe checkout session for a paid plan
   *
   * Request: { price_id: string, plan: "starter" | "professional" }
   * Response: { session_id: string, url: string }
   *
   * After payment:
   * - Stripe webhook creates Subscription record
   * - User upgraded to selected tier (starter: 40/month, professional: 200/month)
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
   * Generate short-lived, check-scoped token for SSE progress streaming.
   * Token is valid for 5 minutes. Use in EventSource URL instead of JWT.
   */
  async createSSEToken(checkId: string, token?: string | null): Promise<{ token: string; expiresIn: number }> {
    return this.request('/api/v1/checks/' + checkId + '/sse-token', {
      method: 'POST',
    }, token);
  }

  /**
   * GET /api/v1/payments/invoices
   * Fetch last 5 Stripe invoices (GAP #17)
   * POST-RELEASE TODO: Not implemented — planned for post-MVP
   */
  async getInvoices(_token?: string | null): Promise<never> {
    throw new Error('getInvoices is not yet implemented');
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
  // File Upload
  // ============================================================================

  /**
   * POST /api/v1/checks/upload
   * Upload an image file for OCR processing.
   * Returns { success, filePath, filename, contentType, size }.
   * Rate limited: 10/minute.
   */
  async uploadFile(
    file: File,
    token?: string | null
  ): Promise<{ success: boolean; filePath: string; filename: string; contentType: string; size: number }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/api/v1/checks/upload`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
      if (response.status === 413) {
        throw new Error('Image is too large (max 6MB). Try compressing or cropping the image.');
      }
      if (response.status === 429) {
        throw new Error('Too many uploads. Please wait a moment and try again.');
      }
      throw new Error(error.detail || `Upload failed: ${response.status}`);
    }

    return response.json();
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
      sortBy?: 'relevance' | 'date';
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

  // ============================================================================
  // API Key Management (JWT auth only — dashboard actions)
  // ============================================================================

  /**
   * POST /api/v1/api-keys
   * Create a new API key. Raw key returned once — cannot be retrieved later.
   */
  async createAPIKey(
    data: { name: string },
    token?: string | null
  ): Promise<{
    id: string;
    key: string;
    key_prefix: string;
    name: string;
    created_at: string;
  }> {
    return this.request('/api/v1/api-keys', {
      method: 'POST',
      body: JSON.stringify(data),
    }, token);
  }

  /**
   * GET /api/v1/api-keys
   * List all API keys for current user. Raw keys never returned.
   */
  async listAPIKeys(token?: string | null): Promise<{
    keys: Array<{
      id: string;
      key_prefix: string;
      name: string;
      is_active: boolean;
      last_used_at: string | null;
      usage_count: number;
      created_at: string;
    }>;
  }> {
    return this.request('/api/v1/api-keys', {}, token);
  }

  /**
   * DELETE /api/v1/api-keys/{key_id}
   * Revoke an API key. Takes effect immediately.
   */
  async revokeAPIKey(keyId: string, token?: string | null): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v1/api-keys/${keyId}`, {
      method: 'DELETE',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }
  }

  // ============================================================================
  // Email Notification Preferences
  // ============================================================================

  /**
   * GET /api/v1/users/email-preferences
   * Get user's email notification preferences
   */
  async getEmailPreferences(token?: string | null) {
    return this.request<{
      emailNotificationsEnabled: boolean;
      checkCompletion: boolean;
      checkFailure: boolean;
      weeklyDigest: boolean;
      marketing: boolean;
    }>('/api/v1/users/email-preferences', {}, token);
  }

  /**
   * PUT /api/v1/users/email-preferences
   * Update user's email notification preferences
   */
  async updateEmailPreferences(
    data: {
      email_notifications_enabled?: boolean;
      email_check_completion?: boolean;
      email_check_failure?: boolean;
      email_weekly_digest?: boolean;
      email_marketing?: boolean;
    },
    token?: string | null
  ) {
    return this.request<{
      success: boolean;
      message: string;
      preferences: {
        emailNotificationsEnabled: boolean;
        checkCompletion: boolean;
        checkFailure: boolean;
        weeklyDigest: boolean;
        marketing: boolean;
      };
    }>('/api/v1/users/email-preferences', {
      method: 'PUT',
      body: JSON.stringify(data),
    }, token);
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
