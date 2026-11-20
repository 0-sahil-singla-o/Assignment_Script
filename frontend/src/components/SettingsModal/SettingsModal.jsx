import React, { useState } from 'react';
import { Key, Eye, EyeOff, Save, CheckCircle2, AlertCircle, ExternalLink } from 'lucide-react';
import { Modal } from '../../design-system/Modal/Modal';
import { Input } from '../../design-system/Input/Input';
import { Button } from '../../design-system/Button/Button';
import { useToast } from '../../design-system/Toast';
import { assignmentService } from '../../services/assignmentService';
import './SettingsModal.css';

export function SettingsModal({ isOpen, onClose }) {
  const toast = useToast();
  const [groqKey, setGroqKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [showGroq, setShowGroq] = useState(false);
  const [showGemini, setShowGemini] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!groqKey.trim() && !geminiKey.trim()) {
      setStatusMessage({ type: 'error', text: 'Please enter at least one API key to update.' });
      return;
    }

    setLoading(true);
    setStatusMessage(null);

    try {
      const payload = {};
      if (groqKey.trim()) payload.groq_api_key = groqKey.trim();
      if (geminiKey.trim()) payload.gemini_api_key = geminiKey.trim();

      const res = await assignmentService.saveApiKeys(payload);
      if (res.status === 'success' || (res.message && res.message.toLowerCase().includes('success'))) {
        setStatusMessage({ type: 'success', text: 'API keys updated and saved to .env successfully!' });
        toast.success('AI engine API keys saved to .env', 'Credentials Updated');
        setGroqKey('');
        setGeminiKey('');
        setTimeout(() => {
          setStatusMessage(null);
          onClose();
        }, 1200);
      } else {
        const msg = res.message || 'Failed to save API keys.';
        setStatusMessage({ type: 'error', text: msg });
        toast.error(msg, 'Key Update Failed');
      }
    } catch (err) {
      const msg = err.message || 'Error saving keys to server.';
      setStatusMessage({ type: 'error', text: msg });
      toast.error(msg, 'Server Error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="API Credentials & Engine Config"
      maxWidth="540px"
    >
      <form onSubmit={handleSubmit} className="settings-form">
        <p className="settings-form__desc">
          Configure your AI engine API keys. Keys are securely stored in your local <code>.env</code> file and never sent to third-party tracking servers.
        </p>

        {statusMessage && (
          <div className={`settings-alert settings-alert--${statusMessage.type}`}>
            {statusMessage.type === 'success' ? (
              <CheckCircle2 size={18} className="settings-alert__icon" />
            ) : (
              <AlertCircle size={18} className="settings-alert__icon" />
            )}
            <span>{statusMessage.text}</span>
          </div>
        )}

        <div className="settings-field">
          <div className="settings-field__header">
            <label className="settings-label" htmlFor="groq-key-input">
              Groq Cloud API Key
            </label>
            <a
              href="https://console.groq.com/keys"
              target="_blank"
              rel="noreferrer"
              className="settings-link"
            >
              Get Free Groq Key <ExternalLink size={12} />
            </a>
          </div>
          <div className="settings-input-group">
            <Input
              id="groq-key-input"
              type={showGroq ? 'text' : 'password'}
              placeholder="gsk_..."
              value={groqKey}
              onChange={(e) => setGroqKey(e.target.value)}
              helperText="Accelerates question paper scanning via LPU (0% local GPU/CPU load)."
            />
            <button
              type="button"
              className="toggle-visibility-btn"
              onClick={() => setShowGroq(!showGroq)}
              aria-label="Toggle Groq key visibility"
            >
              {showGroq ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        <div className="settings-field">
          <div className="settings-field__header">
            <label className="settings-label" htmlFor="gemini-key-input">
              Google Gemini API Key
            </label>
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noreferrer"
              className="settings-link"
            >
              Get Gemini Key <ExternalLink size={12} />
            </a>
          </div>
          <div className="settings-input-group">
            <Input
              id="gemini-key-input"
              type={showGemini ? 'text' : 'password'}
              placeholder="AIzaSy..."
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              helperText="Powers authoritative answer generation, audit loops & layout rule extraction."
            />
            <button
              type="button"
              className="toggle-visibility-btn"
              onClick={() => setShowGemini(!showGemini)}
              aria-label="Toggle Gemini key visibility"
            >
              {showGemini ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        <div className="settings-actions">
          <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" icon={Save} loading={loading}>
            Save to .env
          </Button>
        </div>
      </form>
    </Modal>
  );
}
