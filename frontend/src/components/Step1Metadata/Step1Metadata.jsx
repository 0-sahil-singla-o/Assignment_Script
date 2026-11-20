import React, { useState } from 'react';
import { ArrowRight, RotateCcw, Sparkles } from 'lucide-react';
import { Card, CardHeader, CardBody, CardFooter } from '../../design-system/Card/Card';
import { Input } from '../../design-system/Input/Input';
import { Button } from '../../design-system/Button/Button';
import { Badge } from '../../design-system/Badge/Badge';
import { useAssignment } from '../../hooks/useAssignmentStore';
import { useToast } from '../../design-system/Toast';
import { validateMetadata, sanitizeMetadataInput, METADATA_RULES } from '../../utils/validators';
import './Step1Metadata.css';

const PRESET_DCA7106 = {
  institution: 'Centre for Distance & Online Education, Manipal University Jaipur',
  session: 'JULY 2026',
  program: 'MASTER OF COMPUTER APPLICATIONS',
  semester: '3',
  course_code_name: 'DCA7106 - Web Technologies',
  student_info: 'Learner Submission'
};

export function Step1Metadata() {
  const { metadata, setMetadata, setCurrentStep } = useAssignment();
  const [errors, setErrors] = useState({});
  const toast = useToast();

  const handleChange = (field, rawValue) => {
    // Notify user if they attempt to enter a leading whitespace
    if (rawValue.startsWith(' ')) {
      toast.warning('Leading empty spaces are not permitted in academic fields.', 'Whitespace Filter');
    }

    const sanitized = sanitizeMetadataInput(field, rawValue);
    setMetadata((prev) => ({ ...prev, [field]: sanitized }));

    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: null }));
    }
  };

  // Keyboard interceptor: prevents typing digits in fields that disallow numbers (University, Program)
  const handleLettersOnlyKeyDown = (e) => {
    if (e.key >= '0' && e.key <= '9' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      toast.warning('Numbers are not permitted in this field (letters & punctuation only).', 'Characters Only');
    }
  };

  // Keyboard interceptor: allows ONLY digits in semester
  const handleNumbersOnlyKeyDown = (e) => {
    if (['Backspace', 'Delete', 'Tab', 'Escape', 'Enter', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
      return;
    }
    if (e.ctrlKey || e.metaKey) return;
    if (!/^[0-9]$/.test(e.key)) {
      e.preventDefault();
      toast.warning('Semester accepts numbers only (e.g. 1 to 12).', 'Numbers Only');
    }
  };

  const handleApplyPreset = () => {
    setMetadata(PRESET_DCA7106);
    setErrors({});
    toast.info('Applied Manipal DCA7106 default course preset.', 'Preset Loaded');
  };

  const handleReset = () => {
    setMetadata({
      institution: '',
      session: '',
      program: '',
      semester: '',
      course_code_name: '',
      student_info: ''
    });
    setErrors({});
    toast.info('All metadata fields cleared.');
  };

  const handleProceed = (e) => {
    e.preventDefault();
    const result = validateMetadata(metadata);

    if (!result.isValid) {
      setErrors(result.errors);
      toast.error(result.firstError || 'Please fill in all required academic metadata.', 'Validation Error');

      // Automatically focus and scroll to the first invalid field
      if (result.firstField) {
        const el = document.getElementById(result.firstField);
        if (el) {
          el.focus();
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
      return;
    }

    setErrors({});
    toast.success('Course & Student identification verified!', 'Step 1 Complete');
    setCurrentStep(2);
  };

  return (
    <div className="step1-container">
      <Card variant="elevated">
        <CardHeader>
          <div className="step-header">
            <div>
              <div className="step-badge-row">
                <Badge variant="fuchsia" size="sm">Phase 1</Badge>
                <span className="step-meta-hint">Official ReportLab Cover Block</span>
              </div>
              <h2 className="step-title type-h2">
                <span className="text-accent">Course & Student</span> Identification<span className="text-accent">.</span>
              </h2>
              <p className="step-header-desc type-body-sm">
                Provide academic credentials to compile the official institutional header block on Page 1 of the generated PDF.
              </p>
            </div>
            <div className="step-header-actions">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                icon={Sparkles}
                onClick={handleApplyPreset}
                title="Fill DCA7106 default test values"
              >
                Sample Preset
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardBody>
          <form id="metadata-form" onSubmit={handleProceed} noValidate className="metadata-form">
            <div className="form-grid">
              {/* Institution (Full Width) */}
              <div className="form-col-full">
                <Input
                  label={`University / Institution Name (${metadata.institution.length}/${METADATA_RULES.institution.maxLength})`}
                  id="institution"
                  value={metadata.institution}
                  onChange={(e) => handleChange('institution', e.target.value)}
                  onKeyDown={handleLettersOnlyKeyDown}
                  maxLength={METADATA_RULES.institution.maxLength}
                  placeholder="e.g. Centre for Distance & Online Education, Manipal University Jaipur"
                  helperText="Primary banner on cover • Max 120 chars, up to 20 words (letters and punctuation only, no numbers)."
                  error={errors.institution}
                />
              </div>

              {/* Course Code & Name */}
              <div className="form-col">
                <Input
                  label={`Course Code & Subject Title (${metadata.course_code_name.length}/${METADATA_RULES.course_code_name.maxLength})`}
                  id="course_code_name"
                  value={metadata.course_code_name}
                  onChange={(e) => handleChange('course_code_name', e.target.value)}
                  maxLength={METADATA_RULES.course_code_name.maxLength}
                  placeholder="e.g. DCA7106 - Web Technologies"
                  helperText="Max 80 chars, up to 12 words."
                  error={errors.course_code_name}
                />
              </div>

              {/* Program */}
              <div className="form-col">
                <Input
                  label={`Degree Program (${metadata.program.length}/${METADATA_RULES.program.maxLength})`}
                  id="program"
                  value={metadata.program}
                  onChange={(e) => handleChange('program', e.target.value)}
                  onKeyDown={handleLettersOnlyKeyDown}
                  maxLength={METADATA_RULES.program.maxLength}
                  placeholder="e.g. MASTER OF COMPUTER APPLICATIONS"
                  helperText="Max 80 chars, up to 10 words (letters only, no numbers)."
                  error={errors.program}
                />
              </div>

              {/* Session */}
              <div className="form-col">
                <Input
                  label={`Academic Session (${metadata.session.length}/${METADATA_RULES.session.maxLength})`}
                  id="session"
                  value={metadata.session}
                  onChange={(e) => handleChange('session', e.target.value)}
                  maxLength={METADATA_RULES.session.maxLength}
                  placeholder="e.g. JULY 2026 / JAN 2026"
                  helperText="Max 30 chars (e.g. JULY 2026)."
                  error={errors.session}
                />
              </div>

              {/* Semester */}
              <div className="form-col">
                <Input
                  label={`Semester (${metadata.semester.length}/${METADATA_RULES.semester.maxLength})`}
                  id="semester"
                  value={metadata.semester}
                  onChange={(e) => handleChange('semester', e.target.value)}
                  onKeyDown={handleNumbersOnlyKeyDown}
                  maxLength={METADATA_RULES.semester.maxLength}
                  inputMode="numeric"
                  placeholder="e.g. 3"
                  helperText="Numbers only between 1 and 12."
                  error={errors.semester}
                />
              </div>

              {/* Student Info / Roll Number */}
              <div className="form-col-full">
                <Input
                  label={`Student Info / Roll No / Candidate ID (Optional) (${metadata.student_info.length}/${METADATA_RULES.student_info.maxLength})`}
                  id="student_info"
                  value={metadata.student_info}
                  onChange={(e) => handleChange('student_info', e.target.value)}
                  maxLength={METADATA_RULES.student_info.maxLength}
                  placeholder="e.g. Reg: 211070001 • Section A • John Doe"
                  helperText="Optional identifier printed in the attribution footer or header • Max 80 chars."
                  error={errors.student_info}
                />
              </div>
            </div>
          </form>
        </CardBody>

        <CardFooter>
          <div className="step-footer-actions">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              icon={RotateCcw}
              onClick={handleReset}
            >
              Clear Fields
            </Button>
            <Button
              type="submit"
              form="metadata-form"
              variant="primary"
              size="md"
              iconRight={ArrowRight}
            >
              Proceed to Question Scanner
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
