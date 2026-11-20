import React from 'react';
import { BackgroundField } from './components/BackgroundField/BackgroundField';
import { Header } from './components/Header/Header';
import { Stepper } from './components/Stepper/Stepper';
import { Step1Metadata } from './components/Step1Metadata/Step1Metadata';
import { Step2Scanner } from './components/Step2Scanner/Step2Scanner';
import { Step3Guidelines } from './components/Step3Guidelines/Step3Guidelines';
import { Step4Generate } from './components/Step4Generate/Step4Generate';
import { useAssignment } from './hooks/useAssignmentStore';
import './App.css';

export function App() {
  const { currentStep } = useAssignment();

  return (
    <div className="app-layout">
      {/* BioAge Animated Background: Drifting Color-Shifting Blobs & Canvas Dust */}
      <BackgroundField />

      {/* Sticky Translucent Header with Theme Switch & Status Pills */}
      <Header />

      {/* 4-Step Interactive Workflow Stepper */}
      <Stepper />

      {/* Main Glass Workspace */}
      <main className="app-main">
        <div className="app-container">
          <div className="step-content-mount">
            {currentStep === 1 && <Step1Metadata />}
            {currentStep === 2 && <Step2Scanner />}
            {currentStep === 3 && <Step3Guidelines />}
            {currentStep === 4 && <Step4Generate />}
          </div>
        </div>
      </main>

      {/* Glass Footer */}
      <footer className="app-footer surface-overlay">
        <div className="app-container app-footer__inner">
          <p className="footer-text type-caption">
            Autonomous Academic Assignment Studio • Indigo-Violet Theme • ReportLab Publication Engine
          </p>
          <div className="footer-links">
            <span className="footer-pill">Strict 300–350w Limit</span>
            <span className="footer-pill">TrueType ReportLab</span>
            <span className="footer-pill">Fluid Tokens</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
