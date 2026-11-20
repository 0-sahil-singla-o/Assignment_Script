import React, { useState } from 'react';
import {
  Sliders,
  Sparkles,
  FileCheck,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Layout,
  Type,
  Maximize2,
  Palette,
  FileCode,
  ShieldCheck,
  Info
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardBody, CardFooter } from '../../design-system/Card/Card';
import { Dropzone } from '../../design-system/Dropzone/Dropzone';
import { Button } from '../../design-system/Button/Button';
import { Badge } from '../../design-system/Badge/Badge';
import { Input, Select, Textarea } from '../../design-system/Input/Input';
import { useAssignment } from '../../hooks/useAssignmentStore';
import { useToast } from '../../design-system/Toast';
import { assignmentService } from '../../services/assignmentService';
import './Step3Guidelines.css';

export function Step3Guidelines() {
  const toast = useToast();
  const {
    currentStep,
    setCurrentStep,
    instructionFile,
    setInstructionFile,
    layoutSpecs,
    setLayoutSpecs,
    contentGuidelines,
    setContentGuidelines,
    isInstructionsAnalyzed,
    setIsInstructionsAnalyzed
  } = useAssignment();

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);
  const [rawText, setRawText] = useState('');
  const [showRawTextInput, setShowRawTextInput] = useState(false);

  const handleAnalyze = async () => {
    if (!instructionFile && !rawText.trim()) {
      setAnalysisError('Please upload an Instructions PDF or paste the instruction text.');
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);

    try {
      const res = await assignmentService.analyzeInstructions(instructionFile, rawText);
      const specs = res.pdf_layout_specs || res.layout_specs;
      const guidelines = res.content_writing_guidelines || res.content_guidelines;

      if (res.status === 'success' || specs || guidelines) {
        if (specs) {
          setLayoutSpecs(specs);
        }
        if (guidelines) {
          setContentGuidelines(guidelines);
        }
        setIsInstructionsAnalyzed(true);
        setAnalysisError(null);
        toast.success('Extracted physical layout parameters & academic content directives!', 'Instructions Analyzed');
      } else {
        const msg = res.message || res.detail || 'Instruction parsing failed.';
        setAnalysisError(msg);
        toast.warning(msg, 'Instructions Warning');
      }
    } catch (err) {
      const msg = err.message || 'Failed to analyze instructions. Please verify the file and try again.';
      setAnalysisError(msg);
      toast.error(msg, 'Analysis Error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleUpdateLayoutSpec = (key, value) => {
    setLayoutSpecs((prev) => ({
      ...prev,
      [key]: value
    }));
  };

  return (
    <div className="step3-container">
      <Card variant="elevated">
        <CardHeader>
          <div className="step-header">
            <div>
              <div className="step-badge-row">
                <Badge variant="brand" size="sm">Phase 3</Badge>
                {isInstructionsAnalyzed ? (
                  <Badge variant="success" size="sm" dot>Specifications Extracted</Badge>
                ) : (
                  <Badge variant="neutral" size="sm">Default Rules Loaded</Badge>
                )}
              </div>
              <CardTitle>Physical Layout & AI Directives</CardTitle>
              <p className="step-header-desc">
                Upload your university instructions PDF. Our dual-extractor cleanly decouples physical PDF layout parameters from academic content writing rules.
              </p>
            </div>
          </div>
        </CardHeader>

        <CardBody>
          {/* Upload Section */}
          <div className="guidelines-upload-section">
            {!showRawTextInput ? (
              <Dropzone
                file={instructionFile}
                onFileSelect={(file) => {
                  setInstructionFile(file);
                  setAnalysisError(null);
                }}
                onClear={() => setInstructionFile(null)}
                accept={{ 'application/pdf': ['.pdf'] }}
                label="Upload University Guidelines / Instructions PDF"
                description="Drag & drop the assignment instruction sheet (PDF format)"
              />
            ) : (
              <div className="raw-text-wrapper">
                <Textarea
                  label="Paste Instruction Text Directly"
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="Paste guidelines text here (e.g., Margins 1.25 inches, Font Arial 11pt, Dark Blue #1F3864...)"
                  rows={6}
                />
              </div>
            )}

            <div className="upload-toggle-row">
              <button
                type="button"
                className="text-toggle-btn"
                onClick={() => setShowRawTextInput(!showRawTextInput)}
              >
                {showRawTextInput ? 'Switch back to PDF file upload' : 'Or paste raw instruction text directly'}
              </button>

              <Button
                variant="primary"
                icon={Sparkles}
                loading={isAnalyzing}
                onClick={handleAnalyze}
                disabled={isAnalyzing || (!instructionFile && !rawText.trim())}
              >
                {isAnalyzing ? 'Extracting Specifications...' : 'Analyze Instructions PDF'}
              </Button>
            </div>

            {analysisError && (
              <div className="guidelines-error-alert">
                <AlertTriangle size={18} />
                <span>{analysisError}</span>
              </div>
            )}
          </div>

          {/* Dual Component Inspector */}
          <div className="dual-inspector-grid">
            {/* Component 1: Physical Layout Specs */}
            <div className="inspector-panel">
              <div className="inspector-panel__header">
                <div className="panel-title-group">
                  <Layout size={18} className="panel-icon" />
                  <h3 className="panel-title">Component 1: Physical PDF Layout Specs</h3>
                </div>
                <Badge variant="brand" size="sm">ReportLab Compiler</Badge>
              </div>

              <div className="specs-grid">
                <div className="spec-item">
                  <Select
                    label="Page Size"
                    value={layoutSpecs.page_size || 'LETTER'}
                    onChange={(e) => handleUpdateLayoutSpec('page_size', e.target.value)}
                    options={[
                      { value: 'LETTER', label: 'US Letter (8.5 × 11 in)' },
                      { value: 'A4', label: 'A4 (210 × 297 mm)' },
                      { value: 'LEGAL', label: 'Legal (8.5 × 14 in)' }
                    ]}
                  />
                </div>

                <div className="spec-item">
                  <Select
                    label="Page Margin"
                    value={String(layoutSpecs.page_margin_inch || 1.25)}
                    onChange={(e) => handleUpdateLayoutSpec('page_margin_inch', parseFloat(e.target.value))}
                    options={[
                      { value: '1.25', label: '1.25 Inches (University Standard)' },
                      { value: '1.0', label: '1.0 Inch (Standard)' },
                      { value: '0.75', label: '0.75 Inch (Compact)' }
                    ]}
                  />
                </div>

                <div className="spec-item">
                  <Select
                    label="Font Family"
                    value={layoutSpecs.font_family || 'Arial'}
                    onChange={(e) => handleUpdateLayoutSpec('font_family', e.target.value)}
                    options={[
                      { value: 'Arial', label: 'Arial (TrueType)' },
                      { value: 'Helvetica', label: 'Helvetica' },
                      { value: 'Times-Roman', label: 'Times New Roman' },
                      { value: 'Calibri', label: 'Calibri' }
                    ]}
                  />
                </div>

                <div className="spec-item">
                  <Input
                    label="Font Size (pt)"
                    type="number"
                    value={layoutSpecs.font_size || 11}
                    onChange={(e) => handleUpdateLayoutSpec('font_size', parseInt(e.target.value, 10))}
                  />
                </div>

                <div className="spec-item">
                  <div className="color-spec-field">
                    <label className="input-label">Font Color</label>
                    <div className="color-spec-row">
                      <input
                        type="color"
                        value={layoutSpecs.font_color || '#1F3864'}
                        onChange={(e) => handleUpdateLayoutSpec('font_color', e.target.value)}
                        className="color-picker-swatch"
                        title="Pick body font color"
                      />
                      <Input
                        value={layoutSpecs.font_color || '#1F3864'}
                        onChange={(e) => handleUpdateLayoutSpec('font_color', e.target.value)}
                        placeholder="#1F3864"
                      />
                    </div>
                  </div>
                </div>

                <div className="spec-item">
                  <Select
                    label="Line Spacing"
                    value={String(layoutSpecs.line_spacing || 1.5)}
                    onChange={(e) => handleUpdateLayoutSpec('line_spacing', parseFloat(e.target.value))}
                    options={[
                      { value: '1.5', label: '1.5 Lines (16.5 pt leading)' },
                      { value: '1.15', label: '1.15 Lines' },
                      { value: '1.0', label: '1.0 Single Spacing' },
                      { value: '2.0', label: '2.0 Double Spacing' }
                    ]}
                  />
                </div>

                <div className="spec-item">
                  <Select
                    label="Text Alignment"
                    value={layoutSpecs.alignment || 'LEFT'}
                    onChange={(e) => handleUpdateLayoutSpec('alignment', e.target.value)}
                    options={[
                      { value: 'LEFT', label: 'Left Aligned' },
                      { value: 'JUSTIFIED', label: 'Justified' },
                      { value: 'CENTER', label: 'Centered' }
                    ]}
                  />
                </div>

                <div className="spec-item">
                  <Input
                    label="Max Pages Limit"
                    type="number"
                    value={layoutSpecs.max_pages || 10}
                    onChange={(e) => handleUpdateLayoutSpec('max_pages', parseInt(e.target.value, 10))}
                  />
                </div>
              </div>

              {/* Toggles */}
              <div className="specs-toggles">
                <label className="checkbox-toggle">
                  <input
                    type="checkbox"
                    checked={!layoutSpecs.allow_color_images}
                    onChange={(e) => handleUpdateLayoutSpec('allow_color_images', !e.target.checked)}
                  />
                  <span>Disallow color images (strictly monochrome/clean)</span>
                </label>
                <label className="checkbox-toggle">
                  <input
                    type="checkbox"
                    checked={!layoutSpecs.allow_text_highlighting}
                    onChange={(e) => handleUpdateLayoutSpec('allow_text_highlighting', !e.target.checked)}
                  />
                  <span>Disallow text highlighting / background tinting</span>
                </label>
                <label className="checkbox-toggle">
                  <input
                    type="checkbox"
                    checked={layoutSpecs.plain_code_blocks}
                    onChange={(e) => handleUpdateLayoutSpec('plain_code_blocks', e.target.checked)}
                  />
                  <span>Unshaded plain textbook code blocks</span>
                </label>
              </div>
            </div>

            {/* Component 2: Content Writing Directives */}
            <div className="inspector-panel">
              <div className="inspector-panel__header">
                <div className="panel-title-group">
                  <ShieldCheck size={18} className="panel-icon panel-icon--shield" />
                  <h3 className="panel-title">Component 2: Academic Content Directives</h3>
                </div>
                <Badge variant="success" size="sm">Writing Directives</Badge>
              </div>

              <div className="guidelines-textarea-wrap">
                <Textarea
                  label="Structured Academic Writing & Formatting Directives"
                  value={contentGuidelines}
                  onChange={(e) => setContentGuidelines(e.target.value)}
                  rows={13}
                  helperText="These directives govern word counts, anti-plagiarism phrasing, and academic depth."
                />
              </div>

              <div className="directive-audit-hint">
                <Info size={16} />
                <span>
                  Our engine automatically enforces a dual expansion & condensation audit loop to strictly guarantee responses remain within 300–350 words (10M) and 150–200 words (5M).
                </span>
              </div>
            </div>
          </div>
        </CardBody>

        <CardFooter>
          <div className="step-footer-actions">
            <Button
              type="button"
              variant="outline"
              size="md"
              icon={ArrowLeft}
              onClick={() => setCurrentStep(2)}
            >
              Back to Questions
            </Button>

            <Button
              type="button"
              variant="primary"
              size="md"
              iconRight={ArrowRight}
              onClick={() => setCurrentStep(4)}
            >
              Proceed to Live Generation Studio
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
