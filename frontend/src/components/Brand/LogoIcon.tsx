/**
 * LogoIcon Component
 * 圆形渐变背景 + W 形 SVG Logo
 *
 * 内联 SVG，支持 CSS 变量主题切换（light/dark）
 * 渲染失败时回退到 "问" Avatar
 */

import React, { Component } from 'react';
import { Avatar } from 'antd';

export interface LogoIconProps {
  size?: number;
  className?: string;
}

/** Error boundary for SVG render failures */
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

const LogoIconSVG: React.FC<LogoIconProps> = ({ size = 32, className }) => {
  const gradientId = `logo-gradient-${size}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="问视间 SuperInsight Logo"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="var(--brand-primary, #1890ff)" />
          <stop offset="100%" stopColor="var(--brand-accent, #722ed1)" />
        </linearGradient>
      </defs>
      {/* Circular background */}
      <circle cx="16" cy="16" r="16" fill={`url(#${gradientId})`} />
      {/* W shape */}
      <path
        d="M8 11L11.2 22L16 15L20.8 22L24 11"
        stroke="#ffffff"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
};

export const LogoIcon: React.FC<LogoIconProps> = (props) => {
  const size = props.size ?? 32;
  return (
    <LogoIconErrorBoundary size={size}>
      <LogoIconSVG {...props} />
    </LogoIconErrorBoundary>
  );
};

export default LogoIcon;
