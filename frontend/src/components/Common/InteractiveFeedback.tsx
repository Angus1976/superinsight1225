/**
 * InteractiveFeedback Components
 * 
 * Provides visual feedback for user interactions including
 * ripple effects, press states, and hover animations.
 */

import { memo, ReactNode, useState, useRef, useCallback, CSSProperties } from 'react';
import { useReducedMotion, usePressState, useHoverState } from '@/hooks/useInteraction';

// ============================================
// Types
// ============================================

interface RippleProps {
  color?: string;
  duration?: number;
  children: ReactNode;
  className?: string;
  disabled?: boolean;
}

interface PressableProps {
  children: ReactNode;
  className?: string;
  scale?: number;
  disabled?: boolean;
  onClick?: () => void;
}

interface HoverScaleProps {
  children: ReactNode;
  className?: string;
  scale?: number;
  disabled?: boolean;
}

interface HoverLiftProps {
  children: ReactNode;
  className?: string;
  lift?: number;
  shadow?: boolean;
  disabled?: boolean;
}

// ============================================
// Ripple Effect Component
// ============================================

interface RippleState {
  x: number;
  y: number;
  size: number;
  id: number;
}

export const Ripple = memo<RippleProps>(({
  color = 'rgba(255, 255, 255, 0.3)',
  duration = 600,
  children,
  className,
  disabled = false,
}) => {
  const prefersReducedMotion = useReducedMotion();
  const [ripples, setRipples] = useState<RippleState[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const rippleIdRef = useRef(0);

  const createRipple = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (disabled || prefersReducedMotion) return;

    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    let clientX: number, clientY: number;

    if ('touches' in e) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
    }

    const x = clientX - rect.left;
    const y = clientY - rect.top;
    const size = Math.max(rect.width, rect.height) * 2;
    const id = rippleIdRef.current++;

    setRipples(prev => [...prev, { x, y, size, id }]);

    setTimeout(() => {
      setRipples(prev => prev.filter(r => r.id !== id));
    }, duration);
  }, [disabled, prefersReducedMotion, duration]);

  const containerStyle: CSSProperties = {
    position: 'relative',
    overflow: 'hidden',
    display: 'inline-block',
  };

  const rippleStyle = (ripple: RippleState): CSSProperties => ({
    position: 'absolute',
    left: ripple.x - ripple.size / 2,
    top: ripple.y - ripple.size / 2,
    width: ripple.size,
    height: ripple.size,
    borderRadius: '50%',
    backgroundColor: color,
    transform: 'scale(0)',
    animation: `ripple-effect ${duration}ms ease-out forwards`,
    pointerEvents: 'none',
  });

  return (
    <div
      ref={containerRef}
      className={className}
      style={containerStyle}
      onMouseDown={createRipple}
      onTouchStart={createRipple}
    >
      {children}
      {ripples.map(ripple => (
        <span key={ripple.id} style={rippleStyle(ripple)} />
      ))}
      <style>{`
        @keyframes ripple-effect {
          0% {
            transform: scale(0);
            opacity: 1;
          }
          100% {
            transform: scale(1);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
});

Ripple.displayName = 'Ripple';

// ============================================
// Pressable Component
// ============================================

export const Pressable = memo<PressableProps>(({
  children,
  className,
  scale = 0.97,
  disabled = false,
  onClick,
}) => {
  const prefersReducedMotion = useReducedMotion();
  const { isPressed, pressProps } = usePressState();

  const style: CSSProperties = {
    transform: isPressed && !disabled && !prefersReducedMotion 
      ? `scale(${scale})` 
      : 'scale(1)',
    transition: 'transform 150ms cubic-bezier(0.4, 0, 0.2, 1)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    userSelect: 'none',
  };

  return (
    <div
      className={className}
      style={style}
      onClick={disabled ? undefined : onClick}
      {...pressProps}
    >
      {children}
    </div>
  );
});

Pressable.displayName = 'Pressable';

// ============================================
// HoverScale Component
// ============================================

export const HoverScale = memo<HoverScaleProps>(({
  children,
  className,
  scale = 1.02,
  disabled = false,
}) => {
  const prefersReducedMotion = useReducedMotion();
  const { isHovered, hoverProps } = useHoverState();

  const style: CSSProperties = {
    transform: isHovered && !disabled && !prefersReducedMotion 
      ? `scale(${scale})` 
      : 'scale(1)',
    transition: 'transform 200ms cubic-bezier(0.4, 0, 0.2, 1)',
  };

  return (
    <div
      className={className}
      style={style}
      {...hoverProps}
    >
      {children}
    </div>
  );
});

HoverScale.displayName = 'HoverScale';

// ============================================
// HoverLift Component
// ============================================

export const HoverLift = memo<HoverLiftProps>(({
  children,
  className,
  lift = 4,
  shadow = true,
  disabled = false,
}) => {
  const prefersReducedMotion = useReducedMotion();
  const { isHovered, hoverProps } = useHoverState();

  const isActive = isHovered && !disabled && !prefersReducedMotion;

  const style: CSSProperties = {
    transform: isActive ? `translateY(-${lift}px)` : 'translateY(0)',
    boxShadow: isActive && shadow 
      ? `0 ${lift * 2}px ${lift * 4}px rgba(0, 0, 0, 0.1)` 
      : 'none',
    transition: 'transform 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1)',
  };

  return (
    <div
      className={className}
      style={style}
      {...hoverProps}
    >
      {children}
    </div>
  );
});

HoverLift.displayName = 'HoverLift';

// ============================================
// PulseOnHover Component
// ============================================

interface PulseOnHoverProps {
  children: ReactNode;
  className?: string;
  disabled?: boolean;
}

export const PulseOnHover = memo<PulseOnHoverProps>(({
  children,
  className,
  disabled = false,
}) => {
  const prefersReducedMotion = useReducedMotion();
  const { isHovered, hoverProps } = useHoverState();

  const style: CSSProperties = {
    animation: isHovered && !disabled && !prefersReducedMotion 
      ? 'pulse-hover 1s ease-in-out infinite' 
      : 'none',
  };

  return (
    <div
      className={className}
      style={style}
      {...hoverProps}
    >
      {children}
      <style>{`
        @keyframes pulse-hover {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.9;
            transform: scale(1.01);
          }
        }
      `}</style>
    </div>
  );
});

PulseOnHover.displayName = 'PulseOnHover';

// ============================================
// ShakeOnError Component
// ============================================

interface ShakeOnErrorProps {
  children: ReactNode;
  className?: string;
  shake: boolean;
  onShakeEnd?: () => void;
}

export const ShakeOnError = memo<ShakeOnErrorProps>(({
  children,
  className,
  shake,
  onShakeEnd,
}) => {
  const prefersReducedMotion = useReducedMotion();
  const [isShaking, setIsShaking] = useState(false);

  // Trigger shake animation
  if (shake && !isShaking && !prefersReducedMotion) {
    setIsShaking(true);
    setTimeout(() => {
      setIsShaking(false);
      onShakeEnd?.();
    }, 500);
  }

  const style: CSSProperties = {
    animation: isShaking ? 'shake-error 0.5s ease-in-out' : 'none',
  };

  return (
    <div className={className} style={style}>
      {children}
      <style>{`
        @keyframes shake-error {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-4px); }
          20%, 40%, 60%, 80% { transform: translateX(4px); }
        }
      `}</style>
    </div>
  );
});

ShakeOnError.displayName = 'ShakeOnError';

// ============================================
// BounceOnClick Component
// ============================================

interface BounceOnClickProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
}

export const BounceOnClick = memo<BounceOnClickProps>(({
  children,
  className,
  onClick,
  disabled = false,
}) => {
  const prefersReducedMotion = useReducedMotion();
  const [isBouncing, setIsBouncing] = useState(false);

  const handleClick = useCallback(() => {
    if (disabled) return;
    
    if (!prefersReducedMotion) {
      setIsBouncing(true);
      setTimeout(() => setIsBouncing(false), 300);
    }
    
    onClick?.();
  }, [disabled, prefersReducedMotion, onClick]);

  const style: CSSProperties = {
    animation: isBouncing ? 'bounce-click 0.3s ease-out' : 'none',
    cursor: disabled ? 'not-allowed' : 'pointer',
  };

  return (
    <div className={className} style={style} onClick={handleClick}>
      {children}
      <style>{`
        @keyframes bounce-click {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.05); }
        }
      `}</style>
    </div>
  );
});

BounceOnClick.displayName = 'BounceOnClick';

// ============================================
// GlowOnFocus Component
// ============================================

interface GlowOnFocusProps {
  children: ReactNode;
  className?: string;
  color?: string;
}

export const GlowOnFocus = memo<GlowOnFocusProps>(({
  children,
  className,
  color = '#1890ff',
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const prefersReducedMotion = useReducedMotion();

  const style: CSSProperties = {
    animation: isFocused && !prefersReducedMotion 
      ? 'glow-focus 1.5s ease-in-out infinite' 
      : 'none',
    '--glow-color': color,
  } as CSSProperties;

  return (
    <div
      className={className}
      style={style}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      tabIndex={0}
    >
      {children}
      <style>{`
        @keyframes glow-focus {
          0%, 100% {
            box-shadow: 0 0 0 0 var(--glow-color, rgba(24, 144, 255, 0.4));
          }
          50% {
            box-shadow: 0 0 0 8px transparent;
          }
        }
      `}</style>
    </div>
  );
});

GlowOnFocus.displayName = 'GlowOnFocus';

// ============================================
// SuccessCheckmark Component
// ============================================

interface SuccessCheckmarkProps {
  show: boolean;
  size?: number;
  color?: string;
  className?: string;
}

export const SuccessCheckmark = memo<SuccessCheckmarkProps>(({
  show,
  size = 48,
  color = '#52c41a',
  className,
}) => {
  const prefersReducedMotion = useReducedMotion();

  if (!show) return null;

  const style: CSSProperties = {
    width: size,
    height: size,
  };

  return (
    <div className={className} style={style}>
      <svg viewBox="0 0 52 52" style={{ width: '100%', height: '100%' }}>
        <circle
          cx="26"
          cy="26"
          r="25"
          fill="none"
          stroke={color}
          strokeWidth="2"
          style={{
            strokeDasharray: 166,
            strokeDashoffset: prefersReducedMotion ? 0 : 166,
            animation: prefersReducedMotion ? 'none' : 'circle-draw 0.6s ease-out forwards',
          }}
        />
        <path
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M14.1 27.2l7.1 7.2 16.7-16.8"
          style={{
            strokeDasharray: 48,
            strokeDashoffset: prefersReducedMotion ? 0 : 48,
            animation: prefersReducedMotion ? 'none' : 'check-draw 0.3s ease-out 0.6s forwards',
          }}
        />
      </svg>
      <style>{`
        @keyframes circle-draw {
          to { stroke-dashoffset: 0; }
        }
        @keyframes check-draw {
          to { stroke-dashoffset: 0; }
        }
      `}</style>
    </div>
  );
});

SuccessCheckmark.displayName = 'SuccessCheckmark';

// ============================================
// LoadingDots Component
// ============================================

interface LoadingDotsProps {
  size?: number;
  color?: string;
  className?: string;
}

export const LoadingDots = memo<LoadingDotsProps>(({
  size = 8,
  color = '#1890ff',
  className,
}) => {
  const prefersReducedMotion = useReducedMotion();

  const dotStyle = (delay: number): CSSProperties => ({
    width: size,
    height: size,
    borderRadius: '50%',
    backgroundColor: color,
    animation: prefersReducedMotion ? 'none' : `dot-bounce 1.4s ease-in-out ${delay}s infinite both`,
  });

  return (
    <div 
      className={className}
      style={{ display: 'flex', gap: size / 2, alignItems: 'center' }}
    >
      <span style={dotStyle(0)} />
      <span style={dotStyle(0.16)} />
      <span style={dotStyle(0.32)} />
      <style>{`
        @keyframes dot-bounce {
          0%, 80%, 100% {
            transform: scale(0);
            opacity: 0.5;
          }
          40% {
            transform: scale(1);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
});

LoadingDots.displayName = 'LoadingDots';
