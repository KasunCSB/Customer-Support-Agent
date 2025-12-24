import tseslint from 'typescript-eslint';
import nextPlugin from '@next/eslint-plugin-next';

const eslintConfig = [
  ...tseslint.configs.recommended,
  {
    plugins: {
      '@next/next': nextPlugin,
    },
    rules: {
      ...nextPlugin.configs.recommended.rules,
      ...nextPlugin.configs['core-web-vitals'].rules,
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      'prefer-const': 'error',
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },
  {
    ignores: ['.next/', 'node_modules/', 'out/', 'dist/', '*.config.js', '*.config.mjs'],
  },
];

export default eslintConfig;
