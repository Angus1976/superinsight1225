/**
 * Progress component wrapper with proper format handling
 * 
 * Fixes the percentage display issue in Ant Design Progress component
 * by explicitly providing a format function.
 */

import React from 'react';
import { Progress, ProgressProps } from 'antd';

export interface ProgressWithFormatProps extends ProgressProps {
  /** Override default format function */
  customFormat?: (percent?: number) => React.ReactNode;
}

const ProgressWithFormat: React.FC<ProgressWithFormatProps> = ({
  customFormat,
  format,
  ...props
}) => {
  // Use custom format if provided, otherwise use default format, or fallback to percentage display
  const finalFormat = customFormat || format || ((percent) => `${percent}%`);

  return <Progress {...props} format={finalFormat} />;
};

export default ProgressWithFormat;
