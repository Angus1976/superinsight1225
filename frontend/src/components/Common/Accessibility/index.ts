/**
 * Accessibility Components
 * 
 * WCAG 2.1 compliant accessibility components and utilities.
 */

// Skip Links
export { SkipLinks } from './SkipLinks';
export type { default as SkipLinksDefault } from './SkipLinks';

// Live Region
export { 
  LiveRegion, 
  LiveRegionProvider, 
  useLiveRegion 
} from './LiveRegion';

// Focus Trap
export { FocusTrap } from './FocusTrap';
export type { default as FocusTrapDefault } from './FocusTrap';

// Visually Hidden
export { 
  VisuallyHidden, 
  SrOnly, 
  IconLabel, 
  AccessibleDescription 
} from './VisuallyHidden';

// Accessible Button
export { 
  AccessibleButton, 
  AccessibleIconButton, 
  AccessibleToggleButton 
} from './AccessibleButton';

// Accessible Form
export {
  AccessibleFormItem,
  AccessibleInput,
  AccessibleSelect,
  AccessibleCheckboxGroup,
  AccessibleRadioGroup,
  FormErrorSummary,
} from './AccessibleForm';

// Accessibility Settings
export {
  AccessibilitySettings,
  AccessibilitySettingsButton,
} from './AccessibilitySettings';
