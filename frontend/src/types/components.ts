/**
 * Component Type Definitions
 * 
 * Strict type definitions for component props used throughout the application.
 * These types ensure consistent component interfaces and better type safety.
 */

import type { ReactNode, CSSProperties, RefObject } from 'react';
import type { 
  CommonProps, 
  WithLoading, 
  WithError, 
  WithDisabled,
  Size,
  ThemeMode,
  ID,
  ISODateString,
} from './common';

// ============================================================================
// Base Component Props
// ============================================================================

/** Base props for all components */
export interface BaseComponentProps extends CommonProps {
  /** Unique identifier for the component */
  id?: string;
  /** Test ID for testing purposes */
  'data-testid'?: string;
  /** ARIA label for accessibility */
  'aria-label'?: string;
}

/** Base props for interactive components */
export interface InteractiveComponentProps extends BaseComponentProps, WithDisabled {
  /** Tab index for keyboard navigation */
  tabIndex?: number;
  /** Click handler */
  onClick?: (event: React.MouseEvent) => void;
  /** Keyboard handler */
  onKeyDown?: (event: React.KeyboardEvent) => void;
  /** Focus handler */
  onFocus?: (event: React.FocusEvent) => void;
  /** Blur handler */
  onBlur?: (event: React.FocusEvent) => void;
}

/** Base props for data display components */
export interface DataDisplayProps<T = unknown> extends BaseComponentProps, WithLoading, WithError {
  /** Data to display */
  data: T | null;
  /** Empty state message */
  emptyMessage?: string;
  /** Empty state render */
  emptyRender?: ReactNode;
}

// ============================================================================
// Layout Component Props
// ============================================================================

/** Container component props */
export interface ContainerProps extends BaseComponentProps {
  /** Maximum width of the container */
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | 'full' | number;
  /** Padding size */
  padding?: Size | number;
  /** Center content horizontally */
  centered?: boolean;
  /** Children elements */
  children: ReactNode;
}

/** Grid component props */
export interface GridProps extends BaseComponentProps {
  /** Number of columns */
  columns?: number | { xs?: number; sm?: number; md?: number; lg?: number; xl?: number };
  /** Gap between items */
  gap?: Size | number;
  /** Row gap */
  rowGap?: Size | number;
  /** Column gap */
  columnGap?: Size | number;
  /** Align items */
  alignItems?: 'start' | 'center' | 'end' | 'stretch';
  /** Justify content */
  justifyContent?: 'start' | 'center' | 'end' | 'space-between' | 'space-around';
  /** Children elements */
  children: ReactNode;
}

/** Stack component props */
export interface StackProps extends BaseComponentProps {
  /** Direction of the stack */
  direction?: 'horizontal' | 'vertical';
  /** Gap between items */
  gap?: Size | number;
  /** Align items */
  align?: 'start' | 'center' | 'end' | 'stretch';
  /** Justify content */
  justify?: 'start' | 'center' | 'end' | 'space-between' | 'space-around';
  /** Wrap items */
  wrap?: boolean;
  /** Children elements */
  children: ReactNode;
}

/** Spacer component props */
export interface SpacerProps extends BaseComponentProps {
  /** Size of the spacer */
  size?: Size | number;
  /** Direction of the spacer */
  direction?: 'horizontal' | 'vertical';
  /** Flex grow */
  grow?: boolean;
}

// ============================================================================
// Data Display Component Props
// ============================================================================

/** Metric card props */
export interface MetricCardProps extends BaseComponentProps, WithLoading {
  /** Card title */
  title: string;
  /** Card subtitle */
  subtitle?: string;
  /** Metric value */
  value: number | string;
  /** Value suffix (e.g., '%', 'ms') */
  suffix?: string;
  /** Value prefix (e.g., '$', '¥') */
  prefix?: ReactNode;
  /** Trend percentage */
  trend?: number;
  /** Trend label */
  trendLabel?: string;
  /** Card color */
  color?: string;
  /** Card icon */
  icon?: ReactNode;
  /** Target value for progress */
  target?: number;
  /** Current progress value */
  progress?: number;
  /** Status indicator */
  status?: 'normal' | 'warning' | 'error' | 'success';
  /** Whether the card is refreshable */
  refreshable?: boolean;
  /** Refresh callback */
  onRefresh?: () => void;
  /** Last updated timestamp */
  lastUpdated?: Date;
  /** Extra content */
  extra?: ReactNode;
}

