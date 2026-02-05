// Theme configuration for Ant Design
import type { ThemeConfig } from 'antd';

// Light theme configuration
export const lightTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#1890ff',
    colorTextBase: '#000000',
    colorBgBase: '#ffffff',
    borderRadius: 6,
    fontSize: 14,
  },
  components: {
    Tooltip: {
      colorBgSpotlight: '#ffffff',
      colorTextLightSolid: '#262626',
    },
    Popover: {
      colorBgElevated: '#ffffff',
      colorText: '#000000',
    },
    Dropdown: {
      colorBgElevated: '#ffffff',
      colorText: '#000000',
      controlItemBgHover: '#f5f5f5',
      controlItemBgActive: '#e6f7ff',
    },
    Modal: {
      contentBg: '#ffffff',
      headerBg: '#ffffff',
    },
    Drawer: {
      colorBgElevated: '#ffffff',
    },
  },
};

// Dark theme configuration
export const darkTheme: ThemeConfig = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#1890ff',
    colorTextBase: '#ffffff',
    colorBgBase: '#141414',
    borderRadius: 6,
    fontSize: 14,
  },
  components: {
    Tooltip: {
      colorBgSpotlight: 'rgba(0, 0, 0, 0.85)',
      colorTextLightSolid: '#ffffff',
    },
    Popover: {
      colorBgElevated: '#1f1f1f',
      colorText: '#ffffff',
    },
    Dropdown: {
      colorBgElevated: '#1f1f1f',
      colorText: '#ffffff',
      controlItemBgHover: '#262626',
      controlItemBgActive: '#177ddc',
    },
    Modal: {
      contentBg: '#1f1f1f',
      headerBg: '#1f1f1f',
    },
    Drawer: {
      colorBgElevated: '#1f1f1f',
    },
  },
};
