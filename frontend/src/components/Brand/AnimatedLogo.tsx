/**
 * AnimatedLogo Component
 * 动画LOGO组件
 * 
 * 功能：
 * - 微妙的动画效果
 * - 多种动画模式
 * - 可访问性支持
 * - 性能优化
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useBrandTheme } from '@/hooks/useBrandTheme';
import { useBrandTracking } from '@/hooks/useBrandAnalytics';
import { BrandLocation, LogoVariant } from '@/types/brand';
import styles from './AnimatedLogo.module.scss';

export type AnimationType = 
  | 'none'           // 无动画
  | 'pulse'          // 脉冲
  | 'breathe'        // 呼吸
  | 'glow'           // 发光
  | 'float'          // 漂浮
  | 'spin'           // 旋转（加载时）
  | 'bounce'         // 弹跳
  | 'shimmer';       // 闪烁

export interface AnimatedLogoProps {
  variant?: LogoVariant;
  size?: number | { width: number; height: number };
  animation?: AnimationType;
  animationDuration?: number;  // 毫秒
  animationDelay?: number;     // 毫秒
  pauseOnHover?: boolean;
  reducedMotion?: boolean;     // 减少动画（可访问性）
  location?: BrandLocation;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
  onLoad?: () => void;
  onError?: () => void;
}

export const AnimatedLogo: React.FC<AnimatedLogoProps> = ({
  variant = LogoVariant.STANDARD,
  size,
  animation = 'none',
  animationDuration = 2000,
  animationDelay = 0,
  pauseOnHover = false,
  reducedMotion = false,
  location = BrandLocation.NAVIGATION,
  className,
  style,
  onClick,
  onLoad,
  onError
}) => {
  const { getLogoPath, brandName } = useBrandTheme();
  const { trackImpression, trackInteraction } = useBrandTracking();
  const [isHovered, setIsHovered] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  // 检测系统减少动画偏好
  const prefersReducedMotion = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }, []);

  // 最终是否启用动画
  const shouldAnimate = !reducedMotion && !prefersReducedMotion && animation !== 'none';

  // 计算尺寸
  const dimensions = useMemo(() => {
    if (typeof size === 'number') {
      return { width: size, height: size };
    }
    if (size) {
      return size;
    }
    // 默认尺寸基于变体
    const defaultSizes: Record<LogoVariant, { width: number; height: number }> = {
      [LogoVariant.STANDARD]: { width: 120, height: 120 },
      [LogoVariant.SIMPLE]: { width: 64, height: 64 },
      [LogoVariant.FULL]: { width: 280, height: 80 },
      [LogoVariant.FAVICON]: { width: 32, height: 32 }
    };
    return defaultSizes[variant];
  }, [size, variant]);

  // 动画样式
  const animationStyle = useMemo((): React.CSSProperties => {
    if (!shouldAnimate) return {};

    const isPaused = pauseOnHover && isHovered;
    
    return {
      animationDuration: `${animationDuration}ms`,
      animationDelay: `${animationDelay}ms`,
      animationPlayState: isPaused ? 'paused' : 'running'
    };
  }, [shouldAnimate, animationDuration, animationDelay, pauseOnHover, isHovered]);

  // 获取动画类名
  const animationClassName = useMemo(() => {
    if (!shouldAnimate) return '';
    return styles[`animation-${animation}`] || '';
  }, [shouldAnimate, animation]);

  // 处理加载完成
  const handleLoad = useCallback(() => {
    setIsLoaded(true);
    setHasError(false);
    trackImpression(location);
    onLoad?.();
  }, [location, trackImpression, onLoad]);

  // 处理加载错误
  const handleError = useCallback(() => {
    setHasError(true);
    onError?.();
  }, [onError]);

  // 处理点击
  const handleClick = useCallback(() => {
    trackInteraction('click', location);
    onClick?.();
  }, [location, trackInteraction, onClick]);

  // 处理鼠标进入
  const handleMouseEnter = useCallback(() => {
    setIsHovered(true);
    trackInteraction('hover', location);
  }, [location, trackInteraction]);

  // 处理鼠标离开
  const handleMouseLeave = useCallback(() => {
    setIsHovered(false);
  }, []);

  // 组合类名
  const combinedClassName = useMemo(() => {
    const classes = [styles.animatedLogo];
    if (animationClassName) classes.push(animationClassName);
    if (isLoaded) classes.push(styles.loaded);
    if (hasError) classes.push(styles.error);
    if (className) classes.push(className);
    return classes.join(' ');
  }, [animationClassName, isLoaded, hasError, className]);

  // 组合样式
  const combinedStyle = useMemo((): React.CSSProperties => ({
    width: dimensions.width,
    height: dimensions.height,
    ...animationStyle,
    ...style
  }), [dimensions, animationStyle, style]);

  const logoPath = getLogoPath(variant);

  return (
    <div
      className={combinedClassName}
      style={combinedStyle}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      role={onClick ? 'button' : 'img'}
      tabIndex={onClick ? 0 : undefined}
      aria-label={brandName}
    >
      {!hasError ? (
        <img
          src={logoPath}
          alt={brandName}
          width={dimensions.width}
          height={dimensions.height}
          onLoad={handleLoad}
          onError={handleError}
          className={styles.logoImage}
          loading="eager"
          decoding="async"
        />
      ) : (
        <div className={styles.fallback} aria-label={brandName}>
          {brandName.charAt(0)}
        </div>
      )}
    </div>
  );
};

/**
 * 预设动画LOGO组件
 */
export const PulseLogo: React.FC<Omit<AnimatedLogoProps, 'animation'>> = (props) => (
  <AnimatedLogo {...props} animation="pulse" />
);

export const BreatheLogo: React.FC<Omit<AnimatedLogoProps, 'animation'>> = (props) => (
  <AnimatedLogo {...props} animation="breathe" />
);

export const GlowLogo: React.FC<Omit<AnimatedLogoProps, 'animation'>> = (props) => (
  <AnimatedLogo {...props} animation="glow" />
);

export const FloatLogo: React.FC<Omit<AnimatedLogoProps, 'animation'>> = (props) => (
  <AnimatedLogo {...props} animation="float" />
);

export const SpinLogo: React.FC<Omit<AnimatedLogoProps, 'animation'>> = (props) => (
  <AnimatedLogo {...props} animation="spin" />
);

export const LoadingLogo: React.FC<Omit<AnimatedLogoProps, 'animation' | 'variant'>> = (props) => (
  <AnimatedLogo 
    {...props} 
    animation="spin" 
    variant={LogoVariant.SIMPLE}
    animationDuration={1000}
  />
);

export default AnimatedLogo;
