/**
 * Connection Status Component
 * Shows if the backend API is connected
 */

import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';

export function ConnectionStatus() {
  const [status, setStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');

  useEffect(() => {
    const checkConnection = async () => {
      try {
        await api.healthCheck();
        setStatus('connected');
      } catch (error) {
        console.error('Health check failed:', error);
        setStatus('disconnected');
      }
    };

    // Check immediately
    checkConnection();

    // Check every 10 seconds (faster than 30)
    const interval = setInterval(checkConnection, 10000);

    return () => clearInterval(interval);
  }, []);

  if (status === 'checking') {
    return (
      <Badge variant="outline" className="text-xs">
        <span className="mr-1">⏳</span> Checking...
      </Badge>
    );
  }

  if (status === 'connected') {
    return (
      <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
        <span className="mr-1">✓</span> Connected
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className="text-xs bg-red-50 text-red-700 border-red-200">
      <span className="mr-1">✗</span> Disconnected
    </Badge>
  );
}
