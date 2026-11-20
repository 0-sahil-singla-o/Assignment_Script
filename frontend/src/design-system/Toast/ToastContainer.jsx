import React from 'react';
import { createPortal } from 'react-dom';
import { Toast } from './Toast';
import './Toast.css';

export function ToastContainer({ toasts, onDismiss }) {
  if (typeof document === 'undefined') return null;

  return createPortal(
    <div className="toast-container" aria-label="Notifications">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>,
    document.body
  );
}
