/**
 * ConfirmModal Component
 * 
 * Consistent confirmation modal for user actions.
 * Follows the design system for beautiful and consistent UI.
 */

import { memo, ReactNode } from 'react';
import { Modal, Typography, Space, Button } from 'antd';
import {
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import styles from './ConfirmModal.module.scss';

const { Title, Paragraph } = Typography;

type ModalType = 'confirm' | 'warning' | 'danger' | 'success' | 'info';

interface ConfirmModalProps {
  open: boolean;
  type?: ModalType;
  title: string;
  content: ReactNode;
  confirmText?: string;
  cancelText?: string;
  confirmLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  icon?: ReactNode;
  width?: number;
  centered?: boolean;
  closable?: boolean;
}

const modalConfig: Record<ModalType, {
  icon: ReactNode;
  color: string;
  confirmType: 'primary' | 'default';
  confirmDanger: boolean;
}> = {
  confirm: {
    icon: <QuestionCircleOutlined />,
    color: '#1890ff',
    confirmType: 'primary',
    confirmDanger: false,
  },
  warning: {
    icon: <ExclamationCircleOutlined />,
    color: '#faad14',
    confirmType: 'primary',
    confirmDanger: false,
  },
  danger: {
    icon: <CloseCircleOutlined />,
    color: '#ff4d4f',
    confirmType: 'primary',
    confirmDanger: true,
  },
  success: {
    icon: <CheckCircleOutlined />,
    color: '#52c41a',
    confirmType: 'primary',
    confirmDanger: false,
  },
  info: {
    icon: <InfoCircleOutlined />,
    color: '#1890ff',
    confirmType: 'primary',
    confirmDanger: false,
  },
};

export const ConfirmModal = memo<ConfirmModalProps>(({
  open,
  type = 'confirm',
  title,
  content,
  confirmText = '确认',
  cancelText = '取消',
  confirmLoading = false,
  onConfirm,
  onCancel,
  icon,
  width = 420,
  centered = true,
  closable = true,
}) => {
  const config = modalConfig[type];
  const displayIcon = icon || config.icon;
  
  return (
    <Modal
      open={open}
      onCancel={onCancel}
      width={width}
      centered={centered}
      closable={closable}
      footer={null}
      className={styles.confirmModal}
      maskClosable={!confirmLoading}
    >
      <div className={styles.modalContent}>
        <div 
          className={styles.iconWrapper}
          style={{ backgroundColor: `${config.color}15`, color: config.color }}
        >
          {displayIcon}
        </div>
        
        <div className={styles.textContent}>
          <Title level={4} className={styles.title}>
            {title}
          </Title>
          
          <div className={styles.content}>
            {typeof content === 'string' ? (
              <Paragraph type="secondary" className={styles.description}>
                {content}
              </Paragraph>
            ) : (
              content
            )}
          </div>
        </div>
        
        <div className={styles.footer}>
          <Space size="middle">
            <Button 
              onClick={onCancel}
              disabled={confirmLoading}
            >
              {cancelText}
            </Button>
            <Button
              type={config.confirmType}
              danger={config.confirmDanger}
              loading={confirmLoading}
              onClick={onConfirm}
            >
              {confirmText}
            </Button>
          </Space>
        </div>
      </div>
    </Modal>
  );
});

ConfirmModal.displayName = 'ConfirmModal';

// Utility function to show confirm modal imperatively
export const showConfirm = (props: Omit<ConfirmModalProps, 'open'>) => {
  Modal.confirm({
    title: props.title,
    content: props.content,
    okText: props.confirmText || '确认',
    cancelText: props.cancelText || '取消',
    onOk: props.onConfirm,
    onCancel: props.onCancel,
    centered: props.centered !== false,
    icon: props.icon,
    width: props.width,
  });
};

// Utility function to show danger confirm modal
export const showDangerConfirm = (props: Omit<ConfirmModalProps, 'open' | 'type'>) => {
  Modal.confirm({
    title: props.title,
    content: props.content,
    okText: props.confirmText || '删除',
    cancelText: props.cancelText || '取消',
    okButtonProps: { danger: true },
    onOk: props.onConfirm,
    onCancel: props.onCancel,
    centered: props.centered !== false,
    icon: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
    width: props.width,
  });
};
