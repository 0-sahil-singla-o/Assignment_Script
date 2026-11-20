import React, { createContext, useContext, useState, useEffect } from 'react';
import { assignmentService } from '../services/assignmentService';

const AssignmentContext = createContext(null);

export function AssignmentProvider({ children }) {
  // Step navigation (1: Metadata, 2: Questions, 3: Instructions, 4: Generate)
  const [currentStep, setCurrentStep] = useState(1);

  // System Health & Keys
  const [health, setHealth] = useState({
    has_groq_key: false,
    has_gemini_key: false,
    groq_models: ['llama-3.3-70b-versatile']
  });

  // Step 1: Course Metadata
  const [metadata, setMetadata] = useState({
    institution: 'Centre for Distance & Online Education, Manipal University Jaipur',
    session: 'JULY 2026',
    program: 'MASTER OF COMPUTER APPLICATIONS (MCA)',
    semester: '3',
    course_code_name: 'DCA7106 - Web Technologies',
    student_info: 'Learner Submission'
  });

  // Step 2: Questions
  const [scannedQuestions, setScannedQuestions] = useState([]);
  const [questionFile, setQuestionFile] = useState(null);

  // Step 3: Instructions & Layout Specs
  const [instructionFile, setInstructionFile] = useState(null);
  const [layoutSpecs, setLayoutSpecs] = useState({
    page_size: 'LETTER',
    orientation: 'PORTRAIT',
    page_margin_inch: 1.25,
    font_family: 'Arial',
    font_size: 11,
    font_color: '#1F3864',
    line_spacing: 1.5,
    alignment: 'LEFT',
    max_pages: 10,
    max_file_size_mb: 1.0,
    allow_color_images: false,
    allow_text_highlighting: false,
    allow_shading: false,
    plain_code_blocks: true,
    table_borders: 'GRID',
    page_numbering_format: 'Page X of Y',
    page_number_position: 'BOTTOM_RIGHT',
    header_rule_line: true
  });
  const [contentGuidelines, setContentGuidelines] = useState(
    '### 1. EXACT MARK-TO-WORD COUNT RULES\n- 10-Mark Questions: Answers must strictly fall between 300 and 350 words.\n- 5-Mark Questions: Answers must strictly fall between 150 and 200 words.\n\n### 2. ACADEMIC INTEGRITY DIRECTIVE\n- Strictly no direct copying from Internet or Self-Learning Material (SLM).'
  );
  const [isInstructionsAnalyzed, setIsInstructionsAnalyzed] = useState(false);

  // Step 4: Generation Status & Streaming
  const [generationStatus, setGenerationStatus] = useState('idle'); // idle | generating | compiling | completed | error
  const [generationProgress, setGenerationProgress] = useState(0);
  const [streamedAnswers, setStreamedAnswers] = useState([]);
  const [compiledPdf, setCompiledPdf] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  // Initial Health Check
  const refreshHealth = async () => {
    try {
      const data = await assignmentService.getHealth();
      setHealth(data);
    } catch (e) {
      console.error('Failed to fetch API health:', e);
    }
  };

  useEffect(() => {
    refreshHealth();
  }, []);

  const value = {
    currentStep,
    setCurrentStep,
    health,
    refreshHealth,
    metadata,
    setMetadata,
    scannedQuestions,
    setScannedQuestions,
    questionFile,
    setQuestionFile,
    instructionFile,
    setInstructionFile,
    layoutSpecs,
    setLayoutSpecs,
    contentGuidelines,
    setContentGuidelines,
    isInstructionsAnalyzed,
    setIsInstructionsAnalyzed,
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
  };

  return (
    <AssignmentContext.Provider value={value}>
      {children}
    </AssignmentContext.Provider>
  );
}

export function useAssignment() {
  const context = useContext(AssignmentContext);
  if (!context) {
    throw new Error('useAssignment must be used within an AssignmentProvider');
  }
  return context;
}
