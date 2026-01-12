/**
 * SmoothTransition Component
 * 
 * Provides smooth page and content transitions for a natural
 * and fluid user experience.
 */

import { memo, ReactNode, useEffect, useState, useRef } from 'react';
import { useReducedMotion } from '@/hooks/useInteraction';

// ============================================
// Types
// ============================================

type TransitionType = 
  | 'fade' 
  | 'slide-up' 
  | 'slide-down' 
  | 'slide-left' 
  | 'slide-right'
  | 'scale'
  | 'scale-fade';

interface SmoothTransitionProps {
  children: ReactNode;
  show?: boolean;
  type?: TransitionType;
  duration?: number;
  delay?: number;
  className?: string;
  onEnter?: () => void;
  onEntered?: () => void;
  onExit?: () => void;
  onExited?: () => void;
}

// ============================================
// Transition Styles
// ============================================

const getTransitionStyles = (type: TransitionType, duration: number) => {
  const baseTransition = `all ${duration}ms cubic-bezier(0.4, 0, 0.2, 1)`;
  
  const styles: Record<TransitionType, {
    entering: React.CSSProperties;
    entered: React.CSSProperties;
    exiting: React.CSSProperties;
    exited: React.CSSProperties;
  }> = {
    fade: {
      entering: { opacity: 0, transition: baseTransition },
      entered: { opacity: 1, transition: baseTransition },
      exiting: { opacity: 0, transition: baseTransition },
      exited: { opacity: 0, display: 'none' },
    },
    'slide-up': {
      entering: { opacity: 0, transform: 'translateY(20px)', transition: baseTransition },
      entered: { opacity: 1, transform: 'translateY(0)', transition: baseTransition },
      exiting: { opacity: 0, transform: 'translateY(-10px)', transition: baseTransition },
      exited: { opacity: 0, transform: 'translateY(-10px)', display: 'none' },
    },
    'slide-down': {
      entering: { opacity: 0, transform: 'translateY(-20px)', transition: baseTransition },
      entered: { opacity: 1, transform: 'translateY(0)', transition: baseTransition },
      exiting: { opacity: 0, transform: 'translateY(10px)', transition: baseTransition },
      exited: { opacity: 0, transform: 'translateY(10px)', display: 'none' },
    },
    'slide-left': {
      entering: { opacity: 0, transform: 'translateX(20px)', transition: baseTransition },
      entered: { opacity: 1, transform: 'translateX(0)', transition: baseTransition },
      exiting: { opacity: 0, transform: 'translateX(-20px)', transition: baseTransition },
      exited: { opacity: 0, transform: 'translateX(-20px)', display: 'none' },
    },
    'slide-right': {
      entering: { opacity: 0, transform: 'translateX(-20px)', transition: baseTransition },
      entered: { opacity: 1, transform: 'translateX(0)', transition: baseTransition },
      exiting: { opacity: 0, transform: 'translateX(20px)', transition: baseTransition },
      exited: { opacity: 0, transform: 'translateX(20px)', display: 'none' },
    },
    scale: {
      entering: { opacity: 0, transform: 'scale(0.95)', transition: baseTransition },
      entered: { opacity: 1, transform: 'scale(1)', transition: baseTransition },
      exiting: { opacity: 0, transform: 'scale(0.95)', transition: baseTransition },
      exited: { opacity: 0, transform: 'scale(0.95)', display: 'none' },
    },
    'scale-fade': {
      entering: { opacity: 0, transform: 'scale(0.9)', transition: baseTransition },
      entered: { opacity: 1, transform: 'scale(1)', transition: baseTransition },
      exiting: { opacity: 0, transform: 'scale(1.05)', transition: baseTransition },
      exited: { opacity: 0, transform: 'scale(1.05)', display: 'none' },
    },
  };

  return styles[type];
};

// ============================================
// SmoothTransition Component
// ============================================

