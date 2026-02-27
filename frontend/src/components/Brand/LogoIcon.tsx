/**
 * LogoIcon Component
 * 使用新的问视间 LOGO 图片
 *
 * 根据尺寸自动选择合适的 LOGO 文件
 * 渲染失败时回退到 "问" Avatar
 */

import React, { Component, useState } from 'react';
import { Avatar } from 'antd';

export interface LogoIconProps {
  size?: number;
  className?: string;
}

/** Error boundary for image load failures */
class LogoIconErrorBoundary extends Component<
  { size: number; children: React.ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <Avatar
          size={this.props.size}
          style={{
            background: 'linear-gradient(135deg, var(--brand-primary, #1890ff), var(--brand-accent, #722ed1))',
            fontSize: this.props.size * 0.5,
          }}
        >
          问
        </Avatar>
      );
    }
    return this.props.children;
  }
}

const LogoIconImage: React.FC<LogoIconProps> = ({ size = 32, className }) => {
  const [imageError, setImageError] = useState(false);

  // 根据尺寸选择合适的 LOGO 文件
  const getLogoSrc = () => {
    if (size <= 48) {
      return '/logo-wenshijian-simple.svg'; // 简化版 64x64
    } else if (size <= 128) {
      return '/logo-wenshijian.svg'; // 标准版 128x128
    } else {
      return '/logo-wenshijian.svg'; // 大尺寸也用标准版
    }
  };

  if (imageError) {
    return (
      <Avatar
        size={size}
        style={{
          background: 'linear-gradient(135deg, var(--brand-primary, #1890ff), var(--brand-accent, #722ed1))',
          fontSize: size * 0.5,
        }}
      >
        问
      </Avatar>
    );
  }

  return (
    <img
      src={getLogoSrc()}
      alt="问视间 SuperInsight Logo"
      width={size}
      height={size}
      className={className}
      onError={() => setImageError(true)}
      style={{
        display: 'block',
        objectFit: 'contain',
      }}
    />
  );
};

export const LogoIcon: React.FC<LogoIconProps> = (props) => {
  const size = props.size ?? 32;
  return (
    <LogoIconErrorBoundary size={size}>
      <LogoIconImage {...props} />
    </LogoIconErrorBoundary>
  );
};

export default LogoIcon;
