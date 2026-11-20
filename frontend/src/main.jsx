import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import App from './App.jsx';
import { AssignmentProvider } from './hooks/useAssignmentStore.jsx';
import { ToastProvider } from './design-system/Toast';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ToastProvider>
      <AssignmentProvider>
        <App />
      </AssignmentProvider>
    </ToastProvider>
  </StrictMode>
);