/** Data table column definition */
export interface TableColumn<T = unknown> {
  /** Column key */
  key: string;
  /** Column title */
  title: string;
  /** Data index (path to data) */
  dataIndex?: string | string[];
  /** Column width */
  width?: number | string;
  /** Fixed column position */
  fixed?: 'left' | 'right';
  /** Sortable */
  sortable?: boolean;
  /** Filterable */
  filterable?: boolean;
  /** Custom render function */
  render?: (value: unknown, record: T, index: number) => ReactNode;
  /** Align content */
  align?: 'left' | 'center' | 'right';
  /** Ellipsis overflow */
  ellipsis?: boolean;
  /** Hidden column */
  hidden?: boolean;
}

/** Data table props */
export interface DataTableProps<T extends { id: ID }> extends BaseComponentProps, WithLoading, WithError {
  /** Table columns */
  columns: TableColumn<T>[];
  /** Table data */
  data: T[];
  /** Row key */
  rowKey?: keyof T | ((record: T) => string);
  /** Pagination config */
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onChange: (page: number, pageSize: number) => void;
  };
  /** Sort config */
  sort?: {
    field: string;
    order: 'asc' | 'desc';
    onChange: (field: string, order: 'asc' | 'desc') => void;
  };
  /** Selection config */
  selection?: {
    selectedKeys: ID[];
    onChange: (keys: ID[], rows: T[]) => void;
    type?: 'checkbox' | 'radio';
  };
  /** Row click handler */
  onRowClick?: (record: T, index: number) => void;
  /** Empty state message */
  emptyMessage?: string;
  /** Sticky header */
  stickyHeader?: boolean;
  /** Bordered style */
  bordered?: boolean;
  /** Striped rows */
  striped?: boolean;
  /** Compact size */
  size?: 'small' | 'middle' | 'large';
}

/** List item props */
export interface ListItemProps<T = unknown> extends InteractiveComponentProps {
  /** Item data */
  item: T;
  /** Item index */
  index: number;
  /** Selected state */
  selected?: boolean;
  /** Highlighted state */
  highlighted?: boolean;
  /** Item actions */
  actions?: ReactNode;
  /** Item avatar/icon */
  avatar?: ReactNode;
  /** Item title */
  title: ReactNode;
  /** Item description */
  description?: ReactNode;
  /** Item metadata */
  metadata?: ReactNode;
}

// ============================================================================
// Form Component Props
// ============================================================================

/** Base input props */
export interface BaseInputProps<T = string> extends InteractiveComponentProps {
  /** Input name */
  name: string;
  /** Input value */
  value: T;
  /** Change handler */
  onChange: (value: T) => void;
  /** Input label */
  label?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Required field */
  required?: boolean;
  /** Error message */
  error?: string;
  /** Help text */
  helpText?: string;
  /** Input size */
  size?: 'small' | 'middle' | 'large';
  /** Full width */
  fullWidth?: boolean;
}

/** Text input props */
export interface TextInputProps extends BaseInputProps<string> {
  /** Input type */
  type?: 'text' | 'email' | 'password' | 'tel' | 'url' | 'search';
  /** Maximum length */
  maxLength?: number;
  /** Minimum length */
  minLength?: number;
  /** Pattern for validation */
  pattern?: string;
  /** Auto complete */
  autoComplete?: string;
  /** Prefix element */
  prefix?: ReactNode;
  /** Suffix element */
  suffix?: ReactNode;
  /** Allow clear */
  allowClear?: boolean;
}

/** Number input props */
export interface NumberInputProps extends BaseInputProps<number | null> {
  /** Minimum value */
  min?: number;
  /** Maximum value */
  max?: number;
  /** Step value */
  step?: number;
  /** Precision (decimal places) */
  precision?: number;
  /** Formatter function */
  formatter?: (value: number | undefined) => string;
  /** Parser function */
  parser?: (value: string | undefined) => number;
  /** Prefix element */
  prefix?: ReactNode;
  /** Suffix element */
  suffix?: ReactNode;
}

/** Select option */
export interface SelectOption<T = string> {
  /** Option value */
  value: T;
  /** Option label */
  label: string;
  /** Option disabled */
  disabled?: boolean;
  /** Option group */
  group?: string;
  /** Option icon */
  icon?: ReactNode;
  /** Option description */
  description?: string;
}

