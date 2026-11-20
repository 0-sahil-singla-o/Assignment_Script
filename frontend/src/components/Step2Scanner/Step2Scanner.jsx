import React, { useState } from 'react';
import {
  FileText,
  UploadCloud,
  Cpu,
  Plus,
  Trash2,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Hash
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardBody, CardFooter } from '../../design-system/Card/Card';
import { Dropzone } from '../../design-system/Dropzone/Dropzone';
import { Button } from '../../design-system/Button/Button';
import { Badge } from '../../design-system/Badge/Badge';
import { Textarea, Input } from '../../design-system/Input/Input';
import { useAssignment } from '../../hooks/useAssignmentStore';
import { useToast } from '../../design-system/Toast';
import { assignmentService } from '../../services/assignmentService';
import './Step2Scanner.css';

export function Step2Scanner() {
  const toast = useToast();
  const {
    currentStep,
    setCurrentStep,
    scannedQuestions,
    setScannedQuestions,
    questionFile,
    setQuestionFile
  } = useAssignment();

  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [questionErrors, setQuestionErrors] = useState({});
  const [rawText, setRawText] = useState('');
  const [showRawTextInput, setShowRawTextInput] = useState(false);

  const handleScan = async () => {
    // 1. Client-side input validation
    if (!questionFile && !rawText.trim()) {
      const targetField = showRawTextInput ? 'rawText' : 'file';
      const msg = showRawTextInput
        ? 'Please paste question paper text before scanning.'
        : 'Please upload a question paper PDF before scanning.';
      setFieldErrors({ [targetField]: msg });
      setScanError(msg);
      toast.warning(msg, 'Input Required');
      return;
    }

    // Heuristic client check for raw text
    if (showRawTextInput && rawText.trim().length < 15) {
      const msg = 'Input question text is too short (minimum 15 characters required).';
      setFieldErrors({ rawText: msg });
      setScanError(msg);
      toast.warning(msg, 'Invalid Question Text');
      return;
    }

    setIsScanning(true);
    setScanError(null);
    setFieldErrors({});

    try {
      const res = await assignmentService.scanQuestions(questionFile, rawText);
      const questions = res.questions || (Array.isArray(res) ? res : []);
      if (questions && questions.length > 0) {
        const normalized = questions.map((q, idx) => {
          let m = (q.marks !== undefined && q.marks !== null && String(q.marks).trim() !== '' && Number(q.marks) > 0)
            ? Number(q.marks)
            : 5;
          if (m > 50) m = 50;
          return {
            ...q,
            number: q.number || `Q${idx + 1}`,
            marks: m,
            text: q.text || ''
          };
        });
        setScannedQuestions(normalized);
        setQuestionErrors({});
        setScanError(null);
        setFieldErrors({});
        toast.success(`Successfully parsed ${normalized.length} questions from question paper!`, 'Questions Parsed');
      } else {
        const msg = res.detail || res.message || 'No valid academic questions detected in the provided input.';
        const targetField = showRawTextInput ? 'rawText' : 'file';
        setFieldErrors({ [targetField]: msg });
        setScanError(msg);
        toast.warning(msg, 'No Questions Detected');
      }
    } catch (err) {
      const msg = err.message || 'Failed to scan question paper. Please verify the document format or try again.';
      const targetField = err.field || (showRawTextInput ? 'rawText' : 'file');
      
      const newFieldErrors = err.errors && Object.keys(err.errors).length > 0 
        ? err.errors 
        : { [targetField]: msg };

      setFieldErrors(newFieldErrors);
      setScanError(msg);
      toast.error(msg, 'Question Extraction Error');
    } finally {
      setIsScanning(false);
    }
  };

  const handleToggleInputMode = () => {
    if (showRawTextInput) {
      // Switching back to PDF file upload -> reset and clean the raw text field
      setRawText('');
    } else {
      // Switching to paste text mode -> reset the selected PDF file
      setQuestionFile(null);
    }
    setShowRawTextInput((prev) => !prev);
    setScanError(null);
    setFieldErrors({});
  };

  const handleUpdateQuestion = (index, field, value) => {
    setScannedQuestions((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  };

  const handleMarksChange = (idx, value) => {
    // Only numbers allowed (digits 0-9)
    let cleanVal = value.replace(/[^0-9]/g, '');

    // Limit to max 50 marks per question
    if (cleanVal !== '' && Number(cleanVal) > 50) {
      cleanVal = '50';
    }

    handleUpdateQuestion(idx, 'marks', cleanVal === '' ? '' : Number(cleanVal));

    // Clear error for marks on this question index
    if (questionErrors[idx]?.marks) {
      setQuestionErrors((prev) => {
        const next = { ...prev };
        if (next[idx]) {
          next[idx] = { ...next[idx], marks: null };
          if (!next[idx].text) delete next[idx];
        }
        return next;
      });
    }
  };

  const handleTextChange = (idx, value) => {
    handleUpdateQuestion(idx, 'text', value);

    // Clear error for text on this question index
    if (questionErrors[idx]?.text) {
      setQuestionErrors((prev) => {
        const next = { ...prev };
        if (next[idx]) {
          next[idx] = { ...next[idx], text: null };
          if (!next[idx].marks) delete next[idx];
        }
        return next;
      });
    }
  };

  const handleRemoveQuestion = (index) => {
    setScannedQuestions((prev) => prev.filter((_, i) => i !== index));
    setQuestionErrors((prev) => {
      const next = {};
      Object.keys(prev).forEach((key) => {
        const numKey = Number(key);
        if (numKey < index) {
          next[numKey] = prev[numKey];
        } else if (numKey > index) {
          next[numKey - 1] = prev[numKey];
        }
      });
      return next;
    });
  };

  const handleAddQuestion = () => {
    const nextNum = scannedQuestions.length + 1;
    setScannedQuestions((prev) => [
      ...prev,
      {
        number: `Q${nextNum}`,
        marks: 5,
        text: '',
        sub_parts: []
      }
    ]);
  };

  const handleProceedToStep3 = () => {
    if (scannedQuestions.length === 0) {
      toast.warning('Please scan or add at least one question before proceeding.', 'Questions Required');
      return;
    }

    const newErrors = {};
    let firstErrorMsg = '';
    let firstErrorElementId = null;

    scannedQuestions.forEach((q, idx) => {
      const qErrors = {};

      // Marks validation: cannot be empty, must be > 0 and <= 50
      const marksVal = q.marks;
      if (marksVal === '' || marksVal === null || marksVal === undefined || Number(marksVal) <= 0) {
        qErrors.marks = 'Marks required (1-50)';
        if (!firstErrorMsg) {
          firstErrorMsg = `Please enter valid marks (1-50) for Question ${q.number || idx + 1}.`;
          firstErrorElementId = `marks-${idx}`;
        }
      } else if (Number(marksVal) > 50) {
        qErrors.marks = 'Max 50 marks';
        if (!firstErrorMsg) {
          firstErrorMsg = `Marks cannot exceed 50 for Question ${q.number || idx + 1}.`;
          firstErrorElementId = `marks-${idx}`;
        }
      }

      // Question prompt validation: cannot be empty
      if (!q.text || !q.text.trim()) {
        qErrors.text = 'Question text cannot be empty.';
        if (!firstErrorMsg) {
          firstErrorMsg = `Question text cannot be empty for Question ${q.number || idx + 1}.`;
          firstErrorElementId = `q-text-${idx}`;
        }
      }

      if (Object.keys(qErrors).length > 0) {
        newErrors[idx] = qErrors;
      }
    });

    if (Object.keys(newErrors).length > 0) {
      setQuestionErrors(newErrors);
      toast.error(firstErrorMsg, 'Missing Question Details');
      if (firstErrorElementId) {
        const el = document.getElementById(firstErrorElementId);
        if (el) {
          el.focus();
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
      return;
    }

    setQuestionErrors({});
    setCurrentStep(3);
  };

  const totalMarks = scannedQuestions.reduce((acc, q) => acc + (Number(q.marks) || 0), 0);

  return (
    <div className="step2-container">
      <Card variant="elevated">
        <CardHeader>
          <div className="step-header">
            <div>
              <div className="step-badge-row">
                <Badge variant="brand" size="sm">Phase 2</Badge>
              </div>
              <CardTitle>Question Paper Extraction</CardTitle>
              <p className="step-header-desc">
                Upload your university question paper. Automated extraction parses sets, questions, marks, and sub-parts with strict structural fidelity.
              </p>
            </div>
          </div>
        </CardHeader>

        <CardBody>
          {/* Upload Section */}
          <div className="scanner-upload-section">
            {!showRawTextInput ? (
              <Dropzone
                file={questionFile}
                error={fieldErrors.file}
                onFileSelect={(file) => {
                  setQuestionFile(file);
                  setFieldErrors((prev) => ({ ...prev, file: null }));
                  setScanError(null);
                }}
                onFileClear={() => {
                  setQuestionFile(null);
                  setFieldErrors((prev) => ({ ...prev, file: null }));
                  setScanError(null);
                }}
                accept={{ 'application/pdf': ['.pdf'] }}
                title="Click to upload or drag & drop"
                subtitle="Drag & drop your university question paper (PDF format)"
              />
            ) : (
              <div className="raw-text-wrapper">
                <Textarea
                  label="Paste Question Paper Text"
                  value={rawText}
                  error={fieldErrors.rawText}
                  onChange={(e) => {
                    setRawText(e.target.value);
                    if (fieldErrors.rawText || scanError) {
                      setFieldErrors((prev) => ({ ...prev, rawText: null }));
                      setScanError(null);
                    }
                  }}
                  placeholder="Paste question paper text here (e.g., Set 1: Q1. Explain A* search algorithm... 10 Marks)"
                  rows={6}
                />
              </div>
            )}

            <div className="upload-toggle-row">
              <button
                type="button"
                className="text-toggle-btn"
                onClick={handleToggleInputMode}
              >
                {showRawTextInput ? 'Switch back to PDF file upload' : 'Or paste raw question text directly'}
              </button>

              <Button
                variant="primary"
                icon={Cpu}
                loading={isScanning}
                onClick={handleScan}
                disabled={isScanning}
              >
                {isScanning ? 'Parsing Question Paper...' : 'Scan Questions Now'}
              </Button>
            </div>

            {scanError && !fieldErrors.file && !fieldErrors.rawText && (
              <div className="scanner-error-alert" role="alert">
                <AlertTriangle size={18} />
                <span>{scanError}</span>
              </div>
            )}
          </div>

          {/* Parsed Questions List */}
          {scannedQuestions.length > 0 && (
            <div className="parsed-questions-section">
              <div className="parsed-questions-header">
                <div className="parsed-summary">
                  <h3 className="parsed-title">Extracted Questions</h3>
                  <div className="summary-badges">
                    <Badge variant="brand">{scannedQuestions.length} Questions</Badge>
                    <Badge variant="neutral">{totalMarks} Total Marks</Badge>
                  </div>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  icon={Plus}
                  onClick={handleAddQuestion}
                >
                  Add Question
                </Button>
              </div>

              <div className="questions-grid">
                {scannedQuestions.map((q, idx) => (
                  <div key={idx} className="question-card">
                    <div className="question-card__header">
                      <div className="question-meta-group">
                        <Input
                          value={q.number || `Q${idx + 1}`}
                          onChange={(e) => handleUpdateQuestion(idx, 'number', e.target.value)}
                          className="question-num-input"
                          aria-label="Question identifier"
                        />
                        <div className="marks-input-wrapper">
                          <label htmlFor={`marks-${idx}`} className="marks-label">Marks:</label>
                          <div className="marks-input-box">
                            <input
                              id={`marks-${idx}`}
                              type="text"
                              inputMode="numeric"
                              pattern="[0-9]*"
                              maxLength={2}
                              value={q.marks !== undefined && q.marks !== null ? q.marks : ''}
                              placeholder="5"
                              onChange={(e) => handleMarksChange(idx, e.target.value)}
                              className={`marks-num-input ${questionErrors[idx]?.marks ? 'marks-num-input--error' : ''}`}
                              aria-invalid={!!questionErrors[idx]?.marks}
                              aria-label={`Marks for question ${q.number || idx + 1}`}
                            />
                          </div>
                          {questionErrors[idx]?.marks && (
                            <span className="marks-error-msg">{questionErrors[idx].marks}</span>
                          )}
                        </div>
                      </div>

                      <button
                        type="button"
                        className="delete-q-btn"
                        onClick={() => handleRemoveQuestion(idx)}
                        title="Remove this question"
                        aria-label="Remove question"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>

                    <div className="question-card__body">
                      <Textarea
                        id={`q-text-${idx}`}
                        value={q.text || ''}
                        error={questionErrors[idx]?.text}
                        onChange={(e) => handleTextChange(idx, e.target.value)}
                        rows={3}
                        placeholder="Question prompt..."
                      />
                    </div>
                  </div>
                ))}
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
              onClick={() => setCurrentStep(1)}
            >
              Back to Course Info
            </Button>

            <Button
              type="button"
              variant="primary"
              size="md"
              iconRight={ArrowRight}
              onClick={handleProceedToStep3}
              disabled={scannedQuestions.length === 0}
            >
              Continue to Instructions & Style ({scannedQuestions.length} Questions)
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
