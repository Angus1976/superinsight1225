/**
 * SkipLinks Component
 * 
 * Provides skip navigation links for keyboard users to bypass repetitive content.
 * WCAG 2.1 Success Criterion 2.4.1 - Bypass Blocks
 */

import { memo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import './SkipLinks.scss';

interface SkipLink {
  targetId: string;
  label: string;
}

interface SkipLinksProps {
  links?: SkipLink[];
  mainContentId?: string;
  navigationId?: string;
  searchId?: string;
}

const defaultLinks: SkipLink[] = [
  { targetId: 'main-content', label: 'skipLinks.mainContent' },
  { targetId: 'main-navigation', label: 'skipLinks.navigation' },
];

export const SkipLinks = memo<SkipLinksProps>(({
  links = defaultLinks,
  mainContentId = 'main-content',
  navigationId = 'main-navigation',
  searchId,
}) => {
  const { t } = useTranslation('common');

  const handleSkipClick = useCallback((e: React.MouseEvent<HTMLAnchorElement>, targetId: string) => {
    e.preventDefault();
    const target = document.getElementById(targetId);
    
    if (target) {
      // Make the target focusable temporarily
      target.setAttribute('tabindex', '-1');
      target.focus();
      
      // Scroll into view
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      
      // Remove tabindex after blur to maintain natural tab order
      const handleBlur = () => {
        target.removeAttribute('tabindex');
        target.removeEventListener('blur', handleBlur);
      };
      target.addEventListener('blur', handleBlur);
    }
  }, []);

  const allLinks = [
    ...links,
    ...(searchId ? [{ targetId: searchId, label: 'skipLinks.search' }] : []),
  ];

  return (
    <nav className="skip-links-container" aria-label={t('skipLinks.navigation', 'Skip navigation')}>
      {allLinks.map(({ targetId, label }) => (
        <a
          key={targetId}
          href={`#${targetId}`}
          className="skip-link"
          onClick={(e) => handleSkipClick(e, targetId)}
        >
          {t(label, label)}
        </a>
      ))}
    </nav>
  );
});

SkipLinks.displayName = 'SkipLinks';

export default SkipLinks;
