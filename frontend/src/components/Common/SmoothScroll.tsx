/**
 * SmoothScroll Components
 * 
 * Provides smooth scrolling behavior and scroll-triggered
 * animations for a natural user experience.
 */

import { 
  memo, 
  ReactNode, 
  useEffect, 
  useRef, 
  useState, 
  useCallback,
  createContext,
  useContext,
} from 'react';
import { useReducedMotion, useScrollReveal } from '@/hooks/useInteraction';

// ============================================
// Types
// ============================================

interface SmoothScrollContainerProps {
  children: ReactNode;
  className?: string;
  behavior?: 'smooth' | 'auto';
}

interface ScrollToTopButtonProps {
  threshold?: number;
  className?: string;
  icon?: ReactNode;
}

interface ScrollRevealProps {
  children: ReactNode;
  className?: string;
  threshold?: number;
  delay?: number;
  direction?: 'up' | 'down' | 'left' | 'right' | 'none';
}

interface ParallaxProps {
  children: ReactNode;
  className?: string;
  speed?: number;
  direction?: 'up' | 'down';
}

// ============================================
// Scroll Context
// ============================================

interface ScrollContextValue {
  scrollY: number;
  scrollDirection: 'up' | 'down' | null;
  isScrolling: boolean;
}

const ScrollContext = createContext<ScrollContextValue>({
  scrollY: 0,
  scrollDirection: null,
  isScrolling: false,
});

export const useScrollContext = () => useContext(ScrollContext);

// ============================================
// ScrollProvider Component
// ============================================

interface ScrollProviderProps {
  children: ReactNode;
}

export const ScrollProvider = memo<ScrollProviderProps>(({ children }) => {
  const [scrollY, setScrollY] = useState(0);
  const [scrollDirection, setScrollDirection] = useState<'up' | 'down' | null>(null);
  const [isScrolling, setIsScrolling] = useState(false);
  const lastScrollY = useRef(0);
  const scrollTimeout = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      
      setScrollY(currentScrollY);
      setIsScrolling(true);
      
      if (currentScrollY > lastScrollY.current) {
        setScrollDirection('down');
      } else if (currentScrollY < lastScrollY.current) {
        setScrollDirection('up');
      }
      
      lastScrollY.current = currentScrollY;

      // Clear existing timeout
      if (scrollTimeout.current) {
        clearTimeout(scrollTimeout.current);
      }

      // Set scrolling to false after scroll ends
      scrollTimeout.current = setTimeout(() => {
        setIsScrolling(false);
      }, 150);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (scrollTimeout.current) {
        clearTimeout(scrollTimeout.current);
      }
    };
  }, []);

  return (
    <ScrollContext.Provider value={{ scrollY, scrollDirection, isScrolling }}>
      {children}
    </ScrollContext.Provider>
  );
});

ScrollProvider.displayName = 'ScrollProvider';

// ============================================
// SmoothScrollContainer Component
// ============================================

export const SmoothScrollContainer = memo<SmoothScrollContainerProps>(({
  children,
  className,
  behavior = 'smooth',
}) => {
  const prefersReducedMotion = useReducedMotion();

  const style: React.CSSProperties = {
    scrollBehavior: prefersReducedMotion ? 'auto' : behavior,
    overflowY: 'auto',
    height: '100%',
  };

  return (
    <div className={className} style={style}>
      {children}
    </div>
  );
});

SmoothScrollContainer.displayName = 'SmoothScrollContainer';

// ============================================
// ScrollToTopButton Component
// ============================================

export const ScrollToTopButton = memo<ScrollToTopButtonProps>(({
  threshold = 300,
  className,
  icon,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    const handleScroll = () => {
      setIsVisible(window.scrollY > threshold);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [threshold]);

  const scrollToTop = useCallback(() => {
    window.scrollTo({
      top: 0,
      behavior: prefersReducedMotion ? 'auto' : 'smooth',
    });
  }, [prefersReducedMotion]);

  const buttonStyle: React.CSSProperties = {
    position: 'fixed',
    bottom: 24,
    right: 24,
    width: 44,
    height: 44,
    borderRadius: '50%',
    backgroundColor: '#1890ff',
    color: '#fff',
    border: 'none',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
    opacity: isVisible ? 1 : 0,
    transform: isVisible ? 'translateY(0)' : 'translateY(20px)',
    transition: prefersReducedMotion 
      ? 'none' 
      : 'opacity 0.3s ease, transform 0.3s ease',
    pointerEvents: isVisible ? 'auto' : 'none',
    zIndex: 1000,
  };

  const defaultIcon = (
    <svg 
      width="20" 
      height="20" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M18 15l-6-6-6 6" />
    </svg>
  );

  return (
    <button
      className={className}
      style={buttonStyle}
      onClick={scrollToTop}
      aria-label="Scroll to top"
    >
      {icon || defaultIcon}
    </button>
  );
});

ScrollToTopButton.displayName = 'ScrollToTopButton';

// ============================================
// ScrollReveal Component
// ============================================

export const ScrollReveal = memo<ScrollRevealProps>(({
  children,
  className,
  threshold = 0.1,
  delay = 0,
  direction = 'up',
}) => {
  const prefersReducedMotion = useReducedMotion();
  const { isVisible, elementRef } = useScrollReveal({ threshold });

  const getTransform = () => {
    if (prefersReducedMotion || isVisible) return 'translate(0, 0)';
    
    switch (direction) {
      case 'up': return 'translateY(30px)';
      case 'down': return 'translateY(-30px)';
      case 'left': return 'translateX(30px)';
      case 'right': return 'translateX(-30px)';
      case 'none': return 'translate(0, 0)';
      default: return 'translateY(30px)';
    }
  };

  const style: React.CSSProperties = {
    opacity: prefersReducedMotion ? 1 : (isVisible ? 1 : 0),
    transform: getTransform(),
    transition: prefersReducedMotion 
      ? 'none' 
      : `opacity 0.6s ease ${delay}ms, transform 0.6s ease ${delay}ms`,
  };

  return (
    <div 
      ref={elementRef as React.RefObject<HTMLDivElement>} 
      className={className} 
      style={style}
    >
      {children}
    </div>
  );
});

ScrollReveal.displayName = 'ScrollReveal';

// ============================================
// Parallax Component
// ============================================

export const Parallax = memo<ParallaxProps>(({
  children,
  className,
  speed = 0.5,
  direction = 'up',
}) => {
  const prefersReducedMotion = useReducedMotion();
  const [offset, setOffset] = useState(0);
  const elementRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prefersReducedMotion) return;

    const handleScroll = () => {
      if (!elementRef.current) return;

      const rect = elementRef.current.getBoundingClientRect();
      const windowHeight = window.innerHeight;
      
      // Calculate how far the element is from the center of the viewport
      const elementCenter = rect.top + rect.height / 2;
      const viewportCenter = windowHeight / 2;
      const distanceFromCenter = elementCenter - viewportCenter;
      
      // Apply parallax effect
      const parallaxOffset = distanceFromCenter * speed * (direction === 'up' ? -1 : 1);
      setOffset(parallaxOffset);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Initial calculation

    return () => window.removeEventListener('scroll', handleScroll);
  }, [speed, direction, prefersReducedMotion]);

  const style: React.CSSProperties = {
    transform: prefersReducedMotion ? 'none' : `translateY(${offset}px)`,
    willChange: 'transform',
  };

  return (
    <div ref={elementRef} className={className} style={style}>
      {children}
    </div>
  );
});

