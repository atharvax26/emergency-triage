/**
 * API Client for Emergency Triage System
 * Connects frontend to FastAPI backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * API Client class for making HTTP requests to the backend
 */
class APIClient {
  private baseURL: string;
  private token: string | null = null;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
    // Load token from localStorage if available
    this.token = localStorage.getItem('triage_token');
  }

  /**
   * Set authentication token
   */
  setToken(token: string) {
    this.token = token;
    localStorage.setItem('triage_token', token);
  }

  /**
   * Clear authentication token
   */
  clearToken() {
    this.token = null;
    localStorage.removeItem('triage_token');
  }

  /**
   * Make HTTP request with timeout
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeoutMs: number = 5000
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    // Always read fresh token from localStorage (set by use-auth.ts)
    const storedSession = localStorage.getItem('triage_token');
    let token: string | null = null;
    if (storedSession) {
      try {
        const parsed = JSON.parse(storedSession);
        token = parsed?.token ?? storedSession;
      } catch {
        token = storedSession;
      }
    }

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle non-OK responses
      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: response.statusText,
        }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      // Return JSON response
      return await response.json();
    } catch (error: any) {
      clearTimeout(timeoutId);
      
      if (error.name === 'AbortError') {
        console.error(`API Timeout [${endpoint}]: Request took longer than ${timeoutMs}ms`);
        throw new Error(`Request timeout - server took too long to respond`);
      }
      
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  /**
   * GET request
   */
  async get<T>(endpoint: string, timeoutMs?: number): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' }, timeoutMs);
  }

  /**
   * POST request
   */
  async post<T>(endpoint: string, data?: any, timeoutMs?: number): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }, timeoutMs);
  }

  /**
   * PUT request
   */
  async put<T>(endpoint: string, data?: any, timeoutMs?: number): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }, timeoutMs);
  }

  /**
   * PATCH request
   */
  async patch<T>(endpoint: string, data?: any, timeoutMs?: number): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }, timeoutMs);
  }

  /**
   * DELETE request
   */
  async delete<T>(endpoint: string, timeoutMs?: number): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' }, timeoutMs);
  }

  // ============================================================================
  // Authentication API
  // ============================================================================

  /**
   * Login user
   */
  async login(email: string, password: string) {
    const response = await this.post<{ access_token: string; token_type: string }>(
      '/api/v1/auth/login',
      { email, password }
    );
    this.setToken(response.access_token);
    return response;
  }

  /**
   * Logout user
   */
  async logout() {
    this.clearToken();
  }

  /**
   * Get current user
   */
  async getCurrentUser() {
    return this.get<any>('/api/v1/users/me');
  }

  // ============================================================================
  // Patients API
  // ============================================================================

  /**
   * Get all patients
   */
  async getPatients(params?: { page?: number; limit?: number }) {
    const query = new URLSearchParams();
    if (params?.page) query.append('page', params.page.toString());
    if (params?.limit) query.append('limit', params.limit.toString());
    
    const queryString = query.toString();
    return this.get<any>(`/api/v1/patients${queryString ? `?${queryString}` : ''}`);
  }

  /**
   * Get patient by ID
   */
  async getPatient(id: string) {
    return this.get<any>(`/api/v1/patients/${id}`);
  }

  /**
   * Create new patient
   */
  async createPatient(data: any) {
    return this.post<any>('/api/v1/patients', data);
  }

  /**
   * Update patient
   */
  async updatePatient(id: string, data: any) {
    return this.put<any>(`/api/v1/patients/${id}`, data);
  }

  // ============================================================================
  // Queue API
  // ============================================================================

  /**
   * Get queue
   */
  async getQueue() {
    return this.get<any>('/api/v1/queue', 8000);
  }

  /**
   * Add patient to queue after triage
   */
  async addToQueue(data: {
    patient_id: string;
    name: string;
    age: number;
    chief_complaint: string;
    severity: string;
  }) {
    return this.post<any>('/api/v1/queue', data);
  }

  /**
   * Update queue entry status
   */
  async updateQueueStatus(entryId: string, status: "waiting" | "in-progress" | "completed") {
    return this.patch<any>(`/api/v1/queue/${entryId}/status`, { status });
  }

  // ============================================================================
  // Health Check
  // ============================================================================

  /**
   * Check API health
   */
  async healthCheck() {
    return this.get<{ status: string }>('/health');
  }

  // ============================================================================
  // Audit Log API
  // ============================================================================

  async getAuditLog(limit = 200) {
    return this.get<any>(`/api/v1/audit?limit=${limit}`);
  }

  async addAuditEntry(data: {
    patient_id: string;
    patient_name: string;
    severity: string;
    action_taken: string;
    overridden?: boolean;
    override_reason?: string;
    performed_by?: string;
  }) {
    return this.post<any>('/api/v1/audit', data);
  }

  async clearAuditLog() {
    return this.delete<any>('/api/v1/audit');
  }

  async resetAllData() {
    return this.delete<any>('/api/v1/reset');
  }

  async getStats() {
    return this.get<{
      total_predictions: number;
      pruning_applied_count: number;
      avg_compression_ratio: number;
      total_tokens_original: number;
      total_tokens_compressed: number;
      total_tokens_saved: number;
      avg_tokens_saved_pct: number;
      avg_inference_time_ms: number;
      p50_latency_ms: number;
      p95_latency_ms: number;
      compression_statistics: {
        mean_reduction_pct: number;
        std_dev_pct: number;
        min_reduction_pct: number;
        max_reduction_pct: number;
        sample_size: number;
      };
      tokens_saved_by_severity: Record<string, { count: number; tokens_saved: number }>;
      per_severity_breakdown: Array<{
        severity: string;
        count: number;
        avg_original_tokens: number;
        avg_compressed_tokens: number;
        avg_tokens_saved: number;
        avg_reduction_pct: number;
      }>;
    }>('/api/v1/stats');
  }

  // ============================================================================
  // ML Predictions API
  // ============================================================================

  /**
   * Predict triage severity using AI
   */
  async predictTriage(data: {
    patient_data: {
      vitals: {
        systolic_bp: number;
        diastolic_bp: number;
        heart_rate: number;
        respiratory_rate: number;
        temperature: number;
        spo2: number;
      };
      age: number;
      symptoms?: string[];
    };
    request_id?: string;
  }) {
    return this.post<{
      raw_probability: number;
      calibrated_probability: number;
      risk_tier: string;
      decision_label: string;
      confidence: number;
      safety_override: boolean;
      override_reason?: string;
      model_version: string;
      model_id: string;
      inference_time_ms: number;
      timestamp: string;
      request_id?: string;
      cache_hit?: boolean;
      pruning?: {
        original_tokens: number;
        compressed_tokens: number;
        compression_ratio: number;
        tokens_saved: number;
        pruning_applied: boolean;
      };
      compression_stats?: {
        original_tokens: number;
        compressed_tokens: number;
        reduction_percent: number;
      };
      reasoning?: {
        severity_justification: string;
        recommended_actions: string[];
        reasoning_trace: string[];
        clinical_priority: string;
        estimated_wait_minutes: number;
        gemini_reasoning: boolean;
      };
      latency_breakdown?: {
        ml_ms: number;
        scaledown_ms: number;
        llm_ms: number;
        total_ms: number;
        scaledown_fallback: boolean;
        llm_fallback: boolean;
      };
    }>('/api/v1/ml/triage/predict', data, 15000);
  }

  /**
   * Check ML service health
   */
  async mlHealthCheck() {
    return this.get<{ status: string; ml_service: string }>('/api/v1/ml/health');
  }

  /**
   * Extract patient info from an uploaded document (RAG layer)
   */
  async extractDocument(file: File): Promise<{
    success: boolean;
    extracted: {
      name: string | null;
      age: number | null;
      gender: string | null;
      chiefComplaint: string | null;
      symptoms: string | null;
    };
    source: string;
    error?: string;
  }> {
    const formData = new FormData();
    formData.append("file", file);

    const storedSession = localStorage.getItem("triage_token");
    let token: string | null = null;
    if (storedSession) {
      try {
        const parsed = JSON.parse(storedSession);
        token = parsed?.token ?? storedSession;
      } catch {
        token = storedSession;
      }
    }

    const headers: HeadersInit = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);
    try {
      const response = await fetch(`${this.baseURL}/api/v1/extract-document`, {
        method: "POST",
        headers,
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error: any) {
      clearTimeout(timeoutId);
      throw error;
    }
  }

  /**
   * Get compression evaluation data for dashboard charts
   */
  async getEvaluation() {
    return this.get<{
      evaluated_at: string;
      total_cases: number;
      successful: number;
      failed: number;
      overall_stats: {
        total_original_tokens: number;
        total_compressed_tokens: number;
        average_reduction_percent: number;
        total_tokens_saved: number;
      };
      per_severity_stats: Record<string, {
        count: number;
        avg_original_tokens: number;
        avg_compressed_tokens: number;
        avg_reduction_percent: number;
      }>;
      latency_stats: {
        avg_ml_ms: number;
        avg_scaledown_ms: number;
        avg_llm_ms: number;
        avg_total_ms: number;
      };
      results: Array<{
        case_id: string;
        expected_severity: string;
        predicted_severity: string;
        compression_stats: {
          original_tokens: number;
          compressed_tokens: number;
          reduction_percent: number;
        };
        latency_breakdown: {
          ml_ms: number;
          scaledown_ms: number;
          llm_ms: number;
          total_ms: number;
        };
        success: boolean;
      }>;
    }>('/api/v1/evaluation', 10000);
  }
}

// Create and export singleton instance
export const api = new APIClient(API_BASE_URL);

// Export class for testing
export { APIClient };
