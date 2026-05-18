import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: 'memoria-nox',
      description: 'Hybrid memory with shadow discipline — yours by design.',
      logo: {
        light: './src/assets/logo-light.svg',
        dark: './src/assets/logo-dark.svg',
        replacesTitle: false,
      },
      social: {
        github: 'https://github.com/totobusnello/memoria-nox',
      },
      editLink: {
        baseUrl: 'https://github.com/totobusnello/memoria-nox/edit/main/',
      },
      customCss: ['./src/styles/custom.css'],
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Installation', slug: 'start/install' },
            { label: 'First Query', slug: 'start/first-query' },
            { label: 'Configuration', slug: 'start/configuration' },
          ],
        },
        {
          label: 'Architecture',
          items: [
            { label: 'Overview', slug: 'architecture/overview' },
            { label: 'Q/A/P Pillars', slug: 'architecture/pillars' },
            { label: 'Schema', slug: 'architecture/schema' },
            { label: 'Architectural Decisions', slug: 'architecture/decisions' },
          ],
        },
        {
          label: 'Pillars',
          items: [
            { label: 'Quality (Q)', slug: 'pillars/quality' },
            { label: 'Autonomy (A)', slug: 'pillars/autonomy' },
            { label: 'Product (P)', slug: 'pillars/product' },
            { label: 'Lab (Research)', slug: 'pillars/lab' },
          ],
        },
        {
          label: 'Security',
          items: [
            { label: 'Threat Model', slug: 'security/threat-model' },
            { label: 'OpenSSF Path', slug: 'security/openssf' },
            { label: 'Vulnerability Reporting', slug: 'security/reporting' },
            { label: 'Dependency Policy', slug: 'security/dependency-policy' },
          ],
        },
        {
          label: 'Operations',
          items: [
            { label: 'Deploy Guide', slug: 'operations/deploy' },
            { label: 'Disaster Recovery', slug: 'operations/disaster-recovery' },
            { label: 'Backup Runbook', slug: 'operations/backup-runbook' },
            { label: 'Monitoring', slug: 'operations/monitoring' },
          ],
        },
        {
          label: 'SDKs',
          items: [
            { label: 'Overview', slug: 'sdks/overview' },
            { label: 'TypeScript', slug: 'sdks/typescript' },
            { label: 'Python', slug: 'sdks/python' },
            { label: 'Rust', slug: 'sdks/rust' },
            { label: 'Go', slug: 'sdks/go' },
          ],
        },
        {
          label: 'API Reference',
          items: [
            { label: 'OpenAPI Spec', slug: 'api/openapi-spec' },
          ],
        },
        {
          label: 'Integrations',
          items: [
            { label: 'Overview', slug: 'integrations/overview' },
            { label: 'IDE Plugins', slug: 'integrations/ide' },
            { label: 'MCP Server', slug: 'integrations/mcp' },
            { label: 'CLI Recipes', slug: 'integrations/cli' },
          ],
        },
        {
          label: 'Strategy',
          items: [
            { label: 'Competitive Positioning', slug: 'strategy/competitive-positioning' },
            { label: 'Cost Model', slug: 'strategy/cost-model' },
          ],
        },
        {
          label: 'Contributing',
          items: [
            { label: 'How to Contribute', slug: 'contributing/how-to' },
            { label: 'Code of Conduct', slug: 'contributing/code-of-conduct' },
            { label: 'Changelog', slug: 'contributing/changelog' },
          ],
        },
      ],
    }),
  ],
  site: 'https://totobusnello.github.io',
  base: '/memoria-nox',
});