/** Select input props */
export interface SelectInputProps<T = string> extends BaseInputProps<T | T[] | null> {
  /** Select options */
  options: SelectOption<T>[];
  /** Multiple selection */
  multiple?: boolean;
  /** Searchable */
  searchable?: boolean;
  /** Clearable */
  clearable?: boolean;
  /** Loading state */
  loading?: boolean;
  /** No options message */
  noOptionsMessage?: string;
  /** Option render function */
  optionRender?: (option: SelectOption<T>) => ReactNode;
  /** Max tag count (for multiple) */
  maxTagCount?: number;
}

/** Date picker props */
export interface DatePickerProps extends BaseInputProps<Date | null> {
  /** Date format */
  format?: string;
  /** Show time picker */
  showTime?: boolean;
  /** Minimum date */
  minDate?: Date;
  /** Maximum date */
  maxDate?: Date;
  /** Disabled dates */
  disabledDate?: (date: Date) => boolean;
  /** Picker type */
  picker?: 'date' | 'week' | 'month' | 'quarter' | 'year';
}

/** Date range picker props */
export interface DateRangePickerProps extends BaseInputProps<[Date | null, Date | null]> {
  /** Date format */
  format?: string;
  /** Show time picker */
  showTime?: boolean;
  /** Minimum date */
  minDate?: Date;
  /** Maximum date */
  maxDate?: Date;
  /** Disabled dates */
  disabledDate?: (date: Date) => boolean;
  /** Preset ranges */
  presets?: Array<{
    label: string;
    value: [Date, Date];
  }>;
}

/** Checkbox props */
export interface CheckboxProps extends Omit<BaseInputProps<boolean>, 'placeholder'> {
  /** Indeterminate state */
  indeterminate?: boolean;
}

/** Radio group props */
export interface RadioGroupProps<T = string> extends BaseInputProps<T> {
  /** Radio options */
  options: SelectOption<T>[];
  /** Button style */
  buttonStyle?: 'outline' | 'solid';
  /** Option type */
  optionType?: 'default' | 'button';
  /** Direction */
  direction?: 'horizontal' | 'vertical';
}

/** Switch props */
export interface SwitchProps extends Omit<BaseInputProps<boolean>, 'placeholder'> {
  /** Checked children */
  checkedChildren?: ReactNode;
  /** Unchecked children */
  unCheckedChildren?: ReactNode;
}

// ============================================================================
// Feedback Component Props
// ============================================================================

/** Alert props */
export interface AlertProps extends BaseComponentProps {
  /** Alert type */
  type: 'info' | 'success' | 'warning' | 'error';
  /** Alert title */
  title?: string;
  /** Alert message */
  message: ReactNode;
  /** Show icon */
  showIcon?: boolean;
  /** Closable */
  closable?: boolean;
  /** Close handler */
  onClose?: () => void;
  /** Action buttons */
  action?: ReactNode;
  /** Banner style */
  banner?: boolean;
}

/** Toast/Notification props */
export interface ToastProps {
  /** Toast type */
  type: 'info' | 'success' | 'warning' | 'error';
  /** Toast title */
  title?: string;
  /** Toast message */
  message: ReactNode;
  /** Duration in milliseconds (0 for persistent) */
  duration?: number;
  /** Position */
  position?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight';
  /** Closable */
  closable?: boolean;
  /** Close handler */
  onClose?: () => void;
  /** Action button */
  action?: {
    label: string;
    onClick: () => void;
  };
}

/** Modal props */
export interface ModalProps extends BaseComponentProps {
  /** Modal open state */
  open: boolean;
  /** Close handler */
  onClose: () => void;
  /** Modal title */
  title?: ReactNode;
  /** Modal footer */
  footer?: ReactNode;
  /** Modal width */
  width?: number | string;
  /** Centered modal */
  centered?: boolean;
  /** Close on mask click */
  maskClosable?: boolean;
  /** Close on escape key */
  keyboard?: boolean;
  /** Destroy on close */
  destroyOnClose?: boolean;
  /** Confirm loading */
  confirmLoading?: boolean;
  /** OK button text */
  okText?: string;
  /** Cancel button text */
  cancelText?: string;
  /** OK handler */
  onOk?: () => void | Promise<void>;
  /** Children content */
  children: ReactNode;
}

