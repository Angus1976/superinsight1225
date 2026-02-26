import React, { useState, useRef, useCallback, useMemo } from 'react';
import { ProTable, type ProColumns, type ActionType } from '@ant-design/pro-components';
import {
  Button, Space, Tag, Modal, Form, Input, Select, Switch,
  message, Popconfirm, Tooltip,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  ApiOutlined, DatabaseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { usePermissions } from '@/hooks/usePermissions';
import {
  useDatalakeSources,
  useCreateDatalakeSource,
  useUpdateDatalakeSource,
  useDeleteDatalakeSource,
  useTestDatalakeConnection,
} from '@/hooks/useDatalake';
import {
  DatalakeSourceType,
  DataSourceStatus,
  type DatalakeSourceResponse,
} from '@/types/datalake';

const SOURCE_TYPE_OPTIONS = Object.values(DatalakeSourceType);

const STATUS_COLOR_MAP: Record<DataSourceStatus, string> = {
  [DataSourceStatus.ACTIVE]: 'success',
  [DataSourceStatus.INACTIVE]: 'default',
  [DataSourceStatus.ERROR]: 'error',
  [DataSourceStatus.TESTING]: 'processing',
};

const HEALTH_COLOR_MAP: Record<string, string> = {
  connected: 'success',
  healthy: 'success',
  degraded: 'warning',
  error: 'error',
  down: 'error',
};

/** ADMIN and TECHNICAL_EXPERT can manage sources */
const canManageSources = (role: string): boolean => {
  const upper = role.toUpperCase();
  return upper === 'ADMIN' || upper === 'TECHNICAL_EXPERT';
};
