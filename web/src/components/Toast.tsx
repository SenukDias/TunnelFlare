import React, { createContext, useCallback, useContext, useRef, useState } from 'react';
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  message: string;
  detail?: string;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType, detail?: string) => void;
}

const ToastContext = createContext<ToastContextValue>({ showToast: () => {} });
export const useToast = () => useContext(ToastContext);

const TOAST_ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 size={14} color="var(--state-success)" />,
  error:   <AlertCircle  size={14} color="var(--state-error)"   />,
  warning: <AlertTriangle size={14} color="var(--state-warning)" />,
  info:    <Info          size={14} color="var(--state-info)"    />,
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timerRefs = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const dismissToast = useCallback((id: string) => {
    setToasts((t) => t.filter((x) => x.id !== id));
    clearTimeout(timerRefs.current[id]);
  }, []);

  const showToast = useCallback((message: string, type: ToastType = 'info', detail?: string) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setToasts((t) => [...t.slice(-4), { id, type, message, detail }]);
    timerRefs.current[id] = setTimeout(() => dismissToast(id), 4000);
  }, [dismissToast]);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast--${toast.type}`}>
            {TOAST_ICONS[toast.type]}
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 500 }}>{toast.message}</div>
              {toast.detail && (
                <div style={{ fontSize: 11, color: 'var(--text-2)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>
                  {toast.detail}
                </div>
              )}
            </div>
            <button
              onClick={() => dismissToast(toast.id)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-3)', padding: 0, display: 'flex' }}
            >
              <X size={12} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};
