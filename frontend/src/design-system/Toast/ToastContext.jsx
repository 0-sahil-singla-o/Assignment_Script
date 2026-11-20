import React, { createContext, useContext, useState, useCallback } from 'react';
import { ToastContainer } from './ToastContainer';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(({ type = 'info', title, message, duration = 4500 }) => {
    const id = Date.now() + Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, title, message, duration }]);
    return id;
  }, []);

  const toast = {
    error: (message, title = 'Error') => showToast({ type: 'error', title, message }),
    success: (message, title = 'Success') => showToast({ type: 'success', title, message }),
    warning: (message, title = 'Warning') => showToast({ type: 'warning', title, message }),
    info: (message, title = 'Information') => showToast({ type: 'info', title, message }),
    remove: removeToast
  };

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
