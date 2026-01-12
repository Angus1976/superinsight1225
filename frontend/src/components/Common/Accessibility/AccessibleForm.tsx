/**
 * AccessibleForm Components
 * 
 * Accessible form components with proper ARIA attributes and error handling.
 * WCAG 2.1 Success Criteria 1.3.1, 3.3.1, 3.3.2, 4.1.2
 */

import { memo, forwardRef, ReactNode, useId, useCallback } from 'react';
import { Form, Input, Select, Checkbox, Radio, DatePicker, InputNumber } from 'antd';
import type { FormItemProps, InputProps, SelectProps } from 'antd';
import { useLiveRegion } from './LiveRegion';

// ============================================
// Accessible Form Item
// ============================================

interface AccessibleFormItemProps extends FormItemProps {
  /** Whether the field is required */
  required?: boolean;
  /** Help text for the field */
  helpText?: string;
  /** Error message */
  errorMessage?: string;
  /** Success message */
  successMessage?: string;
  /** Children */
  children: ReactNode;
}

export const AccessibleFormItem = memo<AccessibleFormItemProps>(({
  required,
  helpText,
  errorMessage,
  successMessage,
  label,
  children,
  ...props
}) => {
  const helpId = useId();
  const errorId = useId();
  const successId = useId();

  // Build aria-describedby
  const describedBy = [
    helpText ? helpId : null,
    errorMessage ? errorId : null,
    successMessage ? successId : null,
  ].filter(Boolean).join(' ') || undefined;

  return (
    <Form.Item
      label={
        <>
          {label}
          {required && <span className="required-indicator" aria-hidden="true" />}
        </>
      }
      required={required}
      validateStatus={errorMessage ? 'error' : successMessage ? 'success' : undefined}
      help={
        <>
          {helpText && (
            <span id={helpId} className="form-help">
              {helpText}
            </span>
          )}
          {errorMessage && (
            <span id={errorId} className="form-error" role="alert">
              {errorMessage}
            </span>
          )}
          {successMessage && (
            <span id={successId} className="form-success">
              {successMessage}
            </span>
          )}
        </>
      }
      {...props}
    >
      {children}
    </Form.Item>
  );
});

AccessibleFormItem.displayName = 'AccessibleFormItem';

// ============================================
// Accessible Input
// ============================================

interface AccessibleInputProps extends InputProps {
  /** Accessible label (required if no visible label) */
  accessibleLabel?: string;
  /** Error state */
  hasError?: boolean;
  /** Description for screen readers */
  accessibleDescription?: string;
}

export const AccessibleInput = memo(forwardRef<HTMLInputElement, AccessibleInputProps>(({
  accessibleLabel,
  hasError,
  accessibleDescription,
  id,
  ...props
}, ref) => {
  const generatedId = useId();
  const inputId = id || generatedId;
  const descriptionId = `${inputId}-desc`;

  return (
    <>
      <Input
        ref={ref}
        id={inputId}
        aria-label={accessibleLabel}
        aria-invalid={hasError}
        aria-describedby={accessibleDescription ? descriptionId : undefined}
        {...props}
      />
      {accessibleDescription && (
        <span id={descriptionId} className="sr-only">
          {accessibleDescription}
        </span>
      )}
    </>
  );
}));

AccessibleInput.displayName = 'AccessibleInput';

// ============================================
// Accessible Select
// ============================================

interface AccessibleSelectProps extends SelectProps {
  /** Accessible label */
  accessibleLabel?: string;
  /** Error state */
  hasError?: boolean;
  /** Description for screen readers */
  accessibleDescription?: string;
}

export const AccessibleSelect = memo<AccessibleSelectProps>(({
  accessibleLabel,
  hasError,
  accessibleDescription,
  id,
  ...props
}) => {
  const generatedId = useId();
  const selectId = id || generatedId;
  const descriptionId = `${selectId}-desc`;

  return (
    <>
      <Select
        id={selectId}
        aria-label={accessibleLabel}
        aria-invalid={hasError}
        aria-describedby={accessibleDescription ? descriptionId : undefined}
        {...props}
      />
      {accessibleDescription && (
        <span id={descriptionId} className="sr-only">
          {accessibleDescription}
        </span>
      )}
    </>
  );
});

