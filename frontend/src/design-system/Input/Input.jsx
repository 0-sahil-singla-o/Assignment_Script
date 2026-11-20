import React from 'react';
import { AlertCircle } from 'lucide-react';
import './Input.css';

export function Input({
  label,
  error,
  helperText,
  icon: Icon,
  className = '',
  id,
  fullWidth = true,
  ...props
}) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className={`form-field ${fullWidth ? 'form-field--full' : ''} ${error ? 'form-field--error' : ''} ${className}`}>
      {label && <label htmlFor={inputId} className="form-field__label">{label}</label>}
      <div className="form-field__control">
        {Icon && <Icon className="form-field__icon" size={16} />}
        <input
          id={inputId}
          className={`form-field__input ${Icon ? 'form-field__input--has-icon' : ''}`}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : undefined}
          {...props}
        />
      </div>
      {error && (
        <span id={`${inputId}-error`} className="form-field__message form-field__message--error">
          <AlertCircle size={13} className="form-field__error-icon" />
          <span>{error}</span>
        </span>
      )}
      {!error && helperText && <span className="form-field__message">{helperText}</span>}
    </div>
  );
}

export function Textarea({
  label,
  error,
  helperText,
  className = '',
  id,
  rows = 4,
  fullWidth = true,
  ...props
}) {
  const textareaId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className={`form-field ${fullWidth ? 'form-field--full' : ''} ${error ? 'form-field--error' : ''} ${className}`}>
      {label && <label htmlFor={textareaId} className="form-field__label">{label}</label>}
      <textarea
        id={textareaId}
        rows={rows}
        className="form-field__textarea"
        aria-invalid={!!error}
        aria-describedby={error ? `${textareaId}-error` : undefined}
        {...props}
      />
      {error && (
        <span id={`${textareaId}-error`} className="form-field__message form-field__message--error">
          <AlertCircle size={13} className="form-field__error-icon" />
          <span>{error}</span>
        </span>
      )}
      {!error && helperText && <span className="form-field__message">{helperText}</span>}
    </div>
  );
}

export function Select({
  label,
  error,
  helperText,
  options = [],
  className = '',
  id,
  fullWidth = true,
  ...props
}) {
  const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className={`form-field ${fullWidth ? 'form-field--full' : ''} ${error ? 'form-field--error' : ''} ${className}`}>
      {label && <label htmlFor={selectId} className="form-field__label">{label}</label>}
      <select
        id={selectId}
        className="form-field__select"
        aria-invalid={!!error}
        aria-describedby={error ? `${selectId}-error` : undefined}
        {...props}
      >
        {options.map((opt) => {
          const val = typeof opt === 'object' ? opt.value : opt;
          const lbl = typeof opt === 'object' ? opt.label : opt;
          return <option key={val} value={val}>{lbl}</option>;
        })}
      </select>
      {error && (
        <span id={`${selectId}-error`} className="form-field__message form-field__message--error">
          <AlertCircle size={13} className="form-field__error-icon" />
          <span>{error}</span>
        </span>
      )}
      {!error && helperText && <span className="form-field__message">{helperText}</span>}
    </div>
  );
}
