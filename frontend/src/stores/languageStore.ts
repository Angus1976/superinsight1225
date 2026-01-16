/**
 * Language Store
 * 
 * Centralized language state management with:
 * - react-i18next integration
 * - Label Studio iframe synchronization via postMessage
 * - localStorage persistence
 * - Backend API notification
 * - UI Store synchronization
 * 
 * Design Principles:
 * 1. 项目前端用自己的 i18n 切换 (react-i18next)
 * 2. Label Studio 用官方语言切换 (内置中文支持)
 * 3. 全局状态管理 (Zustand) 同步中/英
 * 4. 最小干扰: 配置驱动 + iframe postMessage
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import i18n from '@/locales/config';
import { DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, type SupportedLanguage } from '@/constants';

// Label Studio postMessage types
export interface LabelStudioLanguageMessage {
  type: 'setLanguage' | 'languageChanged';
  lang: SupportedLanguage;
  source?: 'superinsight' | 'label-studio';
}

// Allowed origins for postMessage security
const ALLOWED_ORIGINS = [
  window.location.origin,
  'http://localhost:8080',
  'http://label-studio:8080',
];

interface LanguageState {
  language: SupportedLanguage;
  isInitialized: boolean;
  labelStudioSynced: boolean;
  
  // Actions
  setLanguage: (lang: SupportedLanguage) => void;
  syncToLabelStudio: () => void;
  initializeLanguage: () => void;
  handleLabelStudioMessage: (event: MessageEvent) => void;
}

export const useLanguageStore = create<LanguageState>()(
  persist(
    (set, get) => ({
      language: DEFAULT_LANGUAGE,
      isInitialized: false,
      labelStudioSynced: false,

      /**
       * Set language and synchronize across all systems
       * 1. Update Zustand state
       * 2. Update react-i18next
       * 3. Sync to Label Studio iframe
       * 4. Notify backend API (optional)
       * 5. Sync with UI Store
       */
      setLanguage: (lang: SupportedLanguage) => {
        // Validate language
        if (!SUPPORTED_LANGUAGES.includes(lang)) {
          console.warn(`[LanguageStore] Invalid language: ${lang}, falling back to ${DEFAULT_LANGUAGE}`);
          lang = DEFAULT_LANGUAGE;
        }

        // 1. Update Zustand state
        set({ language: lang });

        // 2. Update react-i18next
        i18n.changeLanguage(lang);

        // 3. Update document lang attribute for accessibility
        document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';

        // 4. Sync to Label Studio
        get().syncToLabelStudio();

        // 5. Notify backend API (fire and forget)
        fetch('/api/settings/language', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ language: lang }),
        }).catch(() => {
          // Silently ignore API errors - language is already saved locally
        });

        console.log(`[LanguageStore] Language changed to: ${lang}`);
      },

      /**
       * Sync language to Label Studio iframe via postMessage
       */
      syncToLabelStudio: () => {
        const { language } = get();
        
        // Find all Label Studio iframes
        const iframes = document.querySelectorAll<HTMLIFrameElement>('iframe[data-label-studio]');
        
        if (iframes.length === 0) {
          // No Label Studio iframes found, mark as synced anyway
          set({ labelStudioSynced: true });
          return;
        }

        iframes.forEach((iframe) => {
          if (iframe.contentWindow) {
            const message: LabelStudioLanguageMessage = {
              type: 'setLanguage',
              lang: language,
              source: 'superinsight',
            };
            
            // Send to all allowed origins
            ALLOWED_ORIGINS.forEach((origin) => {
              try {
                iframe.contentWindow?.postMessage(message, origin);
              } catch (error) {
                // Ignore cross-origin errors
              }
            });
          }
        });

        set({ labelStudioSynced: true });
        console.log(`[LanguageStore] Synced language to Label Studio: ${language}`);
      },

      /**
       * Initialize language on app startup
       * - Restore from localStorage (handled by persist middleware)
       * - Sync with react-i18next
       * - Set document lang attribute
       */
      initializeLanguage: () => {
        const { language, isInitialized } = get();
        
        if (isInitialized) return;

        // Sync with react-i18next
        if (i18n.language !== language) {
          i18n.changeLanguage(language);
        }

        // Set document lang attribute
        document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';

        set({ isInitialized: true });
        console.log(`[LanguageStore] Initialized with language: ${language}`);
      },

      /**
       * Handle incoming messages from Label Studio
       * Used when Label Studio changes language internally
       */
      handleLabelStudioMessage: (event: MessageEvent) => {
        // Security: Validate origin
        if (!ALLOWED_ORIGINS.includes(event.origin)) {
          return;
        }

        // Validate message structure
        const data = event.data as LabelStudioLanguageMessage;
        if (
          data?.type === 'languageChanged' &&
          data?.source === 'label-studio' &&
          SUPPORTED_LANGUAGES.includes(data.lang)
        ) {
          const { language } = get();
          
          // Only update if different to avoid loops
          if (data.lang !== language) {
            console.log(`[LanguageStore] Received language change from Label Studio: ${data.lang}`);
            get().setLanguage(data.lang);
          }
        }
      },
    }),
    {
      name: 'language-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        language: state.language,
      }),
      onRehydrateStorage: () => (state) => {
        // Initialize after rehydration
        if (state) {
          state.initializeLanguage();
        }
      },
    }
  )
);

/**
 * Setup global message listener for Label Studio communication
 * Call this once in app initialization
 */
export function setupLabelStudioLanguageListener(): () => void {
  const handleMessage = (event: MessageEvent) => {
    useLanguageStore.getState().handleLabelStudioMessage(event);
  };

  window.addEventListener('message', handleMessage);
  
  return () => {
    window.removeEventListener('message', handleMessage);
  };
}

/**
 * Get Label Studio URL with language parameter
 */
export function getLabelStudioUrl(baseUrl: string, projectId: string | number): string {
  const { language } = useLanguageStore.getState();
  const langParam = language === 'zh' ? 'zh' : 'en';
  return `${baseUrl}/projects/${projectId}?lang=${langParam}`;
}
