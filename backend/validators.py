"""
Backend Academic Metadata Validator.
Implements the shared validation rules defined in shared/validation/metadataRules.json.
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, Tuple

SHARED_RULES_PATH = Path(__file__).resolve().parent.parent / "shared" / "validation" / "metadataRules.json"

def load_metadata_rules() -> Dict[str, Any]:
    if SHARED_RULES_PATH.exists():
        try:
            with open(SHARED_RULES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback identical specification
    return {
        "institution": {"required": True, "minLength": 3, "maxLength": 120, "maxWords": 20, "disallowNumbers": True, "label": "University / Institution Name"},
        "course_code_name": {"required": True, "minLength": 3, "maxLength": 80, "maxWords": 12, "label": "Course Code & Subject Title"},
        "program": {"required": True, "minLength": 2, "maxLength": 80, "maxWords": 10, "disallowNumbers": True, "label": "Degree Program"},
        "session": {"required": True, "minLength": 3, "maxLength": 30, "label": "Academic Session"},
        "semester": {"required": True, "onlyNumbers": True, "minValue": 1, "maxValue": 12, "maxLength": 2, "label": "Semester"},
        "student_info": {"required": False, "maxLength": 80, "label": "Student Info / Candidate ID"}
    }

METADATA_RULES = load_metadata_rules()

def validate_metadata(metadata: Dict[str, Any]) -> Tuple[bool, Dict[str, str], str]:
    """
    Validates academic metadata.
    Returns:
        (is_valid, errors_dict, first_error_message)
    """
    errors = {}
    first_error = ""

    for field, rules in METADATA_RULES.items():
        raw_val = metadata.get(field)
        raw_str = str(raw_val) if raw_val is not None else ""
        label = rules.get("label", field)
        error_msgs = rules.get("errorMessages", {})

        # 1. Leading whitespace check
        if re.search(r"^\s+", raw_str):
            msg = error_msgs.get("noLeadingSpace", f"{label} cannot start with empty spaces.")
            errors[field] = msg
            if not first_error:
                first_error = msg
            continue

        val = raw_str.strip()

        # 2. Required check
        if rules.get("required") and not val:
            msg = error_msgs.get("required", f"{label} is required.")
            errors[field] = msg
            if not first_error:
                first_error = msg
            continue

        if not val and not rules.get("required"):
            continue

        # 3. Disallow numbers check (for University name & Degree program)
        if rules.get("disallowNumbers") and re.search(r"[0-9]", val):
            msg = error_msgs.get("disallowNumbers", f"{label} cannot contain numbers.")
            errors[field] = msg
            if not first_error:
                first_error = msg
            continue

        # 4. Digits-only check (for Semester)
        if rules.get("onlyNumbers") and not val.isdigit():
            msg = error_msgs.get("onlyNumbers", f"{label} must be numbers only.")
            errors[field] = msg
            if not first_error:
                first_error = msg
            continue

        # 5. Numerical range check (for Semester: 1 to 12)
        if rules.get("minValue") is not None or rules.get("maxValue") is not None:
            try:
                num_val = int(val)
                min_v = rules.get("minValue")
                max_v = rules.get("maxValue")
                if (min_v is not None and num_val < min_v) or (max_v is not None and num_val > max_v):
                    msg = error_msgs.get("range", f"{label} must be between {min_v} and {max_v}.")
                    errors[field] = msg
                    if not first_error:
                        first_error = msg
                    continue
            except ValueError:
                msg = error_msgs.get("onlyNumbers", f"{label} must be numbers only.")
                errors[field] = msg
                if not first_error:
                    first_error = msg
                continue

        # 6. Min length check
        min_len = rules.get("minLength")
        if min_len and len(val) < min_len:
            msg = error_msgs.get("minLength", f"{label} must be at least {min_len} characters.")
            errors[field] = msg
            if not first_error:
                first_error = msg
            continue

        # 7. Max length check
        max_len = rules.get("maxLength")
        if max_len and len(val) > max_len:
            msg = error_msgs.get("maxLength", f"{label} cannot exceed {max_len} characters.")
            errors[field] = msg
            if not first_error:
                first_error = msg
            continue

        # 8. Max words check
        max_words = rules.get("maxWords")
        if max_words:
            words = val.split()
            if len(words) > max_words:
                msg = error_msgs.get("maxWords", f"{label} cannot exceed {max_words} words.")
                errors[field] = msg
                if not first_error:
                    first_error = msg
                continue

    is_valid = len(errors) == 0
    return is_valid, errors, first_error
