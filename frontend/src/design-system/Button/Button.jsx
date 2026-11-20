import React from 'react';
import './Button.css';

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  isLoading = false,
  loading = false,
  disabled = false,
  icon: Icon,
  iconRight: IconRight,
  iconPosition = 'left',
  type = 'button',
  onClick,
  className = '',
  ...props
}) {
  const isBusy = isLoading || loading;

  return (
    <button
      type={type}
      disabled={disabled || isBusy}
      onClick={onClick}
      className={`btn btn--${variant} btn--${size} ${fullWidth ? 'btn--full' : ''} ${className}`}
      {...props}
    >
      {isBusy && <span className="btn__spinner" />}
      {!isBusy && Icon && iconPosition === 'left' && (
        <Icon className="btn__icon" size={size === 'sm' ? 14 : size === 'lg' ? 18 : 16} />
      )}
      <span className="btn__text">{children}</span>
      {!isBusy && IconRight && (
        <IconRight className="btn__icon" size={size === 'sm' ? 14 : size === 'lg' ? 18 : 16} />
      )}
      {!isBusy && Icon && iconPosition === 'right' && !IconRight && (
        <Icon className="btn__icon" size={size === 'sm' ? 14 : size === 'lg' ? 18 : 16} />
      )}
    </button>
  );
}
