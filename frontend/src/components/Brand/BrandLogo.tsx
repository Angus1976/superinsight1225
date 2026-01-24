/**
 * BrandLogo Component
 * 品牌LOGO组件
 * 
 * 简化的LOGO组件，用于常规场景
 */

import React, { useCallback, useMemo } from 'react';
import { useBrandTheme } from '@/hooks/useBrandTheme';
import { useBrandTracking } from '@/hooks/useBrandAnalytics';
import { BrandLocation, LogoVariant } from '@/types/brand';

export interface BrandLogoProps {
  variant?: LogoVariant;
  size?: number | { width: number; height: number };
  location?: BrandLocation;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({
  variant = LogoVariant.STANDARD,
  size,
  location = BrandLocation.NAVIGATION,
  className,
  style,
  onClick
}) => {
  const { getLogoPath, brandName } = useBrandTheme();
  const { trackImpression, trackInteraction } = useBrandTracking();

  // 计算尺寸
  const dimensions = useMemo(() => {
    if (typeof size === 'number') {
      return { width: size, height: size };
    }
    if (size) {
      return size;
    }
    const defaultSizes: Record<LogoVariant, { width: number; height: number }> = {
      [LogoVariant.STANDARD]: { width: 120, height: 120 },
      [LogoVariant.SIMPLE]: { width: 64, height: 64 },
      [LogoVariant.FULL]: { width: 280, height: 80 },
      [LogoVariant.FAVICON]: { width: 32, height: 32 }
    };
    return defaultSizes[variant];
  }, [size, variant]);

  // 处理加载
  const handleLoad = useCallback(() => {
    trackImpression(location);
  }, [location, trackImpression]);

  // 处理点击
  const handleClick = useCallback(() => {
    if (onClick) {
      trackInteraction('click', location);
      onClick();
    }
  }, [location, trackInteraction, onClick]);

  const logoPath = getLogoPath(variant);

  return (
    <img
      src={logoPath}
      alt={brandName}
      width={dimensions.width}
      height={dimensions.height}
      className={className}
      style={{
        display: 'block',
        objectFit: 'contain',
        cursor: onClick ? 'pointer' : 'default',
        ...style
      }}
      onLoad={handleLoad}
      onClick={handleClick}
      loading="eager"
      decoding="async"
    />
  );
};

export default BrandLogo;
