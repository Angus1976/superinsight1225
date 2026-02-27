/**
 * LogoFull Component
 * LogoIcon + "问视间 SuperInsight" 文字组合
 *
 * 内联 SVG，支持 CSS 变量主题切换（light/dark）
 * showText 控制文字显示，渲染失败时回退到 "问" Avatar
 */

import React, { Component } from 'react';
import { Avatar } from 'antd';
import { LogoIcon } from './LogoIcon';

export interface LogoFullProps {
  height?: number;
  showText?: boolean;
  className?: string;
}

/** Error boundary for render failures */
class LogoFullErrorBoundary extends Component<
  { height: number; children: React.ReactNode },
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
          size={this.props.height}
          style={{
            background: 'linear-gradient(135deg, var(--brand-primary, #1890ff), var(--brand-accent, #722ed1))',
            fontSize: this.props.height * 0.5,
          }}
        >
          问
        </Avatar>
      );
    }
    return this.props.children;
  }
}

const LogoFullInner: React.FC<LogoFullProps> = ({
  height = 28,
  showText = true,
  className,
}) => {
  return (
    <div
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: showText ? 8 : 0,
        height,
      }}
    >
      <LogoIcon size={height} />
      {showText && (
        <span
          style={{
            fontSize: height * 0.5,
            fontWeight: 600,
            lineHeight: 1,
            color: 'var(--brand-text, rgba(0, 0, 0, 0.88))',
            whiteSpace: 'nowrap',
            userSelect: 'none',
          }}
        >
          <span>问视间</span>
          <span
            style={{
              marginLeft: 4,
              fontWeight: 400,
              opacity: 0.75,
            }}
          >
            SuperInsight
          </span>
        </span>
      )}
    </div>
  );
};

export const LogoFull: React.FC<LogoFullProps> = (props) => {
  const height = props.height ?? 28;
  return (
    <LogoFullErrorBoundary height={height}>
      <LogoFullInner {...props} />
    </LogoFullErrorBoundary>
  );
};

export default LogoFull;
