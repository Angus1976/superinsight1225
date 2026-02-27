/**
 * Integration tests for MainLayout rendering.
 *
 * Verifies that sidebar grouping, header components (GlobalSearch,
 * NotificationBell, HelpButton), and footer (LayoutFooter) render
 * together correctly. Also tests theme switch and collapsed mode.
 *
 * Validates: Requirements 2.4, 2.5, 3.4, 5.2
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MainLayout } from '../MainLayout';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

// react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: '/dashboard' }),
  useParams: () => ({}),
  Outlet: () => <div data-testid="outlet">Outlet Content</div>,
}));

// react-i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => fallback ?? key,
    i18n: {
      language: 'zh',
      changeLanguage: vi.fn(),
    },
  }),
}));

// Stores – keep mutable refs so tests can override per-case
let mockUIState = {
  theme: 'light' as string,
  sidebarCollapsed: false,
  clientCompany: null as null | { name: string; nameEn: string; logo?: string; label?: string },
  toggleSidebar: vi.fn(),
  toggleTheme: vi.fn(),
  setLanguage: vi.fn(),
  setTheme: vi.fn(),
  setSidebarCollapsed: vi.fn(),
  setLoading: vi.fn(),
  setClientCompany: vi.fn(),
  language: 'zh' as const,
  loading: false,
};

vi.mock('@/stores/uiStore', () => ({
  useUIStore: (selector?: (s: typeof mockUIState) => unknown) =>
    selector ? selector(mockUIState) : mockUIState,
}));

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    user: { id: '1', username: 'tester', role: 'admin', tenant_id: 't1' },
    token: 'tok',
    isAuthenticated: true,
  }),
}));

// Hooks
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: '1', username: 'tester', role: 'admin' },
    logout: vi.fn(),
  }),
}));

vi.mock('@/hooks/useBreadcrumb', () => ({
  useBreadcrumb: () => ({ breadcrumbItems: [], pageTitle: 'Dashboard' }),
}));

vi.mock('@/hooks/useGlobalSearch', () => ({
  useGlobalSearch: () => ({
    isOpen: false,
    query: '',
    open: vi.fn(),
    close: vi.fn(),
    setQuery: vi.fn(),
  }),
}));

// Auth sub-components that are not under test
vi.mock('@/components/Auth/TenantSelector', () => ({
  TenantSelector: () => <div data-testid="tenant-selector" />,
}));
vi.mock('@/components/Auth/WorkspaceSwitcher', () => ({
  WorkspaceSwitcher: () => <div data-testid="workspace-switcher" />,
}));

// SCSS modules – provide default export with identity proxy for class names
vi.mock('../ClientBranding.module.scss', () => {
  const p = new Proxy({} as Record<string, string>, { get: (_t, k) => String(k) });
  return { default: p, __esModule: true, ...p };
});
vi.mock('../LayoutFooter.module.scss', () => {
  const p = new Proxy({} as Record<string, string>, { get: (_t, k) => String(k) });
  return { default: p, __esModule: true, ...p };
});
vi.mock('../SidebarStyles.module.scss', () => {
  const p = new Proxy({} as Record<string, string>, { get: (_t, k) => String(k) });
  return { default: p, __esModule: true, ...p };
});
vi.mock('../GlobalSearch.module.scss', () => {
  const p = new Proxy({} as Record<string, string>, { get: (_t, k) => String(k) });
  return { default: p, __esModule: true, ...p };
});

// ProLayout – render a simplified shell that exercises the render-prop callbacks
vi.mock('@ant-design/pro-components', () => ({
  ProLayout: (props: {
    menuHeaderRender?: () => React.ReactNode;
    headerContentRender?: () => React.ReactNode;
    footerRender?: () => React.ReactNode;
    menuItemRender?: (item: Record<string, unknown>, dom: React.ReactNode) => React.ReactNode;
    route?: { routes: Array<Record<string, unknown>> };
    children?: React.ReactNode;
  }) => {
    const routes: Array<Record<string, unknown>> = props.route?.routes ?? [];
    return (
      <div data-testid="pro-layout">
        {/* Sidebar header */}
        <div data-testid="sidebar-header">{props.menuHeaderRender?.()}</div>

        {/* Menu items rendered via menuItemRender */}
        <nav data-testid="sidebar-menu">
          {routes.map((r, i) =>
            props.menuItemRender?.(r, <span key={i}>{String(r.name)}</span>),
          )}
        </nav>

        {/* Header */}
        <header data-testid="header">{props.headerContentRender?.()}</header>

        {/* Footer */}
        <footer data-testid="footer">{props.footerRender?.()}</footer>

        {/* Content */}
        {props.children}
      </div>
    );
  },
  PageContainer: (props: { children?: React.ReactNode }) => (
    <div data-testid="page-container">{props.children}</div>
  ),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function resetUIState(overrides: Partial<typeof mockUIState> = {}) {
  mockUIState = {
    theme: 'light',
    sidebarCollapsed: false,
    clientCompany: null,
    toggleSidebar: vi.fn(),
    toggleTheme: vi.fn(),
    setLanguage: vi.fn(),
    setTheme: vi.fn(),
    setSidebarCollapsed: vi.fn(),
    setLoading: vi.fn(),
    setClientCompany: vi.fn(),
    language: 'zh',
    loading: false,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MainLayout integration', () => {
  beforeEach(() => {
    resetUIState();
    mockNavigate.mockReset();
  });

  // -- 1. Sidebar grouping ---------------------------------------------------

  it('renders sidebar with group headers from buildMenuRoutes', () => {
    render(<MainLayout />);
    const menu = screen.getByTestId('sidebar-menu');
    // buildMenuRoutes produces group dividers with translated titleKeys
    // The mock t() returns the key itself, so we look for group title keys
    expect(menu.textContent).toContain('navGroup.workbench');
    expect(menu.textContent).toContain('navGroup.dataManage');
    expect(menu.textContent).toContain('navGroup.system');
  });

  it('renders regular menu items alongside group headers', () => {
    render(<MainLayout />);
    const menu = screen.getByTestId('sidebar-menu');
    // Menu items are translated as t('menu.<nameKey>') → 'menu.dashboard'
    expect(menu.textContent).toContain('menu.dashboard');
    expect(menu.textContent).toContain('menu.tasks');
  });

  // -- 2. Header components ---------------------------------------------------

  it('renders GlobalSearch trigger in header', () => {
    render(<MainLayout />);
    const header = screen.getByTestId('header');
    // GlobalSearch renders a trigger with search text
    expect(header.textContent).toContain('搜索');
  });

  it('renders NotificationBell in header', () => {
    render(<MainLayout />);
    const header = screen.getByTestId('header');
    // NotificationBell renders a bell icon button with aria-label '通知'
    const bell = header.querySelector('.anticon-bell');
    expect(bell).toBeTruthy();
  });

  it('renders HelpButton in header', () => {
    render(<MainLayout />);
    const header = screen.getByTestId('header');
    const help = header.querySelector('.anticon-question-circle');
    expect(help).toBeTruthy();
  });

  // -- 3. Footer --------------------------------------------------------------

  it('renders LayoutFooter with brand text when expanded', () => {
    render(<MainLayout />);
    const footer = screen.getByTestId('footer');
    expect(footer.textContent).toContain('Powered by');
  });

  it('renders LayoutFooter without brand text when collapsed (Req 5.2)', () => {
    resetUIState({ sidebarCollapsed: true });
    render(<MainLayout />);
    const footer = screen.getByTestId('footer');
    // Collapsed footer should NOT contain the powered-by text
    expect(footer.textContent).not.toContain('Powered by');
  });

  // -- 4. Theme switch --------------------------------------------------------

  it('renders theme toggle switch in header', () => {
    render(<MainLayout />);
    const header = screen.getByTestId('header');
    // Ant Design Switch renders a button with role="switch"
    const toggle = header.querySelector('[role="switch"]');
    expect(toggle).toBeTruthy();
  });

  it('theme switch is unchecked in light mode', () => {
    resetUIState({ theme: 'light' });
    render(<MainLayout />);
    const toggle = screen.getByTestId('header').querySelector('[role="switch"]');
    expect(toggle?.getAttribute('aria-checked')).toBe('false');
  });

  it('theme switch is checked in dark mode', () => {
    resetUIState({ theme: 'dark' });
    render(<MainLayout />);
    const toggle = screen.getByTestId('header').querySelector('[role="switch"]');
    expect(toggle?.getAttribute('aria-checked')).toBe('true');
  });

  // -- 5. Collapsed mode (Req 2.5, 3.4) --------------------------------------

  it('hides group header text when sidebar is collapsed (Req 2.5)', () => {
    resetUIState({ sidebarCollapsed: true });
    const { container } = render(<MainLayout />);
    // SidebarMenuItem renders navGroupHeaderCollapsed (empty div) for groups when collapsed
    const collapsedHeaders = container.querySelectorAll('[class*="navGroupHeaderCollapsed"]');
    expect(collapsedHeaders.length).toBeGreaterThan(0);
  });

  it('ClientBranding shows only icon when collapsed, no text (Req 3.4)', () => {
    resetUIState({ sidebarCollapsed: true });
    render(<MainLayout />);
    const sidebarHeader = screen.getByTestId('sidebar-header');
    // Default null clientCompany → LogoIcon only, no "问视间" text
    expect(sidebarHeader.textContent).not.toContain('问视间');
  });

  it('ClientBranding shows icon + text when expanded', () => {
    resetUIState({ sidebarCollapsed: false });
    render(<MainLayout />);
    const sidebarHeader = screen.getByTestId('sidebar-header');
    expect(sidebarHeader.textContent).toContain('问视间');
  });

  // -- 6. ClientBranding with company config ----------------------------------

  it('ClientBranding renders company name when clientCompany is set', () => {
    resetUIState({
      clientCompany: { name: 'Acme Corp', nameEn: 'Acme Corp' },
    });
    render(<MainLayout />);
    const sidebarHeader = screen.getByTestId('sidebar-header');
    expect(sidebarHeader.textContent).toContain('Acme Corp');
  });

  it('ClientBranding hides company name when collapsed with clientCompany', () => {
    resetUIState({
      sidebarCollapsed: true,
      clientCompany: { name: 'Acme Corp', nameEn: 'Acme Corp' },
    });
    render(<MainLayout />);
    const sidebarHeader = screen.getByTestId('sidebar-header');
    expect(sidebarHeader.textContent).not.toContain('Acme Corp');
  });
});
