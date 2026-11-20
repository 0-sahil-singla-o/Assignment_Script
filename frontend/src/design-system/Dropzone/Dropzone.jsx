import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, X, AlertCircle } from 'lucide-react';
import './Dropzone.css';

export function Dropzone({
  file,
  onFileSelect,
  onFileClear,
  accept = '.pdf,.docx,.txt',
  title = 'Click to upload or drag & drop',
  subtitle = 'PDF, Word (.docx), or Text (.txt) files',
  disabled = false,
  error = null,
  className = ''
}) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelect(e.target.files[0]);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 KB';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(2)} MB`;
  };

  return (
    <div className={`dropzone-container ${className}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept={accept}
        style={{ display: 'none' }}
        onChange={handleChange}
        disabled={disabled}
      />

      {!file ? (
        <div
          className={`dropzone ${isDragOver ? 'dropzone--active' : ''} ${disabled ? 'dropzone--disabled' : ''} ${error ? 'dropzone--error' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !disabled && fileInputRef.current?.click()}
          role="button"
          tabIndex={disabled ? -1 : 0}
          aria-invalid={!!error}
        >
          <div className="dropzone__icon-wrapper">
            <UploadCloud size={28} className="dropzone__icon" />
          </div>
          <div className="dropzone__content">
            <p className="dropzone__title">{title}</p>
            <p className="dropzone__subtitle">{subtitle}</p>
          </div>
        </div>
      ) : (
        <div className={`dropzone-file ${error ? 'dropzone-file--error' : ''}`}>
          <div className="dropzone-file__info">
            <div className="dropzone-file__icon-badge">
              <FileText size={20} />
            </div>
            <div className="dropzone-file__meta">
              <p className="dropzone-file__name">{file.name}</p>
              <p className="dropzone-file__size">{formatFileSize(file.size)}</p>
            </div>
          </div>
          <button
            type="button"
            className="dropzone-file__clear"
            onClick={(e) => {
              e.stopPropagation();
              if (fileInputRef.current) fileInputRef.current.value = '';
              onFileClear();
            }}
            title="Remove file"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {error && (
        <span className="dropzone-error-message" role="alert">
          <AlertCircle size={13} className="dropzone-error-icon" />
          <span>{error}</span>
        </span>
      )}
    </div>
  );
}
