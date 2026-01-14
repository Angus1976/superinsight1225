/**
 * Label Studio Version Manager
 * 
 * Manages Label Studio container versions and enables quick switching
 * between different versions of the open-source Label Studio.
 * 
 * Official Docker image: heartexlabs/label-studio
 * Documentation: https://labelstud.io/guide/install
 * 
 * @module VersionManager
 */

export interface LabelStudioVersion {
  version: string;
  dockerImage: string;
  releaseDate: string;
  features: string[];
  breaking: boolean;
  minApiVersion: string;
  recommended: boolean;
  lts: boolean;
}

export interface VersionCompatibility {
  compatible: boolean;
  warnings: string[];
  requiredMigrations: string[];
}

export interface VersionManagerConfig {
  currentVersion?: string;
  dockerRegistry?: string;
  autoUpdate?: boolean;
  checkInterval?: number; // ms
}

export interface VersionCheckResult {
  currentVersion: string;
  latestVersion: string;
  updateAvailable: boolean;
  versions: LabelStudioVersion[];
}

/**
 * Manages Label Studio versions and container switching
 */
export class VersionManager {
  private config: VersionManagerConfig;
  private versions: Map<string, LabelStudioVersion> = new Map();
  private currentVersion: string;
  private listeners: Set<(version: string) => void> = new Set();

  constructor(config: VersionManagerConfig = {}) {
    this.config = {
      dockerRegistry: 'heartexlabs/label-studio',
      autoUpdate: false,
      checkInterval: 86400000, // 24 hours
      ...config,
    };
    this.currentVersion = config.currentVersion || 'latest';
    this.initializeKnownVersions();
  }

  private initializeKnownVersions(): void {
    // Register known stable versions
    // Based on official releases from https://github.com/HumanSignal/label-studio
    
    this.registerVersion({
      version: '1.18.0',
      dockerImage: 'heartexlabs/label-studio:1.18.0',
      releaseDate: '2025-12-01',
      features: [
        'Enhanced LLM evaluation templates',
        'Improved performance for large datasets',
        'New video annotation tools',
        'Better React integration',
      ],
      breaking: false,
      minApiVersion: '1.0.0',
      recommended: true,
      lts: true,
    });

    this.registerVersion({
      version: '1.17.0',
      dockerImage: 'heartexlabs/label-studio:1.17.0',
      releaseDate: '2025-10-15',
      features: [
        'RLHF support improvements',
        'New audio waveform visualization',
        'Enhanced export formats',
      ],
      breaking: false,
      minApiVersion: '1.0.0',
      recommended: false,
      lts: false,
    });

    this.registerVersion({
      version: '1.16.0',
      dockerImage: 'heartexlabs/label-studio:1.16.0',
      releaseDate: '2025-08-20',
      features: [
        'Multi-page document annotation',
        'Improved NER performance',
        'New keyboard shortcuts',
      ],
      breaking: false,
      minApiVersion: '1.0.0',
      recommended: false,
      lts: false,
    });

    this.registerVersion({
      version: '1.15.0',
      dockerImage: 'heartexlabs/label-studio:1.15.0',
      releaseDate: '2025-06-10',
      features: [
        'Time series improvements',
        'Better polygon tools',
        'Enhanced API',
      ],
      breaking: false,
      minApiVersion: '1.0.0',
      recommended: false,
      lts: false,
    });

    this.registerVersion({
      version: '1.14.0',
      dockerImage: 'heartexlabs/label-studio:1.14.0',
      releaseDate: '2025-04-01',
      features: [
        'Video timeline segmentation',
        'Improved brush tools',
        'New export options',
      ],
      breaking: false,
      minApiVersion: '1.0.0',
      recommended: false,
      lts: false,
    });

    this.registerVersion({
      version: '1.13.0',
      dockerImage: 'heartexlabs/label-studio:1.13.0',
      releaseDate: '2025-02-15',
      features: [
        'LLM fine-tuning templates',
        'Improved collaboration features',
        'Better performance',
      ],
      breaking: false,
      minApiVersion: '1.0.0',
      recommended: false,
      lts: false,
    });

    this.registerVersion({
      version: '1.12.0',
      dockerImage: 'heartexlabs/label-studio:1.12.0',
      releaseDate: '2024-12-01',
      features: [
        'Enhanced ML backend integration',
        'New annotation tools',
        'Improved UI',
      ],
      breaking: false,
      minApiVersion: '1.0.0',
      recommended: false,
      lts: true,
    });

    this.registerVersion({
      version: 'latest',
      dockerImage: 'heartexlabs/label-studio:latest',
      releaseDate: 'rolling',
      features: ['Latest features and fixes'],
      breaking: false,
      minApiVersion: '1.0.0',
      recommended: false,
      lts: false,
    });
  }