Parallax.displayName = 'Parallax';

// ============================================
// StickyHeader Component
// ============================================

interface StickyHeaderProps {
  children: ReactNode;
  className?: string;
  hideOnScroll?: boolean;
  threshold?: number;
}

export const StickyHeader = memo<StickyHeaderProps>(({
  children,
  className,
  hideOnScroll = false,
  threshold = 100,
}) => {
  const prefersReducedMotion = useReducedMotion();
  const [isHidden, setIsHidden] = useState(false);
  const [isSticky, setIsSticky] = useState(false);
  const lastScrollY = useRef(0);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;
      
      setIsSticky(currentScrollY > threshold);
      
      if (hideOnScroll) {
        if (currentScrollY > lastScrollY.current && currentScrollY > threshold) {
          setIsHidden(true);
        } else {
          setIsHidden(false);
        }
      }
      
      lastScrollY.current = currentScrollY;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [hideOnScroll, threshold]);

  const style: React.CSSProperties = {
    position: 'sticky',
    top: 0,
    zIndex: 100,
    transform: isHidden ? 'translateY(-100%)' : 'translateY(0)',
    transition: prefersReducedMotion ? 'none' : 'transform 0.3s ease, box-shadow 0.3s ease',
    boxShadow: isSticky ? '0 2px 8px rgba(0, 0, 0, 0.1)' : 'none',
  };

  return (
    <div className={className} style={style}>
      {children}
    </div>
  );
});

StickyHeader.displayName = 'StickyHeader';

// ============================================
// InfiniteScroll Component
// ============================================

interface InfiniteScrollProps {
  children: ReactNode;
  className?: string;
  onLoadMore: () => void;
  hasMore: boolean;
  loading?: boolean;
  threshold?: number;
  loader?: ReactNode;
}

export const InfiniteScroll = memo<InfiniteScrollProps>(({
  children,
  className,
  onLoadMore,
  hasMore,
  loading = false,
  threshold = 200,
  loader,
}) => {
  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (loading || !hasMore) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          onLoadMore();
        }
      },
      { rootMargin: `${threshold}px` }
    );

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current);
    }

    return () => {
      observerRef.current?.disconnect();
    };
  }, [onLoadMore, hasMore, loading, threshold]);

  const defaultLoader = (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      padding: '20px',
      color: '#999',
    }}>
      Loading...
    </div>
  );

  return (
    <div className={className}>
      {children}
      <div ref={loadMoreRef}>
        {loading && (loader || defaultLoader)}
      </div>
    </div>
  );
});

InfiniteScroll.displayName = 'InfiniteScroll';

// ============================================
// ScrollProgress Component
// ============================================

interface ScrollProgressProps {
  className?: string;
  color?: string;
  height?: number;
  position?: 'top' | 'bottom';
}

export const ScrollProgress = memo<ScrollProgressProps>(({
  className,
  color = '#1890ff',
  height = 3,
  position = 'top',
}) => {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const windowHeight = window.innerHeight;
      const documentHeight = document.documentElement.scrollHeight;
      const scrollTop = window.scrollY;
      const scrollableHeight = documentHeight - windowHeight;
      
      const currentProgress = scrollableHeight > 0 
        ? (scrollTop / scrollableHeight) * 100 
        : 0;
      
      setProgress(Math.min(100, Math.max(0, currentProgress)));
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Initial calculation

    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const style: React.CSSProperties = {
    position: 'fixed',
    [position]: 0,
    left: 0,
    width: `${progress}%`,
    height,
    backgroundColor: color,
    zIndex: 9999,
    transition: 'width 0.1s ease-out',
  };

  return <div className={className} style={style} />;
});

ScrollProgress.displayName = 'ScrollProgress';