AccessibleSelect.displayName = 'AccessibleSelect';

// ============================================
// Accessible Checkbox Group
// ============================================

interface AccessibleCheckboxGroupProps {
  /** Group label */
  label: string;
  /** Options */
  options: Array<{ label: string; value: string; disabled?: boolean }>;
  /** Selected values */
  value?: string[];
  /** Change handler */
  onChange?: (values: string[]) => void;
  /** Error state */
  hasError?: boolean;
  /** Required */
  required?: boolean;
}

export const AccessibleCheckboxGroup = memo<AccessibleCheckboxGroupProps>(({
  label,
  options,
  value,
  onChange,
  hasError,
  required,
}) => {
  const groupId = useId();

  return (
    <fieldset
      role="group"
      aria-labelledby={`${groupId}-label`}
      aria-required={required}
      aria-invalid={hasError}
    >
      <legend id={`${groupId}-label`} className="sr-only">
        {label}
        {required && ' (required)'}
      </legend>
      <Checkbox.Group
        options={options}
        value={value}
        onChange={onChange}
      />
    </fieldset>
  );
});

AccessibleCheckboxGroup.displayName = 'AccessibleCheckboxGroup';

// ============================================
// Accessible Radio Group
// ============================================

interface AccessibleRadioGroupProps {
  /** Group label */
  label: string;
  /** Options */
  options: Array<{ label: string; value: string; disabled?: boolean }>;
  /** Selected value */
  value?: string;
  /** Change handler */
  onChange?: (value: string) => void;
  /** Error state */
  hasError?: boolean;
  /** Required */
  required?: boolean;
  /** Layout direction */
  direction?: 'horizontal' | 'vertical';
}

export const AccessibleRadioGroup = memo<AccessibleRadioGroupProps>(({
  label,
  options,
  value,
  onChange,
  hasError,
  required,
  direction = 'horizontal',
}) => {
  const groupId = useId();

  return (
    <fieldset
      role="radiogroup"
      aria-labelledby={`${groupId}-label`}
      aria-required={required}
      aria-invalid={hasError}
    >
      <legend id={`${groupId}-label`} className="sr-only">
        {label}
        {required && ' (required)'}
      </legend>
      <Radio.Group
        options={options}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        optionType="default"
        style={{ display: 'flex', flexDirection: direction === 'vertical' ? 'column' : 'row', gap: 8 }}
      />
    </fieldset>
  );
});

AccessibleRadioGroup.displayName = 'AccessibleRadioGroup';

// ============================================
// Form Error Summary
// ============================================

interface FormErrorSummaryProps {
  /** List of errors */
  errors: Array<{ field: string; message: string }>;
  /** Title for the error summary */
  title?: string;
}

export const FormErrorSummary = memo<FormErrorSummaryProps>(({
  errors,
  title = 'Please correct the following errors:',
}) => {
  const { announceAssertive } = useLiveRegion();

  // Announce errors to screen readers
  useCallback(() => {
    if (errors.length > 0) {
      const errorCount = errors.length;
      const message = `${errorCount} error${errorCount > 1 ? 's' : ''} found. ${title}`;
      announceAssertive(message);
    }
  }, [errors, title, announceAssertive]);

  if (errors.length === 0) return null;

  return (
    <div
      role="alert"
      aria-labelledby="error-summary-title"
      className="form-error-summary"
      tabIndex={-1}
    >
      <h2 id="error-summary-title" className="form-error-summary-title">
        {title}
      </h2>
      <ul className="form-error-summary-list">
        {errors.map(({ field, message }) => (
          <li key={field}>
            <a href={`#${field}`} className="form-error-summary-link">
              {message}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
});

FormErrorSummary.displayName = 'FormErrorSummary';

export default {
  AccessibleFormItem,
  AccessibleInput,
  AccessibleSelect,
  AccessibleCheckboxGroup,
  AccessibleRadioGroup,
  FormErrorSummary,
};