/** Drawer props */
export interface DrawerProps extends BaseComponentProps {
  /** Drawer open state */
  open: boolean;
  /** Close handler */
  onClose: () => void;
  /** Drawer title */
  title?: ReactNode;
  /** Drawer placement */
  placement?: 'top' | 'right' | 'bottom' | 'left';
  /** Drawer width (for left/right) */
  width?: number | string;
  /** Drawer height (for top/bottom) */
  height?: number | string;
  /** Close on mask click */
  maskClosable?: boolean;
  /** Close on escape key */
  keyboard?: boolean;
  /** Destroy on close */
  destroyOnClose?: boolean;
  /** Footer content */
  footer?: ReactNode;
  /** Children content */
  children: ReactNode;
}

/** Popover props */
export interface PopoverProps extends BaseComponentProps {
  /** Popover content */
  content: ReactNode;
  /** Popover title */
  title?: ReactNode;
  /** Trigger element */
  children: ReactNode;
  /** Trigger type */
  trigger?: 'hover' | 'click' | 'focus' | 'contextMenu';
  /** Placement */
  placement?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight' | 'left' | 'leftTop' | 'leftBottom' | 'right' | 'rightTop' | 'rightBottom';
  /** Open state (controlled) */
  open?: boolean;
  /** Open change handler */
  onOpenChange?: (open: boolean) => void;
  /** Arrow visibility */
  arrow?: boolean;
}

/** Tooltip props */
export interface TooltipProps extends BaseComponentProps {
  /** Tooltip content */
  title: ReactNode;
  /** Trigger element */
  children: ReactNode;
  /** Placement */
  placement?: 'top' | 'topLeft' | 'topRight' | 'bottom' | 'bottomLeft' | 'bottomRight' | 'left' | 'leftTop' | 'leftBottom' | 'right' | 'rightTop' | 'rightBottom';
  /** Trigger type */
  trigger?: 'hover' | 'click' | 'focus';
  /** Open state (controlled) */
  open?: boolean;
  /** Open change handler */
  onOpenChange?: (open: boolean) => void;
  /** Color */
  color?: string;
}

// ============================================================================
// Navigation Component Props
// ============================================================================

/** Breadcrumb item */
export interface BreadcrumbItem {
  /** Item key */
  key: string;
  /** Item label */
  label: ReactNode;
  /** Item path */
  path?: string;
  /** Item icon */
  icon?: ReactNode;
  /** Click handler */
  onClick?: () => void;
}

/** Breadcrumb props */
export interface BreadcrumbProps extends BaseComponentProps {
  /** Breadcrumb items */
  items: BreadcrumbItem[];
  /** Separator */
  separator?: ReactNode;
  /** Max items before collapse */
  maxItems?: number;
}

/** Tab item */
export interface TabItem {
  /** Tab key */
  key: string;
  /** Tab label */
  label: ReactNode;
  /** Tab icon */
  icon?: ReactNode;
  /** Tab content */
  children?: ReactNode;
  /** Tab disabled */
  disabled?: boolean;
  /** Tab closable */
  closable?: boolean;
}

/** Tabs props */
export interface TabsProps extends BaseComponentProps {
  /** Tab items */
  items: TabItem[];
  /** Active tab key */
  activeKey?: string;
  /** Default active key */
  defaultActiveKey?: string;
  /** Tab change handler */
  onChange?: (key: string) => void;
  /** Tab type */
  type?: 'line' | 'card' | 'editable-card';
  /** Tab position */
  tabPosition?: 'top' | 'right' | 'bottom' | 'left';
  /** Tab size */
  size?: 'small' | 'middle' | 'large';
  /** Centered tabs */
  centered?: boolean;
  /** Tab bar extra content */
  tabBarExtraContent?: ReactNode;
}

/** Menu item */
export interface MenuItem {
  /** Item key */
  key: string;
  /** Item label */
  label: ReactNode;
  /** Item icon */
  icon?: ReactNode;
  /** Item path */
  path?: string;
  /** Item disabled */
  disabled?: boolean;
  /** Item danger style */
  danger?: boolean;
  /** Sub menu items */
  children?: MenuItem[];
  /** Item type */
  type?: 'group' | 'divider';
}

/** Menu props */
export interface MenuProps extends BaseComponentProps {
  /** Menu items */
  items: MenuItem[];
  /** Selected keys */
  selectedKeys?: string[];
  /** Open keys (for sub menus) */
  openKeys?: string[];
  /** Menu mode */
  mode?: 'vertical' | 'horizontal' | 'inline';
  /** Menu theme */
  theme?: 'light' | 'dark';
  /** Collapsed state */
  collapsed?: boolean;
  /** Select handler */
  onSelect?: (key: string) => void;
  /** Open change handler */
  onOpenChange?: (keys: string[]) => void;
  /** Click handler */
  onClick?: (key: string) => void;
}

