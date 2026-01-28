// Main App component - Full version
import { useEffect } from 'react';
import { ConfigProvider, App as AntApp, theme } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import zhCN from 'antd/locale/zh_CN';
import enUS from 'antd/locale/en_US';
import { useUIStore } from '@/stores/uiStore';
import { useLanguageStore, setupLabelStudioLanguageListener } from '@/stores/languageStore';
import { AppRouter } from '@/router';
import { ErrorBoundary } from '@/components/Common/ErrorBoundary';
import { THEMES } from '@/constants';
import { lightTheme, darkTheme } from '@/styles/theme';

// Import i18n config
import '@/locales/config';

// Import global styles
import '@/styles/global.scss';

// Create Query Client with optimized cache settings
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      // Reduce stale time to ensure fresh data on navigation
      staleTime: 30000, // 30 seconds
      // Enable cache time but keep it short
      gcTime: 5 * 60 * 1000, // 5 minutes (formerly cacheTime)
      // Refetch on mount if data is stale
      refetchOnMount: true,
    },
  },
});

function App() {
  const { theme: currentTheme, language: uiLanguage, setLanguage: setUILanguage } = useUIStore();
  const { language: langStoreLanguage, initializeLanguage, setLanguage: setLangStoreLanguage } = useLanguageStore();

  // Initialize language store and set up Label Studio listener
  useEffect(() => {
    initializeLanguage();
    const cleanup = setupLabelStudioLanguageListener();
    return cleanup;
  }, [initializeLanguage]);

  // Sync language between UI store and language store
  useEffect(() => {
    if (uiLanguage !== langStoreLanguage) {
      // UI store changed, sync to language store
      setLangStoreLanguage(uiLanguage);
    }
  }, [uiLanguage, langStoreLanguage, setLangStoreLanguage]);

  // Use the language from language store (which handles Label Studio sync)
  const language = langStoreLanguage;

  // Get the appropriate theme configuration
  const themeConfig = currentTheme === THEMES.DARK ? darkTheme : lightTheme;

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={language === 'zh' ? zhCN : enUS}
        theme={{
          algorithm: currentTheme === THEMES.DARK ? theme.darkAlgorithm : theme.defaultAlgorithm,
          ...themeConfig,
        }}
      >
        <AntApp>
          <ErrorBoundary>
            <AppRouter />
          </ErrorBoundary>
        </AntApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;
