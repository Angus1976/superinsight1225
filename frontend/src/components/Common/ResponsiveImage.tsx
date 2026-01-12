/**
 * ResponsiveImage Component
 * 
 * An image component that adapts its size and loading behavior
 * based on viewport size and network conditions.
 */

import { memo, useState, useEffect, useRef, CSSProperties, ImgHTMLAttributes } from 'react';
import { Skeleton } from 'antd';
import { useResponsive } from '@/hooks/useResponsive';
import styles from './ResponsiveImage.module.scss';

type ObjectFit = 'contain' | 'cover' | 'fill' | 'none' | 'scale-down';
type AspectRatio = '1:1' | '4:3' | '16:9' | '21:9' | 'auto';

interface ResponsiveImageProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  // Image sources for different breakpoints
  src: string;
  srcMobile?: string;
  srcTablet?: string;
  srcDesktop?: string;
  
  // Alt text (required for accessibility)
  alt: string;
  
  // Sizing
  width?: number | string;
  height?: number | string;
  aspectRatio?: AspectRatio;
  objectFit?: ObjectFit;
  
  // Loading behavior
  lazy?: boolean;
  placeholder?: 'blur' | 'skeleton' | 'none';
  blurDataURL?: string;
  
  // Fallback
  fallback?: string;
  
  // Styling
  className?: string;
  style?: CSSProperties;
  rounded?: boolean | 'sm' | 'md' | 'lg' | 'full';
  
  // Events
  onLoad?: () => void;
  onError?: () => void;
}

const ASPECT_RATIOS: Record<AspectRatio, number | null> = {
  '1:1': 1,
  '4:3': 4 / 3,
  '16:9': 16 / 9,
  '21:9': 21 / 9,
  'auto': null,
};

const BORDER_RADIUS: Record<string, string> = {
  sm: '4px',
  md: '8px',
  lg: '12px',
  full: '50%',
};

export const ResponsiveImage = memo<ResponsiveImageProps>(({
  src,
  srcMobile,
  srcTablet,
  srcDesktop,
  alt,
  width,
  height,
  aspectRatio = 'auto',
  objectFit = 'cover',
  lazy = true,
  placeholder = 'skeleton',
  blurDataURL,
  fallback = '/images/placeholder.png',
  className,
  style,
  rounded = false,
  onLoad,
  onError,
  ...imgProps
}) => {
  const { isMobile, isTablet } = useResponsive();
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isInView, setIsInView] = useState(!lazy);
  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Determine the appropriate image source
  const imageSrc = isMobile && srcMobile
    ? srcMobile
    : isTablet && srcTablet
      ? srcTablet
      : srcDesktop || src;

  // Intersection Observer for lazy loading
  useEffect(() => {
    if (!lazy || isInView) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInView(true);
            observer.disconnect();
          }
        });
      },
      {
        rootMargin: '50px',
        threshold: 0.01,
      }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, [lazy, isInView]);

  // Handle image load
  const handleLoad = () => {
    setIsLoaded(true);
    onLoad?.();
  };

  // Handle image error
  const handleError = () => {
    setHasError(true);
    onError?.();
  };

  // Calculate aspect ratio padding
  const aspectRatioValue = ASPECT_RATIOS[aspectRatio];
  const paddingBottom = aspectRatioValue 
    ? `${(1 / aspectRatioValue) * 100}%` 
    : undefined;

  // Determine border radius
  const borderRadius = rounded === true 
    ? BORDER_RADIUS.md 
    : rounded 
      ? BORDER_RADIUS[rounded] 
      : undefined;

  const containerStyle: CSSProperties = {
    width,
    height: aspectRatioValue ? undefined : height,
    paddingBottom: aspectRatioValue ? paddingBottom : undefined,
    borderRadius,
    ...style,
  };

  const imgStyle: CSSProperties = {
    objectFit,
    borderRadius,
  };

  const containerClasses = [
    styles.responsiveImage,
    aspectRatioValue && styles.hasAspectRatio,
    isLoaded && styles.loaded,
    className,
  ].filter(Boolean).join(' ');

  return (
    <div 
      ref={containerRef}
      className={containerClasses}
      style={containerStyle}
    >
      {/* Placeholder */}
      {placeholder === 'skeleton' && !isLoaded && !hasError && (
        <div className={styles.placeholder}>
          <Skeleton.Image active style={{ width: '100%', height: '100%' }} />
        </div>
      )}
      
      {placeholder === 'blur' && blurDataURL && !isLoaded && !hasError && (
        <img
          src={blurDataURL}
          alt=""
          className={styles.blurPlaceholder}
          style={imgStyle}
          aria-hidden="true"
        />
      )}

      {/* Actual image */}
      {isInView && (
        <img
          ref={imgRef}
          src={hasError ? fallback : imageSrc}
          alt={alt}
          className={`${styles.image} ${isLoaded ? styles.visible : ''}`}
          style={imgStyle}
          onLoad={handleLoad}
          onError={handleError}
          loading={lazy ? 'lazy' : 'eager'}
          decoding="async"
          {...imgProps}
        />
      )}
    </div>
  );
});

ResponsiveImage.displayName = 'ResponsiveImage';

export default ResponsiveImage;
