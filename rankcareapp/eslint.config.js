import reactHooks from 'eslint-plugin-react-hooks';

export default [
  {
    ignores: ['.next/**', 'node_modules/**'],
  },
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: {
        console: 'readonly',
        document: 'readonly',
        FileReader: 'readonly',
        localStorage: 'readonly',
        navigator: 'readonly',
        process: 'readonly',
        setInterval: 'readonly',
        setTimeout: 'readonly',
        window: 'readonly',
      },
    },
    plugins: {
      'react-hooks': reactHooks,
    },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
    },
  },
];