  /**
   * Register a new version
   */
  registerVersion(version: LabelStudioVersion): void {
    this.versions.set(version.version, version);
  }

  /**
   * Get current version
   */
  getCurrentVersion(): string {
    return this.currentVersion;
  }

  /**
   * Get version info
   */
  getVersionInfo(version: string): LabelStudioVersion | undefined {
    return this.versions.get(version);
  }

  /**
   * Get all available versions
   */
  getAllVersions(): LabelStudioVersion[] {
    return Array.from(this.versions.values())
      .sort((a, b) => {
        if (a.version === 'latest') return -1;
        if (b.version === 'latest') return 1;
        return b.version.localeCompare(a.version, undefined, { numeric: true });
      });
  }

  /**
   * Get recommended version
   */
  getRecommendedVersion(): LabelStudioVersion | undefined {
    return Array.from(this.versions.values()).find(v => v.recommended);
  }

  /**
   * Get LTS versions
   */
  getLTSVersions(): LabelStudioVersion[] {
    return Array.from(this.versions.values()).filter(v => v.lts);
  }

  /**
   * Check compatibility between versions
   */
  checkCompatibility(
    fromVersion: string, 
    toVersion: string
  ): VersionCompatibility {
    const from = this.versions.get(fromVersion);
    const to = this.versions.get(toVersion);

    if (!from || !to) {
      return {
        compatible: false,
        warnings: ['Unknown version'],
        requiredMigrations: [],
      };
    }

    const warnings: string[] = [];
    const requiredMigrations: string[] = [];

    // Check for breaking changes
    if (to.breaking) {
      warnings.push(`Version ${to.version} contains breaking changes`);
    }

    // Check API version compatibility
    if (from.minApiVersion !== to.minApiVersion) {
      warnings.push('API version mismatch - some features may not work');
    }

    // Downgrade warning
    if (fromVersion !== 'latest' && toVersion !== 'latest') {
      const fromNum = parseFloat(fromVersion);
      const toNum = parseFloat(toVersion);
      if (toNum < fromNum) {
        warnings.push('Downgrading may cause data compatibility issues');
        requiredMigrations.push('Backup database before downgrade');
      }
    }

    return {
      compatible: warnings.length === 0,
      warnings,
      requiredMigrations,
    };
  }

  /**
   * Switch to a different version
   */
  async switchVersion(targetVersion: string): Promise<{
    success: boolean;
    previousVersion: string;
    newVersion: string;
    dockerCommand: string;
    warnings: string[];
  }> {
    const versionInfo = this.versions.get(targetVersion);
    if (!versionInfo) {
      throw new Error(`Unknown version: ${targetVersion}`);
    }

    const compatibility = this.checkCompatibility(this.currentVersion, targetVersion);
    const previousVersion = this.currentVersion;

    // Generate Docker commands for version switch
    const dockerCommand = this.generateDockerSwitchCommand(versionInfo);

    // Update current version
    this.currentVersion = targetVersion;

    // Notify listeners
    this.listeners.forEach(listener => listener(targetVersion));

    return {
      success: true,
      previousVersion,
      newVersion: targetVersion,
      dockerCommand,
      warnings: compatibility.warnings,
    };
  }

  /**
   * Generate Docker command for version switch
   */
  private generateDockerSwitchCommand(version: LabelStudioVersion): string {
    return `# Stop current container
docker-compose stop label-studio

# Pull new version
docker pull ${version.dockerImage}

# Update docker-compose.yml to use: ${version.dockerImage}
# Then restart:
docker-compose up -d label-studio

# Verify version
docker exec label-studio label-studio --version`;
  }

