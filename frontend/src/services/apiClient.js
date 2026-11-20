/**
 * Base API Client Configuration
 * Handles endpoint URL and response parsing.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = options.headers || {};

  // If body is not FormData, default to application/json
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const response = await fetch(url, {
    ...options,
    headers
  });

  if (!response.ok) {
    let errorDetail = 'Network request failed';
    let fieldErrors = null;
    let errorField = null;
    try {
      const errJson = await response.json();
      if (typeof errJson.detail === 'object' && errJson.detail !== null) {
        errorDetail = errJson.detail.message || errJson.message || errorDetail;
        fieldErrors = errJson.detail.errors || null;
        errorField = errJson.detail.field || null;
      } else {
        errorDetail = errJson.detail || errJson.message || errorDetail;
        fieldErrors = errJson.errors || null;
      }
    } catch {
      errorDetail = await response.text();
    }
    const error = new Error(errorDetail || `HTTP error ${response.status}`);
    error.status = response.status;
    error.errors = fieldErrors;
    error.field = errorField || (fieldErrors ? Object.keys(fieldErrors)[0] : null);
    throw error;
  }

  return response.json();
}

export { API_BASE };
