/**
 * ResponsiveTable Component
 * 
 * A table component that adapts its layout and display
 * based on viewport size, with card view for mobile.
 */

import { memo, ReactNode, useMemo } from 'react';
import { Table, Card, List, Tag, Typography, Empty } from 'antd';
import type { TableProps, ColumnsType } from 'antd/es/table';
import { useResponsive } from '@/hooks/useResponsive';
import styles from './ResponsiveTable.module.scss';

const { Text } = Typography;

interface ResponsiveColumn<T> {
  key: string;
  title: string;
  dataIndex: string | string[];
  render?: (value: unknown, record: T, index: number) => ReactNode;
  
  // Responsive options
  hideOnMobile?: boolean;
  hideOnTablet?: boolean;
  showInCard?: boolean;
  cardLabel?: string;
  isPrimary?: boolean; // Show as card title
  isSecondary?: boolean; // Show as card subtitle
  isTag?: boolean; // Render as tag in card view
}

interface ResponsiveTableProps<T extends object> extends Omit<TableProps<T>, 'columns'> {
  columns: ResponsiveColumn<T>[];
  dataSource: T[];
  
  // Mobile card options
  cardTitle?: (record: T) => ReactNode;
  cardDescription?: (record: T) => ReactNode;
  cardExtra?: (record: T) => ReactNode;
  cardActions?: (record: T) => ReactNode[];
  
  // Loading
  loading?: boolean;
  
  // Empty state
  emptyText?: string;
  emptyDescription?: string;
  
  // Styling
  className?: string;
  cardClassName?: string;
  
  // Force card view
  forceCardView?: boolean;
  
  // Row key
  rowKey: string | ((record: T) => string);
}

function getNestedValue(obj: Record<string, unknown>, path: string | string[]): unknown {
  const keys = Array.isArray(path) ? path : path.split('.');
  return keys.reduce((acc: unknown, key: string) => {
    if (acc && typeof acc === 'object' && key in acc) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

function ResponsiveTableInner<T extends object>({
  columns,
  dataSource,
  cardTitle,
  cardDescription,
  cardExtra,
  cardActions,
  loading = false,
  emptyText = '暂无数据',
  emptyDescription,
  className,
  cardClassName,
  forceCardView = false,
  rowKey,
  ...tableProps
}: ResponsiveTableProps<T>) {
  const { isMobile, isTablet } = useResponsive();

  // Filter columns based on viewport
  const filteredColumns = useMemo(() => {
    return columns.filter((col) => {
      if (isMobile && col.hideOnMobile) return false;
      if (isTablet && col.hideOnTablet) return false;
      return true;
    });
  }, [columns, isMobile, isTablet]);

  // Convert to Ant Design columns
  const antColumns: ColumnsType<T> = useMemo(() => {
    return filteredColumns.map((col) => ({
      key: col.key,
      title: col.title,
      dataIndex: col.dataIndex,
      render: col.render,
    }));
  }, [filteredColumns]);

  // Get row key function
  const getRowKey = (record: T): string => {
    if (typeof rowKey === 'function') {
      return rowKey(record);
    }
    return String((record as Record<string, unknown>)[rowKey]);
  };

  // Render card view for mobile
  const renderCardView = () => {
    if (dataSource.length === 0) {
      return (
        <Empty
          description={emptyDescription || emptyText}
          className={styles.empty}
        />
      );
    }

    return (
      <List
        loading={loading}
        dataSource={dataSource}
        className={`${styles.cardList} ${cardClassName || ''}`}
        renderItem={(record, index) => {
          // Find primary and secondary columns
          const primaryCol = columns.find((col) => col.isPrimary);
          const secondaryCol = columns.find((col) => col.isSecondary);
          const tagCols = columns.filter((col) => col.isTag);
          const cardCols = columns.filter((col) => col.showInCard !== false && !col.isPrimary && !col.isSecondary && !col.isTag);

          // Get title
          const title = cardTitle 
            ? cardTitle(record)
            : primaryCol 
              ? primaryCol.render 
                ? primaryCol.render(getNestedValue(record, primaryCol.dataIndex), record, index)
                : getNestedValue(record, primaryCol.dataIndex)
              : `Item ${index + 1}`;

          // Get description
          const description = cardDescription
            ? cardDescription(record)
            : secondaryCol
              ? secondaryCol.render
                ? secondaryCol.render(getNestedValue(record, secondaryCol.dataIndex), record, index)
                : getNestedValue(record, secondaryCol.dataIndex)
              : null;

          return (
            <List.Item key={getRowKey(record)} className={styles.cardItem}>
              <Card
                className={styles.card}
                size="small"
                title={
                  <div className={styles.cardHeader}>
                    <div className={styles.cardTitle}>{title}</div>
                    {cardExtra && <div className={styles.cardExtra}>{cardExtra(record)}</div>}
                  </div>
                }
                actions={cardActions ? cardActions(record) : undefined}
              >
                {description && (
                  <Text type="secondary" className={styles.cardDescription}>
                    {description}
                  </Text>
                )}

                {/* Tags */}
                {tagCols.length > 0 && (
                  <div className={styles.cardTags}>
                    {tagCols.map((col) => {
                      const value = getNestedValue(record, col.dataIndex);
                      const rendered = col.render 
                        ? col.render(value, record, index)
                        : value;
                      return (
                        <span key={col.key}>
                          {typeof rendered === 'string' ? <Tag>{rendered}</Tag> : rendered}
                        </span>
                      );
                    })}
                  </div>
                )}

                {/* Other fields */}
                {cardCols.length > 0 && (
                  <div className={styles.cardFields}>
                    {cardCols.map((col) => {
                      const value = getNestedValue(record, col.dataIndex);
                      const rendered = col.render 
                        ? col.render(value, record, index)
                        : value;
                      return (
                        <div key={col.key} className={styles.cardField}>
                          <Text type="secondary" className={styles.fieldLabel}>
                            {col.cardLabel || col.title}:
                          </Text>
                          <span className={styles.fieldValue}>{rendered}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>
            </List.Item>
          );
        }}
      />
    );
  };

  // Render table view for desktop
  const renderTableView = () => {
    return (
      <Table<T>
        columns={antColumns}
        dataSource={dataSource}
        loading={loading}
        rowKey={rowKey}
        className={`${styles.table} ${className || ''}`}
        locale={{
          emptyText: (
            <Empty
              description={emptyDescription || emptyText}
            />
          ),
        }}
        scroll={{ x: 'max-content' }}
        {...tableProps}
      />
    );
  };

  // Determine which view to render
  const shouldShowCardView = forceCardView || isMobile;

  return (
    <div className={styles.responsiveTable}>
      {shouldShowCardView ? renderCardView() : renderTableView()}
    </div>
  );
}

export const ResponsiveTable = memo(ResponsiveTableInner) as typeof ResponsiveTableInner;

export default ResponsiveTable;
