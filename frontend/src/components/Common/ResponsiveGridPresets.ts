/**
 * ResponsiveGrid Presets
 * 
 * Preset grid configurations for common layouts.
 */

export interface ResponsiveColSpan {
  xs?: number;
  sm?: number;
  md?: number;
  lg?: number;
  xl?: number;
  xxl?: number;
}

/**
 * Preset grid configurations for common layouts
 */
export const GridPresets = {
  // 1 column on mobile, 2 on tablet, 4 on desktop
  cards: {
    xs: 24,
    sm: 12,
    md: 12,
    lg: 6,
    xl: 6,
    xxl: 6,
  } as ResponsiveColSpan,
  
  // 1 column on mobile, 2 on tablet, 3 on desktop
  threeColumn: {
    xs: 24,
    sm: 12,
    md: 12,
    lg: 8,
    xl: 8,
    xxl: 8,
  } as ResponsiveColSpan,
  
  // 1 column on mobile, 2 on tablet+
  twoColumn: {
    xs: 24,
    sm: 24,
    md: 12,
    lg: 12,
    xl: 12,
    xxl: 12,
  } as ResponsiveColSpan,
  
  // Sidebar layout (sidebar + main content)
  sidebar: {
    sidebar: {
      xs: 24,
      sm: 24,
      md: 8,
      lg: 6,
      xl: 6,
      xxl: 4,
    } as ResponsiveColSpan,
    main: {
      xs: 24,
      sm: 24,
      md: 16,
      lg: 18,
      xl: 18,
      xxl: 20,
    } as ResponsiveColSpan,
  },
  
  // Dashboard stats (4 cards)
  stats: {
    xs: 24,
    sm: 12,
    md: 12,
    lg: 6,
    xl: 6,
    xxl: 6,
  } as ResponsiveColSpan,
  
  // Form layout (labels + inputs)
  form: {
    label: {
      xs: 24,
      sm: 24,
      md: 6,
      lg: 6,
      xl: 4,
      xxl: 4,
    } as ResponsiveColSpan,
    input: {
      xs: 24,
      sm: 24,
      md: 18,
      lg: 18,
      xl: 20,
      xxl: 20,
    } as ResponsiveColSpan,
  },
};

export default GridPresets;
