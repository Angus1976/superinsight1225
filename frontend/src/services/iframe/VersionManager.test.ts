/**
 * Version Manager Tests
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { VersionManager, LabelStudioVersion } from './VersionManager';

describe('VersionManager', () => {
  let manager: VersionManager;

  beforeEach(() => {
    manager = new VersionManager({ currentVersion: '1.16.0' });
  });

  describe('Initialization', () => {
    it('should initialize with default version', () => {
      const defaultManager = new VersionManager();
      expect(defaultManager.getCurrentVersion()).toBe('latest');
    });

    it('should initialize with specified version', () => {
      expect(manager.getCurrentVersion()).toBe('1.16.0');
    });

    it('should have built-in versions', () => {
      const versions = manager.getAllVersions();
      expect(versions.length).toBeGreaterThan(5);
    });
  });

  describe('getVersionInfo', () => {
    it('should return version info for known version', () => {
      const info = manager.getVersionInfo('1.18.0');
      expect(info).toBeDefined();
      expect(info?.dockerImage).toBe('heartexlabs/label-studio:1.18.0');
      expect(info?.features.length).toBeGreaterThan(0);
    });

    it('should return undefined for unknown version', () => {
      const info = manager.getVersionInfo('0.0.0');
      expect(info).toBeUndefined();
    });

    it('should have latest version', () => {
      const info = manager.getVersionInfo('latest');
      expect(info).toBeDefined();
      expect(info?.dockerImage).toBe('heartexlabs/label-studio:latest');
    });
  });

  describe('getAllVersions', () => {
    it('should return versions sorted by version number', () => {
      const versions = manager.getAllVersions();
      
      // Latest should be first
      expect(versions[0].version).toBe('latest');
      
      // Rest should be in descending order
      for (let i = 2; i < versions.length; i++) {
        const current = parseFloat(versions[i].version);
        const previous = parseFloat(versions[i - 1].version);
        expect(current).toBeLessThanOrEqual(previous);
      }
    });
  });

  describe('getRecommendedVersion', () => {
    it('should return recommended version', () => {
      const recommended = manager.getRecommendedVersion();
      expect(recommended).toBeDefined();
      expect(recommended?.recommended).toBe(true);
    });
  });

  describe('getLTSVersions', () => {
    it('should return LTS versions', () => {
      const ltsVersions = manager.getLTSVersions();
      expect(ltsVersions.length).toBeGreaterThan(0);
      ltsVersions.forEach(v => {
        expect(v.lts).toBe(true);
      });
    });
  });

  describe('checkCompatibility', () => {
    it('should return compatible for same version', () => {
      const result = manager.checkCompatibility('1.16.0', '1.16.0');
      expect(result.compatible).toBe(true);
      expect(result.warnings.length).toBe(0);
    });

    it('should warn about downgrade', () => {
      const result = manager.checkCompatibility('1.18.0', '1.16.0');
      expect(result.warnings.some(w => w.includes('Downgrading'))).toBe(true);
    });

    it('should return incompatible for unknown version', () => {
      const result = manager.checkCompatibility('1.16.0', '0.0.0');
      expect(result.compatible).toBe(false);
      expect(result.warnings).toContain('Unknown version');
    });
  });

  describe('switchVersion', () => {
    it('should switch to new version', async () => {
      const result = await manager.switchVersion('1.18.0');
      
      expect(result.success).toBe(true);
      expect(result.previousVersion).toBe('1.16.0');
      expect(result.newVersion).toBe('1.18.0');
      expect(manager.getCurrentVersion()).toBe('1.18.0');
    });

    it('should generate docker command', async () => {
      const result = await manager.switchVersion('1.18.0');
      
      expect(result.dockerCommand).toContain('docker pull');
      expect(result.dockerCommand).toContain('heartexlabs/label-studio:1.18.0');
    });

    it('should throw for unknown version', async () => {
      await expect(manager.switchVersion('0.0.0')).rejects.toThrow('Unknown version');
    });

    it('should notify listeners on version change', async () => {
      const listener = vi.fn();
      manager.onVersionChange(listener);
      
      await manager.switchVersion('1.18.0');
      
      expect(listener).toHaveBeenCalledWith('1.18.0');
    });
  });

  describe('generateDockerComposeConfig', () => {
    it('should generate valid docker-compose config', () => {
      const config = manager.generateDockerComposeConfig('1.18.0');
      
      expect(config).toContain('version:');
      expect(config).toContain('services:');
      expect(config).toContain('label-studio:');
      expect(config).toContain('heartexlabs/label-studio:1.18.0');
      expect(config).toContain('postgres:');
    });

    it('should throw for unknown version', () => {
      expect(() => {
        manager.generateDockerComposeConfig('0.0.0');
      }).toThrow('Unknown version');
    });
  });

  describe('onVersionChange', () => {
    it('should add and remove listeners', async () => {
      const listener = vi.fn();
      const unsubscribe = manager.onVersionChange(listener);
      
      await manager.switchVersion('1.17.0');
      expect(listener).toHaveBeenCalledTimes(1);
      
      unsubscribe();
      
      await manager.switchVersion('1.18.0');
      expect(listener).toHaveBeenCalledTimes(1); // Still 1, not called again
    });
  });

  describe('checkForUpdates', () => {
    it('should check for updates', async () => {
      const result = await manager.checkForUpdates();
      
      expect(result.currentVersion).toBe('1.16.0');
      expect(result.versions.length).toBeGreaterThan(0);
    });

    it('should detect update available', async () => {
      const oldManager = new VersionManager({ currentVersion: '1.12.0' });
      const result = await oldManager.checkForUpdates();
      
      expect(result.updateAvailable).toBe(true);
    });
  });

  describe('getMigrationGuide', () => {
    it('should generate migration guide', () => {
      const guide = manager.getMigrationGuide('1.16.0', '1.18.0');
      
      expect(guide).toContain('Migration Guide');
      expect(guide).toContain('1.16.0');
      expect(guide).toContain('1.18.0');
      expect(guide).toContain('Backup');
      expect(guide).toContain('docker pull');
    });

    it('should include new features', () => {
      const guide = manager.getMigrationGuide('1.16.0', '1.18.0');
      const v118 = manager.getVersionInfo('1.18.0');
      
      v118?.features.forEach(feature => {
        expect(guide).toContain(feature);
      });
    });

    it('should include rollback procedure', () => {
      const guide = manager.getMigrationGuide('1.16.0', '1.18.0');
      expect(guide).toContain('Rollback');
    });
  });

  describe('compareVersions', () => {
    it('should compare versions correctly', () => {
      const result = manager.compareVersions('1.16.0', '1.18.0');
      
      expect(result.newer).toBe('1.18.0');
      expect(result.older).toBe('1.16.0');
      expect(result.featureDiff.length).toBeGreaterThan(0);
    });

    it('should handle latest version', () => {
      const result = manager.compareVersions('1.18.0', 'latest');
      
      expect(result.newer).toBe('latest');
      expect(result.older).toBe('1.18.0');
    });

    it('should throw for unknown version', () => {
      expect(() => {
        manager.compareVersions('1.16.0', '0.0.0');
      }).toThrow('Unknown version');
    });
  });

  describe('registerVersion', () => {
    it('should register new version', () => {
      const newVersion: LabelStudioVersion = {
        version: '2.0.0',
        dockerImage: 'heartexlabs/label-studio:2.0.0',
        releaseDate: '2026-06-01',
        features: ['Major new feature'],
        breaking: true,
        minApiVersion: '2.0.0',
        recommended: false,
        lts: false,
      };

      manager.registerVersion(newVersion);
      
      const retrieved = manager.getVersionInfo('2.0.0');
      expect(retrieved).toBeDefined();
      expect(retrieved?.breaking).toBe(true);
    });
  });

  describe('Version Properties', () => {
    it('all versions should have required properties', () => {
      const versions = manager.getAllVersions();
      
      versions.forEach(version => {
        expect(version.version).toBeDefined();
        expect(version.dockerImage).toBeDefined();
        expect(version.dockerImage).toContain('heartexlabs/label-studio');
        expect(version.releaseDate).toBeDefined();
        expect(Array.isArray(version.features)).toBe(true);
        expect(typeof version.breaking).toBe('boolean');
        expect(version.minApiVersion).toBeDefined();
        expect(typeof version.recommended).toBe('boolean');
        expect(typeof version.lts).toBe('boolean');
      });
    });

    it('should have exactly one recommended version', () => {
      const versions = manager.getAllVersions();
      const recommendedCount = versions.filter(v => v.recommended).length;
      expect(recommendedCount).toBe(1);
    });
  });
});
