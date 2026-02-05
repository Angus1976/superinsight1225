/**
 * ThemePreview Component
 * 主题预览组件
 * 
 * 用于预览和选择品牌主题
 */

import React, { useCallback } from 'react';
import { Card, Button, Tag, Space, Typography, Tooltip } from 'antd';
import { CheckOutlined, EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons';
import { useBrandTheme } from '@/hooks/useBrandTheme';
import type { BrandTheme, BrandThemeType } from '@/types/brand';
import styles from './ThemePreview.module.scss';

const { Text, Title } = Typography;

export interface ThemePreviewProps {
  theme: BrandTheme;
  isSelected?: boolean;
  isPreviewing?: boolean;
  showActions?: boolean;
  compact?: boolean;
  onSelect?: (themeId: BrandThemeType) => void;
  onPreview?: (theme: BrandTheme) => void;
  onStopPreview?: () => void;
}

export const ThemePreview: React.FC<ThemePreviewProps> = ({
  theme,
  isSelected = false,
  isPreviewing = false,
  showActions = true,
  compact = false,
  onSelect,
  onPreview,
  onStopPreview
}) => {
  const { colors } = theme;

  const handleSelect = useCallback(() => {
    onSelect?.(theme.id);
  }, [theme.id, onSelect]);

  const handlePreview = useCallback(() => {
    if (isPreviewing) {
      onStopPreview?.();
    } else {
      onPreview?.(theme);
    }
  }, [theme, isPreviewing, onPreview, onStopPreview]);

  // 颜色预览块
  const ColorSwatch: React.FC<{ color: string; label: string }> = ({ color, label }) => (
    <Tooltip title={`${label}: ${color}`}>
      <div
        className={styles.colorSwatch}
        style={{ backgroundColor: color }}
        aria-label={`${label}: ${color}`}
      />
    </Tooltip>
  );

  if (compact) {
    return (
      <div 
        className={`${styles.compactPreview} ${isSelected ? styles.selected : ''}`}
        onClick={handleSelect}
        role="button"
        tabIndex={0}
        aria-pressed={isSelected}
      >
        <div className={styles.colorBar}>
          <div style={{ backgroundColor: colors.primary, flex: 2 }} />
          <div style={{ backgroundColor: colors.secondary, flex: 1 }} />
          <div style={{ backgroundColor: colors.accent, flex: 1 }} />
        </div>
        <Text className={styles.compactName}>{theme.nameZh}</Text>
        {isSelected && <CheckOutlined className={styles.checkIcon} />}
      </div>
    );
  }

  return (
    <Card
      className={`${styles.themeCard} ${isSelected ? styles.selected : ''} ${isPreviewing ? styles.previewing : ''}`}
      hoverable
      size="small"
    >
      {/* 颜色预览 */}
      <div className={styles.colorPreview}>
        <div 
          className={styles.primaryBlock}
          style={{ backgroundColor: colors.primary }}
        >
          <Text className={styles.primaryText} style={{ color: '#fff' }}>
            {theme.nameZh}
          </Text>
        </div>
        <div className={styles.colorRow}>
          <ColorSwatch color={colors.primaryHover} label="悬停色" />
          <ColorSwatch color={colors.secondary} label="次要色" />
          <ColorSwatch color={colors.accent} label="强调色" />
          <ColorSwatch color={colors.background} label="背景色" />
        </div>
      </div>

      {/* 主题信息 */}
      <div className={styles.themeInfo}>
        <Title level={5} className={styles.themeName}>
          {theme.nameZh}
          {isSelected && (
            <Tag color="blue" className={styles.activeTag}>当前</Tag>
          )}
          {isPreviewing && (
            <Tag color="orange" className={styles.previewTag}>预览中</Tag>
          )}
        </Title>
        <Text type="secondary" className={styles.themeDescription}>
          {theme.description}
        </Text>
        
        {/* 日期范围 */}
        {theme.startDate && theme.endDate && (
          <Text type="secondary" className={styles.dateRange}>
            {theme.startDate} ~ {theme.endDate}
          </Text>
        )}
      </div>

      {/* 操作按钮 */}
      {showActions && (
        <div className={styles.actions}>
          <Space>
            <Button
              type={isPreviewing ? 'default' : 'text'}
              icon={isPreviewing ? <EyeInvisibleOutlined /> : <EyeOutlined />}
              onClick={handlePreview}
              size="small"
            >
              {isPreviewing ? '停止预览' : '预览'}
            </Button>
            <Button
              type={isSelected ? 'primary' : 'default'}
              icon={isSelected ? <CheckOutlined /> : null}
              onClick={handleSelect}
              disabled={isSelected}
              size="small"
            >
              {isSelected ? '已选择' : '选择'}
            </Button>
          </Space>
        </div>
      )}
    </Card>
  );
};

/**
 * 主题列表组件
 */
export interface ThemeListProps {
  compact?: boolean;
}

export const ThemeList: React.FC<ThemeListProps> = ({ compact = false }) => {
  const { 
    availableThemes, 
    currentTheme, 
    previewTheme,
    isPreviewMode,
    setTheme, 
    startPreview, 
    stopPreview 
  } = useBrandTheme();

  return (
    <div className={compact ? styles.compactList : styles.themeList}>
      {availableThemes.map((theme) => (
        <ThemePreview
          key={theme.id}
          theme={theme}
          isSelected={currentTheme.id === theme.id}
          isPreviewing={isPreviewMode && previewTheme?.id === theme.id}
          compact={compact}
          onSelect={setTheme}
          onPreview={startPreview}
          onStopPreview={stopPreview}
        />
      ))}
    </div>
  );
};

export default ThemePreview;
