/**
 * Shared Academic Metadata Validator & Sanitizer for Frontend
 * Mirroring the shared rules defined in shared/validation/metadataRules.json
 */

export const METADATA_RULES = {
  institution: {
    required: true,
    minLength: 3,
    maxLength: 120,
    maxWords: 20,
    disallowNumbers: true,
    label: 'University / Institution Name',
    errorMessages: {
      required: 'University / Institution Name is required.',
      noLeadingSpace: 'Institution Name cannot start with empty spaces.',
      minLength: 'Institution Name must be at least 3 characters.',
      maxLength: 'Institution Name cannot exceed 120 characters.',
      maxWords: 'Institution Name cannot exceed 20 words.',
      disallowNumbers: 'University Name cannot contain numbers (letters and punctuation only).'
    }
  },
  course_code_name: {
    required: true,
    minLength: 3,
    maxLength: 80,
    maxWords: 12,
    label: 'Course Code & Subject Title',
    errorMessages: {
      required: 'Course Code & Subject Title is required (e.g. DCA7106 - Web Technologies).',
      noLeadingSpace: 'Course Code cannot start with empty spaces.',
      minLength: 'Course Code & Title must be at least 3 characters.',
      maxLength: 'Course Code & Title cannot exceed 80 characters.',
      maxWords: 'Course Code & Title cannot exceed 12 words.'
    }
  },
  program: {
    required: true,
    minLength: 2,
    maxLength: 80,
    maxWords: 10,
    disallowNumbers: true,
    label: 'Degree Program',
    errorMessages: {
      required: 'Degree Program is required (e.g. MASTER OF COMPUTER APPLICATIONS).',
      noLeadingSpace: 'Degree Program cannot start with empty spaces.',
      minLength: 'Degree Program must be at least 2 characters.',
      maxLength: 'Degree Program cannot exceed 80 characters.',
      maxWords: 'Degree Program cannot exceed 10 words.',
      disallowNumbers: 'Degree Program cannot contain numbers (e.g. use MCA, BCA, M.Sc).'
    }
  },
  session: {
    required: true,
    minLength: 3,
    maxLength: 30,
    label: 'Academic Session',
    errorMessages: {
      required: 'Academic Session is required (e.g. JULY 2026).',
      noLeadingSpace: 'Academic Session cannot start with empty spaces.',
      minLength: 'Academic Session must be at least 3 characters.',
      maxLength: 'Academic Session cannot exceed 30 characters.'
    }
  },
  semester: {
    required: true,
    onlyNumbers: true,
    minValue: 1,
    maxValue: 12,
    maxLength: 2,
    label: 'Semester',
    errorMessages: {
      required: 'Semester is required.',
      noLeadingSpace: 'Semester cannot start with empty spaces.',
      onlyNumbers: 'Semester must be numbers only (e.g. 1 to 12).',
      range: 'Semester must be a valid number between 1 and 12.',
      maxLength: 'Semester cannot exceed 2 digits.'
    }
  },
  student_info: {
    required: false,
    maxLength: 80,
    label: 'Student Info / Candidate ID',
    errorMessages: {
      noLeadingSpace: 'Student Info cannot start with empty spaces.',
      maxLength: 'Student Info cannot exceed 80 characters.'
    }
  }
};

/**
 * Live sanitizes input on every keystroke:
 * - Prevents leading spaces
 * - Disallows numbers where prohibited
 * - Enforces digits-only for semester
 * - Enforces character length caps
 */
export function sanitizeMetadataInput(field, rawValue) {
  if (rawValue == null) return '';
  let val = String(rawValue);

  // 1. Disallow leading whitespace
  val = val.replace(/^\s+/, '');

  // 2. Field-specific sanitizations
  if (field === 'institution' || field === 'program') {
    // Cannot enter numbers into university name or degree program
    val = val.replace(/[0-9]/g, '');
  } else if (field === 'semester') {
    // Semester must be ONLY numbers
    val = val.replace(/[^0-9]/g, '');
    if (val.length > 2) {
      val = val.slice(0, 2);
    }
  }

  // 3. Length caps
  const rules = METADATA_RULES[field];
  if (rules && rules.maxLength && val.length > rules.maxLength) {
    val = val.slice(0, rules.maxLength);
  }

  return val;
}

