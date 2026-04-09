// Export common components
export * from './Loading';
export * from './ErrorBoundary';
export * from './SkeletonLoader';
export * from './withPerformanceMonitor';
export * from './PerformanceProfiler';
export * from './MemoryMonitor';

// Smooth interaction components
export * from './SmoothTransition';
export * from './InteractiveFeedback';
// SmoothScroll 模块内导出名为 *Container / *Button / Parallax，此处别名以保持对外 API
export {
  SmoothScrollContainer as SmoothScroll,
  InfiniteScroll as SmoothInfiniteScroll,
  ScrollToTopButton as ScrollToTop,
  ScrollProgress,
  Parallax as ParallaxScroll,
} from './SmoothScroll';

// Responsive design components
export * from './ResponsiveContainer';
export * from './ResponsiveGrid';
export * from './ResponsiveText';
export * from './ResponsiveImage';
export * from './ResponsiveTable';

// Accessibility components
export * from './Accessibility';

// Error handling components
export * from './ErrorHandling';

// Design system components
export * from './DesignSystem';

// Composable reusable components (includes InfiniteScroll)
export * from './Composable';
