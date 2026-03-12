/**
 * Property Test: 角色决定配置按钮可见性
 *
 * Feature: ai-assistant-config-redesign, Property 1: 角色决定配置按钮可见性
 *
 * **Validates: Requirements 2.3, 2.4**
 *
 * Property 1: 对于任意用户角色，ConfigPanel 显示的按钮数量应为：
 * admin 角色显示 3 个（配置数据源、配置权限表、输出方式），
 * 非 admin 角色仅显示 1 个（输出方式）。
 */

import { describe, it, expect, vi } from 'vitest';
import * as fc from 'fast-check';
import { render, screen } from '@testing-library/react';
import ConfigPanel from '@/pages/AIAssistant/components/ConfigPanel';
import { I18nextProvider } from 'react-i18next';
import i18n from 'i18next';

// Initialize i18n for testing
i18n.init({
  lng: 'zh',
  fallbackLng: 'zh',
  resources: {
    zh: {
      aiAssistant: {
        'configPanel.title': '配置',
        'configPanel.configDataSource': '配置数据源',
        'configPanel.configPermissions': '配置权限表',
        'configPanel.outputMode': '输出方式',
      },
    },
  },
  interpolation: {
    escapeValue: false,
  },
});

// Arbitrary for generating valid user roles
const roleArb = fc.constantFrom('admin', 'business_expert', 'annotator', 'viewer');

/**
 * Helper function to render ConfigPanel with i18n context
 */
function renderConfigPanel(userRole: string) {
  const mockHandlers = {
    onOpenDataSourceConfig: vi.fn(),
    onOpenPermissionTable: vi.fn(),
    onOpenOutputMode: vi.fn(),
  };

  const result = render(
    <I18nextProvider i18n={i18n}>
      <ConfigPanel
        userRole={userRole}
        onOpenDataSourceConfig={mockHandlers.onOpenDataSourceConfig}
        onOpenPermissionTable={mockHandlers.onOpenPermissionTable}
        onOpenOutputMode={mockHandlers.onOpenOutputMode}
      />
    </I18nextProvider>
  );

  return { ...result, mockHandlers };
}

describe('Property 1: 角色决定配置按钮可见性', () => {
  it('admin role always displays exactly 3 buttons', () => {
    fc.assert(
      fc.property(fc.constant('admin'), (role) => {
        const { container, unmount } = renderConfigPanel(role);
        
        try {
          // Count all buttons in the ConfigPanel
          const buttons = container.querySelectorAll('button');
          
          expect(buttons).toHaveLength(3);
          
          // Verify the specific button texts are present in the container
          const buttonTexts = Array.from(buttons).map(btn => btn.textContent);
          expect(buttonTexts).toContain('配置数据源');
          expect(buttonTexts).toContain('配置权限表');
          expect(buttonTexts).toContain('输出方式');
        } finally {
          unmount();
        }
      }),
      { numRuns: 100 }
    );
  });

  it('non-admin roles always display exactly 1 button', () => {
    const nonAdminRoleArb = fc.constantFrom('business_expert', 'annotator', 'viewer');
    
    fc.assert(
      fc.property(nonAdminRoleArb, (role) => {
        const { container, unmount } = renderConfigPanel(role);
        
        try {
          // Count all buttons in the ConfigPanel
          const buttons = container.querySelectorAll('button');
          
          expect(buttons).toHaveLength(1);
          
          // Verify only the output mode button is present
          const buttonTexts = Array.from(buttons).map(btn => btn.textContent);
          expect(buttonTexts).toContain('输出方式');
          expect(buttonTexts).not.toContain('配置数据源');
          expect(buttonTexts).not.toContain('配置权限表');
        } finally {
          unmount();
        }
      }),
      { numRuns: 100 }
    );
  });

  it('button count is determined solely by role: admin=3, non-admin=1', () => {
    fc.assert(
      fc.property(roleArb, (role) => {
        const { container, unmount } = renderConfigPanel(role);
        
        try {
          const buttons = container.querySelectorAll('button');
          const expectedCount = role === 'admin' ? 3 : 1;
          
          expect(buttons).toHaveLength(expectedCount);
        } finally {
          unmount();
        }
      }),
      { numRuns: 100 }
    );
  });

  it('output mode button is always present regardless of role', () => {
    fc.assert(
      fc.property(roleArb, (role) => {
        const { container, unmount } = renderConfigPanel(role);
        
        try {
          // Output mode button must always be present
          const buttons = container.querySelectorAll('button');
          const buttonTexts = Array.from(buttons).map(btn => btn.textContent);
          expect(buttonTexts).toContain('输出方式');
        } finally {
          unmount();
        }
      }),
      { numRuns: 100 }
    );
  });

  it('admin-only buttons are never present for non-admin roles', () => {
    const nonAdminRoleArb = fc.constantFrom('business_expert', 'annotator', 'viewer');
    
    fc.assert(
      fc.property(nonAdminRoleArb, (role) => {
        const { container, unmount } = renderConfigPanel(role);
        
        try {
          // Admin-only buttons must not be present
          const buttons = container.querySelectorAll('button');
          const buttonTexts = Array.from(buttons).map(btn => btn.textContent);
          expect(buttonTexts).not.toContain('配置数据源');
          expect(buttonTexts).not.toContain('配置权限表');
        } finally {
          unmount();
        }
      }),
      { numRuns: 100 }
    );
  });

  it('button visibility is consistent across multiple renders of the same role', () => {
    fc.assert(
      fc.property(roleArb, (role) => {
        // First render
        const { container: container1, unmount: unmount1 } = renderConfigPanel(role);
        const buttonCount1 = container1.querySelectorAll('button').length;
        unmount1();
        
        // Second render
        const { container: container2, unmount: unmount2 } = renderConfigPanel(role);
        const buttonCount2 = container2.querySelectorAll('button').length;
        unmount2();
        
        // Button count should be consistent
        expect(buttonCount1).toBe(buttonCount2);
        expect(buttonCount1).toBe(role === 'admin' ? 3 : 1);
      }),
      { numRuns: 100 }
    );
  });
});