// ============================================================================
// Progress Component Props
// ============================================================================

/** Progress bar props */
export interface ProgressBarProps extends BaseComponentProps {
  /** Progress percentage (0-100) */
  percent: number;
  /** Progress status */
  status?: 'normal' | 'success' | 'exception' | 'active';
  /** Show percentage text */
  showInfo?: boolean;
  /** Stroke color */
  strokeColor?: string | { from: string; to: string };
  /** Trail color */
  trailColor?: string;
  /** Stroke width */
  strokeWidth?: number;
  /** Progress type */
  type?: 'line' | 'circle' | 'dashboard';
  /** Size */
  size?: 'small' | 'default';
  /** Format function */
  format?: (percent: number) => ReactNode;
}

/** Steps item */
export interface StepItem {
  /** Step key */
  key: string;
  /** Step title */
  title: ReactNode;
  /** Step description */
  description?: ReactNode;
  /** Step icon */
  icon?: ReactNode;
  /** Step status */
  status?: 'wait' | 'process' | 'finish' | 'error';
  /** Step disabled */
  disabled?: boolean;
}

/** Steps props */
export interface StepsProps extends BaseComponentProps {
  /** Step items */
  items: StepItem[];
  /** Current step */
  current: number;
  /** Steps direction */
  direction?: 'horizontal' | 'vertical';
  /** Steps type */
  type?: 'default' | 'navigation' | 'inline';
  /** Steps size */
  size?: 'small' | 'default';
  /** Step change handler */
  onChange?: (current: number) => void;
  /** Clickable steps */
  clickable?: boolean;
}

// ============================================================================
// Chart Component Props
// ============================================================================

/** Chart data point */
export interface ChartDataPoint {
  /** X-axis value */
  x: string | number | Date;
  /** Y-axis value */
  y: number;
  /** Data label */
  label?: string;
  /** Data color */
  color?: string;
  /** Additional data */
  [key: string]: unknown;
}

/** Chart series */
export interface ChartSeries {
  /** Series name */
  name: string;
  /** Series data */
  data: ChartDataPoint[];
  /** Series type */
  type?: 'line' | 'bar' | 'area' | 'scatter' | 'pie';
  /** Series color */
  color?: string;
  /** Show in legend */
  showInLegend?: boolean;
}

/** Base chart props */
export interface BaseChartProps extends BaseComponentProps, WithLoading {
  /** Chart data */
  data: ChartSeries[];
  /** Chart title */
  title?: string;
  /** Chart subtitle */
  subtitle?: string;
  /** Chart height */
  height?: number | string;
  /** Chart width */
  width?: number | string;
  /** Show legend */
  showLegend?: boolean;
  /** Legend position */
  legendPosition?: 'top' | 'right' | 'bottom' | 'left';
  /** Show tooltip */
  showTooltip?: boolean;
  /** Show grid */
  showGrid?: boolean;
  /** Animation enabled */
  animation?: boolean;
  /** Click handler */
  onClick?: (data: ChartDataPoint, series: ChartSeries) => void;
}

/** Line chart props */
export interface LineChartProps extends BaseChartProps {
  /** Smooth lines */
  smooth?: boolean;
  /** Show dots */
  showDots?: boolean;
  /** Dot size */
  dotSize?: number;
  /** Line width */
  lineWidth?: number;
  /** Area fill */
  areaFill?: boolean;
}

/** Bar chart props */
export interface BarChartProps extends BaseChartProps {
  /** Horizontal bars */
  horizontal?: boolean;
  /** Stacked bars */
  stacked?: boolean;
  /** Bar width */
  barWidth?: number;
  /** Bar gap */
  barGap?: number;
  /** Show bar labels */
  showLabels?: boolean;
}

/** Pie chart props */
export interface PieChartProps extends BaseComponentProps, WithLoading {
  /** Chart data */
  data: Array<{
    name: string;
    value: number;
    color?: string;
  }>;
  /** Chart title */
  title?: string;
  /** Chart height */
  height?: number | string;
  /** Inner radius (for donut chart) */
  innerRadius?: number;
  /** Outer radius */
  outerRadius?: number;
  /** Show labels */
  showLabels?: boolean;
  /** Show legend */
  showLegend?: boolean;
  /** Legend position */
  legendPosition?: 'top' | 'right' | 'bottom' | 'left';
  /** Click handler */
  onClick?: (data: { name: string; value: number }) => void;
}


