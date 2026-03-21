/**
 * React hooks for API integration
 */

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

/**
 * Hook for fetching data from API
 */
export function useAPI<T>(
  fetcher: () => Promise<T>,
  dependencies: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, dependencies);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

/**
 * Hook for API mutations (POST, PUT, DELETE)
 */
export function useMutation<T, P = any>(
  mutator: (params: P) => Promise<T>
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const mutate = useCallback(async (params: P) => {
    try {
      setLoading(true);
      setError(null);
      const result = await mutator(params);
      setData(result);
      return result;
    } catch (err) {
      setError(err as Error);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [mutator]);

  return { data, loading, error, mutate };
}

/**
 * Hook for checking API health
 */
export function useHealthCheck() {
  return useAPI(() => api.healthCheck(), []);
}

/**
 * Hook for fetching patients
 */
export function usePatients(params?: { page?: number; limit?: number }) {
  return useAPI(
    () => api.getPatients(params),
    [params?.page, params?.limit]
  );
}

/**
 * Hook for fetching single patient
 */
export function usePatient(id: string) {
  return useAPI(() => api.getPatient(id), [id]);
}

/**
 * Hook for fetching queue
 */
export function useQueue() {
  return useAPI(() => api.getQueue(), []);
}
