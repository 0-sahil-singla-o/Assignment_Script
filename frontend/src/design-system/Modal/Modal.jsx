import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import './Modal.css';

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  maxWidth = '540px'
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Use createPortal to mount directly to document.body, escaping any parent backdrop-filter or transform containing blocks!
  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal"
        style={{ maxWidth }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="modal__header">
          <h3 className="modal__title">{title}</h3>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>
        <div className="modal__body">
          {children}
        </div>
      </div>
    </div>,
    document.body
  );
}
