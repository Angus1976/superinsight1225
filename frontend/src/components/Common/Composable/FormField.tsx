/**
 * FormField Component
 * 
 * A reusable form field wrapper that provides consistent
 * styling, validation, and accessibility features.
 * 
 * @module components/Common/Composable/FormField
 * @version 1.0.0
 */

import React, { type ReactNode, memo, useId } from 'react';
import { Form, Tooltip, Typography } from 'antd';
import { InfoCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import type { Rule } from 'antd/es/form';
import styles from './FormField.module.scss';

const { Text } = Typography;

/**
 * FormField component props
 */
export interface FormFieldProps {
  /** Field name for form binding */
  name: string | (string | number)[];
  /** Field label */
  label?: ReactNode;
  /** Help text below the field */
  help?: ReactNode;
  /** Tooltip for the label */
  tooltip?: string;
  /** Required field indicator */
  required?: boolean;
  /** Validation rules */
  rules?: Rule[];
  /** Initial value */
  initialValue?: unknown;
  /** Field children (input component) */
  children: ReactNode;
  /** Custom class name */
  className?: string;
  /** Label column span */
  labelCol?: { span?: number; offset?: number };
  /** Wrapper column span */
  wrapperCol?: { span?: number; offset?: number };
  /** Colon after label */
  colon?: boolean;
  /** Extra content after field */
  extra?: ReactNode;
  /** Hide label */
  noLabel?: boolean;
  /** Inline layout */
  inline?: boolean;
  /** Dependencies for validation */
  dependencies?: string[];
  /** Should update function */
  shouldUpdate?: boolean | ((prevValues: unknown, curValues: unknown) => boolean);
  /** Preserve field value when unmounted */
  preserve?: boolean;
  /** Validation trigger */
  validateTrigger?: string | string[];
  /** Value prop name */
  valuePropName?: string;
  /** Get value from event */
  getValueFromEvent?: (...args: unknown[]) => unknown;
  /** Normalize value */
  normalize?: (value: unknown, prevValue: unknown, allValues: unknown) => unknown;
}

/**
 * FormField component for consistent form field rendering
 */
export const FormField = memo(function FormField({
  name,
  label,
  help,
  tooltip,
  required = false,
  rules = [],
  initialValue,
  children,
  className,
  labelCol,
  wrapperCol,
  colon = true,
  extra,
  noLabel = false,
  inline = false,
  dependencies,
  shouldUpdate,
  preserve,
  validateTrigger,
  valuePropName,
  getValueFromEvent,
  normalize,
}: FormFieldProps): React.ReactElement {
  const fieldId = useId();

  // Build validation rules
  const fieldRules: Rule[] = [
    ...(required ? [{ required: true, message: `请输入${label || '此字段'}` }] : []),
    ...rules,
  ];

  // Render label with optional tooltip
  const renderLabel = () => {
    if (noLabel) return undefined;
    if (!label) return undefined;

    return (
      <span className={styles.labelWrapper}>
        {label}
        {tooltip && (
          <Tooltip title={tooltip}>
            <QuestionCircleOutlined className={styles.tooltipIcon} />
          </Tooltip>
        )}
      </span>
    );
  };

  return (
    <Form.Item
      name={name}
      label={renderLabel()}
      help={help}
      required={required}
      rules={fieldRules}
      initialValue={initialValue}
      className={`${styles.formField} ${inline ? styles.inline : ''} ${className || ''}`}
      labelCol={labelCol}
      wrapperCol={wrapperCol}
      colon={colon}
      extra={extra}
      dependencies={dependencies}
      shouldUpdate={shouldUpdate}
      preserve={preserve}
      validateTrigger={validateTrigger}
      valuePropName={valuePropName}
      getValueFromEvent={getValueFromEvent}
      normalize={normalize}
    >
      {children}
    </Form.Item>
  );
});