  /**
   * Generate docker-compose configuration for a version
   */
  generateDockerComposeConfig(version: string): string {
    const versionInfo = this.versions.get(version);
    if (!versionInfo) {
      throw new Error(`Unknown version: ${version}`);
    }

    return `# Label Studio Docker Compose Configuration
# Version: ${version}
# Generated: ${new Date().toISOString()}

version: '3.8'

services:
  label-studio:
    image: ${versionInfo.dockerImage}
    container_name: label-studio
    ports:
      - "8080:8080"
    volumes:
      - label-studio-data:/label-studio/data
    environment:
      - LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true
      - LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=/label-studio/files
      - DJANGO_DB=default
      - POSTGRE_NAME=\${POSTGRES_DB:-labelstudio}
      - POSTGRE_USER=\${POSTGRES_USER:-labelstudio}
      - POSTGRE_PASSWORD=\${POSTGRES_PASSWORD:-labelstudio}
      - POSTGRE_HOST=\${POSTGRES_HOST:-postgres}
      - POSTGRE_PORT=\${POSTGRES_PORT:-5432}
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    container_name: label-studio-postgres
    environment:
      - POSTGRES_DB=\${POSTGRES_DB:-labelstudio}
      - POSTGRES_USER=\${POSTGRES_USER:-labelstudio}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD:-labelstudio}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  label-studio-data:
  postgres-data:
`;
  }

  /**
   * Add version change listener
   */
  onVersionChange(listener: (version: string) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Check for updates
   */
  async checkForUpdates(): Promise<VersionCheckResult> {
    const allVersions = this.getAllVersions();
    const latestStable = allVersions.find(v => v.version !== 'latest' && v.recommended);
    
    return {
      currentVersion: this.currentVersion,
      latestVersion: latestStable?.version || 'latest',
      updateAvailable: latestStable ? 
        this.currentVersion !== latestStable.version && this.currentVersion !== 'latest' : 
        false,
      versions: allVersions,
    };
  }

  /**
   * Get migration guide between versions
   */
  getMigrationGuide(fromVersion: string, toVersion: string): string {
    const from = this.versions.get(fromVersion);
    const to = this.versions.get(toVersion);

    if (!from || !to) {
      return 'Unknown version - please check version numbers';
    }

    return `# Migration Guide: ${fromVersion} → ${toVersion}

## Pre-Migration Checklist
- [ ] Backup your database
- [ ] Export all projects
- [ ] Document custom configurations

## Migration Steps

1. **Stop Label Studio**
   \`\`\`bash
   docker-compose stop label-studio
   \`\`\`

2. **Backup Data**
   \`\`\`bash
   docker exec label-studio-postgres pg_dump -U labelstudio labelstudio > backup.sql
   \`\`\`

3. **Update Docker Image**
   \`\`\`bash
   docker pull ${to.dockerImage}
   \`\`\`

4. **Update docker-compose.yml**
   Change image to: \`${to.dockerImage}\`

5. **Start Label Studio**
   \`\`\`bash
   docker-compose up -d label-studio
   \`\`\`

6. **Verify Migration**
   - Check all projects load correctly
   - Verify annotations are intact
   - Test annotation workflow

## New Features in ${toVersion}
${to.features.map(f => `- ${f}`).join('\n')}

## Rollback Procedure
If issues occur:
\`\`\`bash
docker-compose stop label-studio
docker pull ${from.dockerImage}
# Restore backup if needed
docker-compose up -d label-studio
\`\`\`
`;
  }

  /**
   * Get version comparison
   */
  compareVersions(version1: string, version2: string): {
    newer: string;
    older: string;
    featureDiff: string[];
  } {
    const v1 = this.versions.get(version1);
    const v2 = this.versions.get(version2);

    if (!v1 || !v2) {
      throw new Error('Unknown version');
    }

    const v1Num = version1 === 'latest' ? Infinity : parseFloat(version1);
    const v2Num = version2 === 'latest' ? Infinity : parseFloat(version2);

    const newer = v1Num >= v2Num ? version1 : version2;
    const older = v1Num < v2Num ? version1 : version2;

    const newerInfo = this.versions.get(newer)!;
    const olderInfo = this.versions.get(older)!;

    const featureDiff = newerInfo.features.filter(
      f => !olderInfo.features.includes(f)
    );

    return { newer, older, featureDiff };
  }
}

export default VersionManager;
