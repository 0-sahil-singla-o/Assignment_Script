import React from 'react';
import './Card.css';

export function Card({
  children,
  variant = 'default',
  className = '',
  onClick,
  ...props
}) {
  return (
    <div
      className={`card card--${variant} ${onClick ? 'card--clickable' : ''} ${className}`}
      onClick={onClick}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '', ...props }) {
  return (
    <div className={`card__header ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ children, subtitle, className = '', ...props }) {
  return (
    <div className={`card__title-group ${className}`} {...props}>
      <h3 className="card__title">{children}</h3>
      {subtitle && <p className="card__subtitle">{subtitle}</p>}
    </div>
  );
}

export function CardBody({ children, className = '', ...props }) {
  return (
    <div className={`card__body ${className}`} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ children, className = '', ...props }) {
  return (
    <div className={`card__footer ${className}`} {...props}>
      {children}
    </div>
  );
}
