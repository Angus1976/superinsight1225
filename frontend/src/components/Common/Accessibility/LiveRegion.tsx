/**
 * LiveRegion Component
 * 
 * ARIA live region for screen reader announcements.
 * WCAG 2.1 Success Criterion 4.1.3 - Status Messages
 */

import { memo, useEffect, useState, useCallback, createContext, useContext, ReactNode } from 'react';

// ============================================
// Types
// ============================================

type Politeness = 'polite' | 'assertive' | 'off';

interface Announcement {
  message: string;
  politeness: Politeness;
  id: number;
}

interface LiveRegionContextValue {
  announce: (message: string, politeness?: Politeness) => void;
  announcePolite: (message: string) => void;
  announceAssertive: (message: string) => void;
  clear: () => void;
}

// ============================================
// Context
// ============================================

const LiveRegionContext = createContext<LiveRegionContextValue | null>(null);

// ============================================
// Provider Component
// ============================================

interface LiveRegionProviderProps {
  children: ReactNode;
  clearDelay?: number;
}

export const LiveRegionProvider = memo<LiveRegionProviderProps>(({
  children,
  clearDelay = 5000,
}) => {
  const [politeMessage, setPoliteMessage] = useState('');
  const [assertiveMessage, setAssertiveMessage] = useState('');
  const [messageId, setMessageId] = useState(0);

  const announce = useCallback((message: string, politeness: Politeness = 'polite') => {
    // Increment ID to force re-announcement of same message
    setMessageId(prev => prev + 1);
    
    if (politeness === 'assertive') {
      setAssertiveMessage(message);
    } else {
      setPoliteMessage(message);
    }
  }, []);

  const announcePolite = useCallback((message: string) => {
    announce(message, 'polite');
  }, [announce]);

  const announceAssertive = useCallback((message: string) => {
    announce(message, 'assertive');
  }, [announce]);

  const clear = useCallback(() => {
    setPoliteMessage('');
    setAssertiveMessage('');
  }, []);

  // Auto-clear messages after delay
  useEffect(() => {
    if (politeMessage || assertiveMessage) {
      const timer = setTimeout(clear, clearDelay);
      return () => clearTimeout(timer);
    }
  }, [politeMessage, assertiveMessage, clearDelay, clear, messageId]);

  const contextValue: LiveRegionContextValue = {
    announce,
    announcePolite,
    announceAssertive,
    clear,
  };

  return (
    <LiveRegionContext.Provider value={contextValue}>
      {children}
      
      {/* Polite live region */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        id="a11y-live-region-polite"
      >
        {politeMessage}
      </div>
      
      {/* Assertive live region */}
      <div
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
        id="a11y-live-region-assertive"
      >
        {assertiveMessage}
      </div>
    </LiveRegionContext.Provider>
  );
});

LiveRegionProvider.displayName = 'LiveRegionProvider';

// ============================================
// Hook
// ============================================

export const useLiveRegion = (): LiveRegionContextValue => {
  const context = useContext(LiveRegionContext);
  
  if (!context) {
    // Return no-op functions if used outside provider
    return {
      announce: () => {},
      announcePolite: () => {},
      announceAssertive: () => {},
      clear: () => {},
    };
  }
  
  return context;
};

// ============================================
// Standalone Component
// ============================================

interface LiveRegionProps {
  message: string;
  politeness?: Politeness;
  atomic?: boolean;
  relevant?: 'additions' | 'removals' | 'text' | 'all' | 'additions text';
  className?: string;
}

export const LiveRegion = memo<LiveRegionProps>(({
  message,
  politeness = 'polite',
  atomic = true,
  relevant = 'additions text',
  className = 'sr-only',
}) => {
  const [currentMessage, setCurrentMessage] = useState('');

  // Clear and set message to trigger announcement
  useEffect(() => {
    setCurrentMessage('');
    const timer = requestAnimationFrame(() => {
      setCurrentMessage(message);
    });
    return () => cancelAnimationFrame(timer);
  }, [message]);

  return (
    <div
      role={politeness === 'assertive' ? 'alert' : 'status'}
      aria-live={politeness}
      aria-atomic={atomic}
      aria-relevant={relevant}
      className={className}
    >
      {currentMessage}
    </div>
  );
});

LiveRegion.displayName = 'LiveRegion';

export default LiveRegion;