export const SmoothTransition = memo<SmoothTransitionProps>(({
  children,
  show = true,
  type = 'fade',
  duration = 250,
  delay = 0,
  className,
  onEnter,
  onEntered,
  onExit,
  onExited,
}) => {
  const prefersReducedMotion = useReducedMotion();
  const [state, setState] = useState<'entering' | 'entered' | 'exiting' | 'exited'>(
    show ? 'entered' : 'exited'
  );
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Use instant transitions if user prefers reduced motion
  const actualDuration = prefersReducedMotion ? 0 : duration;

  useEffect(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    if (show) {
      setState('entering');
      onEnter?.();
      
      timeoutRef.current = setTimeout(() => {
        setState('entered');
        onEntered?.();
      }, actualDuration + delay);
    } else {
      setState('exiting');
      onExit?.();
      
      timeoutRef.current = setTimeout(() => {
        setState('exited');
        onExited?.();
      }, actualDuration);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [show, actualDuration, delay, onEnter, onEntered, onExit, onExited]);

  const styles = getTransitionStyles(type, actualDuration);
  const currentStyle = styles[state];

  if (state === 'exited' && !show) {
    return null;
  }

  return (
    <div 
      className={className}
      style={{
        ...currentStyle,
        transitionDelay: state === 'entering' ? `${delay}ms` : '0ms',
      }}
    >
      {children}
    </div>
  );
});

SmoothTransition.displayName = 'SmoothTransition';

// ============================================
// FadeIn Component
// ============================================

interface FadeInProps {
  children: ReactNode;
  delay?: number;
  duration?: number;
  className?: string;
}

export const FadeIn = memo<FadeInProps>(({ 
  children, 
  delay = 0, 
  duration = 250,
  className 
}) => {
  return (
    <SmoothTransition 
      show={true} 
      type="fade" 
      delay={delay} 
      duration={duration}
      className={className}
    >
      {children}
    </SmoothTransition>
  );
});

FadeIn.displayName = 'FadeIn';

// ============================================
// SlideIn Component
// ============================================

interface SlideInProps {
  children: ReactNode;
  direction?: 'up' | 'down' | 'left' | 'right';
  delay?: number;
  duration?: number;
  className?: string;
}

export const SlideIn = memo<SlideInProps>(({ 
  children, 
  direction = 'up',
  delay = 0, 
  duration = 250,
  className 
}) => {
  const typeMap: Record<string, TransitionType> = {
    up: 'slide-up',
    down: 'slide-down',
    left: 'slide-left',
    right: 'slide-right',
  };

  return (
    <SmoothTransition 
      show={true} 
      type={typeMap[direction]} 
      delay={delay} 
      duration={duration}
      className={className}
    >
      {children}
    </SmoothTransition>
  );
});

SlideIn.displayName = 'SlideIn';

// ============================================
// ScaleIn Component
// ============================================

interface ScaleInProps {
  children: ReactNode;
  delay?: number;
  duration?: number;
  className?: string;
}

export const ScaleIn = memo<ScaleInProps>(({ 
  children, 
  delay = 0, 
  duration = 250,
  className 
}) => {
  return (
    <SmoothTransition 
      show={true} 
      type="scale-fade" 
      delay={delay} 
      duration={duration}
      className={className}
    >
      {children}
    </SmoothTransition>
  );
});

ScaleIn.displayName = 'ScaleIn';

// ============================================
// StaggeredList Component
// ============================================

interface StaggeredListProps {
  children: ReactNode[];
  staggerDelay?: number;
  initialDelay?: number;
  type?: TransitionType;
  duration?: number;
  className?: string;
  itemClassName?: string;
}

export const StaggeredList = memo<StaggeredListProps>(({
  children,
  staggerDelay = 50,
  initialDelay = 0,
  type = 'slide-up',
  duration = 250,
  className,
  itemClassName,
}) => {
  return (
    <div className={className}>
      {children.map((child, index) => (
        <SmoothTransition
          key={index}
          show={true}
          type={type}
          delay={initialDelay + (index * staggerDelay)}
          duration={duration}
          className={itemClassName}
        >
          {child}
        </SmoothTransition>
      ))}
    </div>
  );
});

StaggeredList.displayName = 'StaggeredList';

// ============================================
// AnimatedPresence Component
// ============================================

interface AnimatedPresenceProps {
  children: ReactNode;
  isPresent: boolean;
  type?: TransitionType;
  duration?: number;
  className?: string;
}

export const AnimatedPresence = memo<AnimatedPresenceProps>(({
  children,
  isPresent,
  type = 'fade',
  duration = 250,
  className,
}) => {
  const [shouldRender, setShouldRender] = useState(isPresent);

  useEffect(() => {
    if (isPresent) {
      setShouldRender(true);
    }
  }, [isPresent]);

  const handleExited = () => {
    if (!isPresent) {
      setShouldRender(false);
    }
  };

  if (!shouldRender) {
    return null;
  }

  return (
    <SmoothTransition
      show={isPresent}
      type={type}
      duration={duration}
      className={className}
      onExited={handleExited}
    >
      {children}
    </SmoothTransition>
  );
});

AnimatedPresence.displayName = 'AnimatedPresence';

// ============================================
// PageTransition Component
// ============================================

interface PageTransitionProps {
  children: ReactNode;
  className?: string;
}

export const PageTransition = memo<PageTransitionProps>(({ 
  children,
  className 
}) => {
  return (
    <SmoothTransition
      show={true}
      type="slide-up"
      duration={300}
      className={className}
    >
      {children}
    </SmoothTransition>
  );
});

PageTransition.displayName = 'PageTransition';
