import React from 'react';
import { Check, UserCheck, FileText, Sliders, Cpu } from 'lucide-react';
import { useAssignment } from '../../hooks/useAssignmentStore';
import './Stepper.css';

const STEPS = [
  { id: 1, title: 'Course Details', subtitle: 'Metadata & Info', icon: UserCheck },
  { id: 2, title: 'Scan Questions', subtitle: 'Document Parsing', icon: FileText },
  { id: 3, title: 'Style & Rules', subtitle: 'Layout Directives', icon: Sliders },
  { id: 4, title: 'Live Studio', subtitle: 'Compile & Export', icon: Cpu },
];

export function Stepper() {
  const { currentStep, setCurrentStep, scannedQuestions } = useAssignment();

  const canNavigateTo = (stepId) => {
    if (stepId <= currentStep) return true;
    if (stepId === 2) return true;
    if (stepId === 3 && scannedQuestions.length > 0) return true;
    if (stepId === 4 && scannedQuestions.length > 0) return true;
    return false;
  };

  return (
    <nav className="stepper-nav" aria-label="Assignment Workflow Steps">
      <div className="app-container">
        <ol className="stepper-track">
          {STEPS.map((step) => {
            const isCompleted = currentStep > step.id;
            const isActive = currentStep === step.id;
            const isClickable = canNavigateTo(step.id);
            const Icon = step.icon;

            return (
              <li
                key={step.id}
                className={`stepper-item ${isActive ? 'stepper-item--active' : ''} ${
                  isCompleted ? 'stepper-item--completed' : ''
                } ${isClickable ? 'stepper-item--clickable' : ''}`}
              >
                <button
                  type="button"
                  className="stepper-btn"
                  onClick={() => isClickable && setCurrentStep(step.id)}
                  disabled={!isClickable}
                  aria-current={isActive ? 'step' : undefined}
                >
                  <div className="stepper-indicator">
                    {isCompleted ? (
                      <Check size={14} strokeWidth={3} className="stepper-check" />
                    ) : (
                      <span className="stepper-num">{step.id}</span>
                    )}
                  </div>
                  <div className="stepper-content">
                    <span className="stepper-title">{step.title}</span>
                    <span className="stepper-subtitle">{step.subtitle}</span>
                  </div>
                </button>
              </li>
            );
          })}
        </ol>
      </div>
    </nav>
  );
}