/**
 * Validates metadata object against shared rules.
 * @param {Object} metadata
 * @returns {{ isValid: boolean, errors: Object, firstError: string|null, firstField: string|null }}
 */
export function validateMetadata(metadata = {}) {
  const errors = {};
  let firstError = null;
  let firstField = null;

  for (const [field, rules] of Object.entries(METADATA_RULES)) {
    const rawVal = metadata[field];
    const rawStr = rawVal != null ? String(rawVal) : '';

    // Check for leading whitespace if somehow present
    if (/^\s+/.test(rawStr)) {
      const msg = rules.errorMessages?.noLeadingSpace || `${rules.label} cannot start with empty spaces.`;
      errors[field] = msg;
      if (!firstError) {
        firstError = msg;
        firstField = field;
      }
      continue;
    }

    const val = rawStr.trim();

    // 1. Required check
    if (rules.required && (!val || val.length === 0)) {
      const msg = rules.errorMessages?.required || `${rules.label} is required.`;
      errors[field] = msg;
      if (!firstError) {
        firstError = msg;
        firstField = field;
      }
      continue;
    }

    // If empty and optional, skip further checks
    if (!val && !rules.required) {
      continue;
    }

    // 2. Disallow numbers check (for University name & Degree program)
    if (rules.disallowNumbers && /[0-9]/.test(val)) {
      const msg = rules.errorMessages?.disallowNumbers || `${rules.label} cannot contain numbers.`;
      errors[field] = msg;
      if (!firstError) {
        firstError = msg;
        firstField = field;
      }
      continue;
    }

    // 3. Digits-only check (for Semester)
    if (rules.onlyNumbers && !/^\d+$/.test(val)) {
      const msg = rules.errorMessages?.onlyNumbers || `${rules.label} must be numbers only.`;
      errors[field] = msg;
      if (!firstError) {
        firstError = msg;
        firstField = field;
      }
      continue;
    }

    // 4. Numerical range check (for Semester: 1 to 12)
    if (rules.minValue !== undefined || rules.maxValue !== undefined) {
      const numVal = parseInt(val, 10);
      if (isNaN(numVal) || (rules.minValue !== undefined && numVal < rules.minValue) || (rules.maxValue !== undefined && numVal > rules.maxValue)) {
        const msg = rules.errorMessages?.range || `${rules.label} must be between ${rules.minValue} and ${rules.maxValue}.`;
        errors[field] = msg;
        if (!firstError) {
          firstError = msg;
          firstField = field;
        }
        continue;
      }
    }

    // 5. Minimum length check
    if (rules.minLength && val.length < rules.minLength) {
      const msg = rules.errorMessages?.minLength || `${rules.label} must be at least ${rules.minLength} characters.`;
      errors[field] = msg;
      if (!firstError) {
        firstError = msg;
        firstField = field;
      }
      continue;
    }

    // 6. Maximum length check
    if (rules.maxLength && val.length > rules.maxLength) {
      const msg = rules.errorMessages?.maxLength || `${rules.label} cannot exceed ${rules.maxLength} characters.`;
      errors[field] = msg;
      if (!firstError) {
        firstError = msg;
        firstField = field;
      }
      continue;
    }

    // 7. Word count limit check
    if (rules.maxWords) {
      const words = val.split(/\s+/).filter(Boolean);
      if (words.length > rules.maxWords) {
        const msg = rules.errorMessages?.maxWords || `${rules.label} cannot exceed ${rules.maxWords} words.`;
        errors[field] = msg;
        if (!firstError) {
          firstError = msg;
          firstField = field;
        }
        continue;
      }
    }
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
    firstError,
    firstField
  };
}
