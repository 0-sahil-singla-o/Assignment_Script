import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, AlertTriangle, Info, X } from 'lucide-react';

const ICONS = {
  error: AlertCircle,
  success: CheckCircle2,
  warning: AlertTriangle,
  info: Info
};

export function Toast({ toast, onDismiss }) {
  const { id, type = 'info', title, message, duration = 4500 } = toast;
  const [isExiting, setIsExiting] = useState(false);
  const IconComponent = ICONS[type] || Info;

  useEffect(() => {
    if (!duration || duration <= 0) return;

    const timer = setTimeout(() => {
      setIsExiting(true);
      setTimeout(() => onDismiss(id), 300);
    }, duration);

    return () => clearTimeout(timer);
  }, [id, duration, onDismiss]);

  const handleManualClose = () => {
    setIsExiting(true);
    setTimeout(() => onDismiss(id), 250);
  };

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`toast-item toast-item--${type} ${isExiting ? 'toast-item--exit' : 'toast-item--enter'}`}
    >
      <div className="toast-item__indicator" />
      <div className="toast-item__icon-wrap">
        <IconComponent size={18} className="toast-item__icon" />
      </div>
      <div className="toast-item__content">
        {title && <h5 className="toast-item__title">{title}</h5>}
        {message && <p className="toast-item__message">{message}</p>}
      </div>
      <button
        type="button"
        className="toast-item__close-btn"
        onClick={handleManualClose}
        aria-label="Close notification"
      >
        <X size={15} />
      </button>
    </div>
  );
}
