import React, { useState } from 'react';
import {
  Cpu,
  Download,
  Eye,
  CheckCircle2,
  AlertCircle,
  FileCheck,
  RefreshCw,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  ArrowLeft,
  Sparkles,
  Layers,
  FileText
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardBody, CardFooter } from '../../design-system/Card/Card';
import { Button } from '../../design-system/Button/Button';
import { Badge } from '../../design-system/Badge/Badge';
import { useAssignment } from '../../hooks/useAssignmentStore';
import { useToast } from '../../design-system/Toast';
import { assignmentService } from '../../services/assignmentService';
import { API_BASE } from '../../services/apiClient';
import './Step4Generate.css';

export function Step4Generate() {
  const toast = useToast();
  const {
    setCurrentStep,
    metadata,
    scannedQuestions,
    layoutSpecs,
    contentGuidelines,
    generationStatus,
    setGenerationStatus,
    generationProgress,
    setGenerationProgress,
    streamedAnswers,
    setStreamedAnswers,
    compiledPdf,
    setCompiledPdf,
    errorMessage,
    setErrorMessage
  } = useAssignment();

  const [currentMessage, setCurrentMessage] = useState('');
  const [expandedAnswers, setExpandedAnswers] = useState({});

  const toggleExpand = (idx) => {
    setExpandedAnswers((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleStartGeneration = () => {
    setGenerationStatus('generating');
    setGenerationProgress(5);
    setCurrentMessage('Initiating generation session...');
    setStreamedAnswers([]);
    setCompiledPdf(null);
    setErrorMessage('');

    const payload = {
      metadata,
      questions: scannedQuestions,
      pdf_layout_specs: layoutSpecs,
      layout_specs: layoutSpecs,
      content_writing_guidelines: contentGuidelines,
      content_guidelines: contentGuidelines
    };

    assignmentService.generateAssignmentStream(
      payload,
      (data) => {
        if (data.type === 'progress') {
          setGenerationProgress(data.progress || 10);
          setCurrentMessage(data.message || 'Processing...');
        } else if (data.type === 'question_drafted') {
          setStreamedAnswers((prev) => [...prev, data]);
          setCurrentMessage(`Drafted ${data.number} (${data.word_count} words)`);
        } else if (data.type === 'compiling') {
          setGenerationStatus('compiling');
          setGenerationProgress(data.progress || 90);
          setCurrentMessage(data.message || 'Compiling PDF with ReportLab...');
        }
      },
      (err) => {
        setGenerationStatus('error');
        setErrorMessage(err.message || 'An error occurred during generation.');
        toast.error(err.message || 'Generation failed. Please try again.', 'Generation Error');
      },
      (completedData) => {
        setGenerationStatus('completed');
        setGenerationProgress(100);
        setCurrentMessage('PDF successfully compiled and verified!');
        setCompiledPdf(completedData);
        toast.success(`PDF compiled: ${completedData.filename} (${completedData.page_count} pages, ${completedData.file_size_mb} MB)`, 'Generation Complete');
      }
    );
  };

  const getWordCountStatus = (marks, wordCount) => {
    const is10M = Number(marks) === 10;
    const is5M = Number(marks) === 5;
    const minTarget = is10M ? 300 : is5M ? 150 : 250;
    const maxTarget = is10M ? 350 : is5M ? 200 : 350;

    const inBounds = wordCount >= minTarget && wordCount <= maxTarget;
    return {
      inBounds,
      target: `${minTarget}–${maxTarget} words`,
      text: inBounds ? `In Bounds (${wordCount}w)` : `${wordCount} words`
    };
  };

  const downloadUrl = compiledPdf ? `${API_BASE}/api/download/${compiledPdf.filename}` : '#';

  return (
    <div className="step4-container">
      <Card variant="elevated">
        <CardHeader>
          <div className="step-header">
            <div>
              <div className="step-badge-row">
                <Badge variant="brand" size="sm">Phase 4</Badge>
                {generationStatus === 'completed' ? (
                  <Badge variant="success" size="sm" dot>PDF Ready for Download</Badge>
                ) : generationStatus === 'generating' || generationStatus === 'compiling' ? (
                  <Badge variant="warning" size="sm" dot>Generation in Progress</Badge>
                ) : (
                  <Badge variant="neutral" size="sm">Studio Ready</Badge>
                )}
              </div>
              <CardTitle>Live Generation Studio & ReportLab Engine</CardTitle>
              <p className="step-header-desc">
                Execute streaming answer drafting, automated bidirectional word-count audit loops, and physical ReportLab PDF compilation.
              </p>
            </div>

            <div className="step-header-actions">
              {generationStatus === 'idle' || generationStatus === 'completed' || generationStatus === 'error' ? (
                <Button
                  variant="primary"
                  icon={Sparkles}
                  size="md"
                  onClick={handleStartGeneration}
                  disabled={scannedQuestions.length === 0}
                >
                  {generationStatus === 'completed' ? 'Re-generate Assignment' : 'Start Full Generation'}
                </Button>
              ) : null}
            </div>
          </div>
        </CardHeader>

        <CardBody>
          {/* Progress / Status Bar */}
          {(generationStatus === 'generating' || generationStatus === 'compiling') && (
            <div className="generation-progress-box">
              <div className="progress-top-row">
                <div className="progress-status-indicator">
                  <span className="spinner-dot" />
                  <span className="progress-message">{currentMessage}</span>
                </div>
                <span className="progress-pct">{generationProgress}%</span>
              </div>
              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{ width: `${generationProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Error Banner */}
          {generationStatus === 'error' && (
            <div className="generation-error-banner">
              <AlertCircle size={20} className="error-icon" />
              <div>
                <h4 className="error-title">Generation Error</h4>
                <p className="error-desc">{errorMessage}</p>
              </div>
            </div>
          )}

          {/* Success Banner & PDF Viewer */}
          {generationStatus === 'completed' && compiledPdf && (
            <div className="pdf-success-section">
              <div className="success-banner">
                <div className="success-banner__left">
                  <div className="success-icon-badge">
                    <CheckCircle2 size={24} />
                  </div>
                  <div>
                    <h3 className="success-title">Assignment Generated & Verified Successfully!</h3>
                    <div className="pdf-metrics-row">
                      <span className="pdf-metric">
                        <strong>Filename:</strong> {compiledPdf.filename}
                      </span>
                      <span className="pdf-metric">
                        <strong>Pages:</strong> {compiledPdf.page_count} / {layoutSpecs.max_pages || 10}
                      </span>
                      <span className="pdf-metric">
                        <strong>File Size:</strong> {compiledPdf.file_size_mb} MB (Target: &lt; 1.0 MB)
                      </span>
                    </div>
                  </div>
                </div>

                <div className="success-banner__right">
                  <a
                    href={downloadUrl}
                    download={compiledPdf.filename}
                    className="download-btn-link"
                  >
                    <Button variant="primary" icon={Download} size="md">
                      Download PDF
                    </Button>
                  </a>
                </div>
              </div>

              {/* PDF Preview Frame */}
              <div className="pdf-preview-container">
                <div className="pdf-preview-header">
                  <span className="preview-label">Live PDF Preview</span>
                  <a
                    href={downloadUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="open-tab-link"
                  >
                    Open in new tab <ExternalLink size={12} />
                  </a>
                </div>
                <iframe
                  src={downloadUrl}
                  title="PDF Preview"
                  className="pdf-iframe"
                />
              </div>
            </div>
          )}

          {/* Streamed Answers & Audit Log */}
          {streamedAnswers.length > 0 && (
            <div className="streamed-answers-section">
              <h3 className="section-title">
                Audited Question Answers ({streamedAnswers.length} of {scannedQuestions.length})
              </h3>

              <div className="answers-list">
                {streamedAnswers.map((ans, idx) => {
                  const isExpanded = !!expandedAnswers[idx];
                  const { inBounds, target, text } = getWordCountStatus(ans.marks, ans.word_count);

                  return (
                    <div key={idx} className="answer-audit-card">
                      <div className="answer-audit-card__header" onClick={() => toggleExpand(idx)}>
                        <div className="header-left">
                          <span className="q-badge">{ans.number}</span>
                          <span className="q-marks-label">{ans.marks} Marks</span>
                          <Badge
                            variant={inBounds ? 'success' : 'warning'}
                            size="sm"
                            dot={inBounds}
                          >
                            {text} (Target: {target})
                          </Badge>
                        </div>

                        <div className="header-right">
                          <button
                            type="button"
                            className="expand-btn"
                            aria-label={isExpanded ? 'Collapse answer' : 'Expand answer'}
                          >
                            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                          </button>
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="answer-audit-card__body">
                          <pre className="answer-markdown-text">{ans.content}</pre>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Idle Placeholder */}
          {generationStatus === 'idle' && streamedAnswers.length === 0 && (
            <div className="idle-placeholder">
              <div className="idle-icon-wrap">
                <Sparkles size={36} />
              </div>
              <h3 className="idle-title">Ready to Generate</h3>
              <p className="idle-desc">
                Review your course metadata, questions, and styling guidelines above. When you are ready, click "Start Full Generation" to begin live streaming.
              </p>
              <div className="generation-preflight-checklist">
                <div className="checklist-item">
                  <CheckCircle2 size={16} className="checklist-icon" />
                  <span>{scannedQuestions.length} Questions prepared</span>
                </div>
                <div className="checklist-item">
                  <CheckCircle2 size={16} className="checklist-icon" />
                  <span>Font: {layoutSpecs.font_family} ({layoutSpecs.font_size}pt) in {layoutSpecs.font_color}</span>
                </div>
                <div className="checklist-item">
                  <CheckCircle2 size={16} className="checklist-icon" />
                  <span>Margins: {layoutSpecs.page_margin_inch}" • Spacing: {layoutSpecs.line_spacing}x</span>
                </div>
                <div className="checklist-item">
                  <CheckCircle2 size={16} className="checklist-icon" />
                  <span>Enforcing strict limits: 300–350w (10M) & 150–200w (5M)</span>
                </div>
              </div>
            </div>
          )}
        </CardBody>

        <CardFooter>
          <div className="step-footer-actions">
            <Button
              type="button"
              variant="outline"
              size="md"
              icon={ArrowLeft}
              onClick={() => setCurrentStep(3)}
              disabled={generationStatus === 'generating' || generationStatus === 'compiling'}
            >
              Back to Guidelines
            </Button>

            {generationStatus === 'completed' && (
              <a href={downloadUrl} download={compiledPdf?.filename} className="download-btn-link">
                <Button variant="primary" icon={Download} size="md">
                  Download Verified PDF
                </Button>
              </a>
            )}
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
