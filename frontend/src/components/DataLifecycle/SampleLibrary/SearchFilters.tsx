/**
 * SearchFilters Component
 * 
 * Provides search and filter controls for the sample library.
 * Supports filtering by tags, category, quality score range, and date range.
 */

import React, { useState, useCallback } from 'react';
import {
  Form,
  Input,
  Select,
  DatePicker,
  Slider,
  Button,
  Space,
  Card,
  Row,
  Col,
} from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;

// ============================================================================
// Types
// ============================================================================

export interface SearchFilters {
  tags?: string[];
  category?: string;
  qualityScoreMin?: number;
  qualityScoreMax?: number;
  dateFrom?: string;
  dateTo?: string;
}

export interface SearchFiltersProps {
  filters: SearchFilters;
  onChange: (filters: SearchFilters) => void;
}

// ============================================================================
// Component
// ============================================================================

const SearchFilters: React.FC<SearchFiltersProps> = ({ filters, onChange }) => {
  const { t } = useTranslation('dataLifecycle');
  const [form] = Form.useForm();
  
  // Local state for quality score range
  const [qualityRange, setQualityRange] = useState<[number, number]>([
    filters.qualityScoreMin || 0,
    filters.qualityScoreMax || 1,
  ]);

  // Handle search
  const handleSearch = useCallback(() => {
    const values = form.getFieldsValue();
    const newFilters: SearchFilters = {
      tags: values.tags,
      category: values.category,
      qualityScoreMin: qualityRange[0],
      qualityScoreMax: qualityRange[1],
    };

    // Handle date range
    if (values.dateRange && values.dateRange.length === 2) {
      newFilters.dateFrom = values.dateRange[0].format('YYYY-MM-DD');
      newFilters.dateTo = values.dateRange[1].format('YYYY-MM-DD');
    }

    onChange(newFilters);
  }, [form, qualityRange, onChange]);

  // Handle reset
  const handleReset = useCallback(() => {
    form.resetFields();
    setQualityRange([0, 1]);
    onChange({});
  }, [form, onChange]);

  // Handle quality range change
  const handleQualityRangeChange = useCallback((value: number | number[]) => {
    if (Array.isArray(value)) {
      setQualityRange([value[0], value[1]]);
    }
  }, []);

  return (
    <Card size="small">
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          tags: filters.tags,
          category: filters.category,
        }}
      >
        <Row gutter={16}>
          {/* Tags Filter */}
          <Col xs={24} sm={12} md={6}>
            <Form.Item
              name="tags"
              label={t('sampleLibrary.filters.tags')}
            >
              <Select
                mode="tags"
                placeholder={t('common.placeholders.select')}
                style={{ width: '100%' }}
                allowClear
              >
                {/* Tags will be populated dynamically */}
              </Select>
            </Form.Item>
          </Col>

          {/* Category Filter */}
          <Col xs={24} sm={12} md={6}>
            <Form.Item
              name="category"
              label={t('sampleLibrary.filters.category')}
            >
              <Select
                placeholder={t('common.placeholders.select')}
                allowClear
              >
                <Option value="text">{t('common.type')}</Option>
                <Option value="image">{t('common.type')}</Option>
                <Option value="audio">{t('common.type')}</Option>
                <Option value="video">{t('common.type')}</Option>
              </Select>
            </Form.Item>
          </Col>

          {/* Date Range Filter */}
          <Col xs={24} sm={12} md={6}>
            <Form.Item
              name="dateRange"
              label={t('sampleLibrary.filters.dateRange')}
            >
              <RangePicker
                style={{ width: '100%' }}
                format="YYYY-MM-DD"
              />
            </Form.Item>
          </Col>

          {/* Action Buttons */}
          <Col xs={24} sm={12} md={6}>
            <Form.Item label=" ">
              <Space>
                <Button
                  type="primary"
                  icon={<SearchOutlined />}
                  onClick={handleSearch}
                >
                  {t('common.actions.search')}
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={handleReset}
                >
                  {t('common.actions.reset')}
                </Button>
              </Space>
            </Form.Item>
          </Col>
        </Row>

        {/* Quality Score Range Filter */}
        <Row>
          <Col span={24}>
            <Form.Item
              label={`${t('sampleLibrary.filters.quality')}: ${qualityRange[0].toFixed(2)} - ${qualityRange[1].toFixed(2)}`}
            >
              <Slider
                range
                min={0}
                max={1}
                step={0.01}
                value={qualityRange}
                onChange={handleQualityRangeChange}
                marks={{
                  0: '0',
                  0.25: '0.25',
                  0.5: '0.5',
                  0.75: '0.75',
                  1: '1',
                }}
              />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Card>
  );
};

export default SearchFilters;
