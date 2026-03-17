import js from "@eslint/js";
import react from "eslint-plugin-react";
import globals from "globals";

export default [
  {
    ignores: ["node_modules/**", "build/**", "dist/**", "coverage/**"],
  },
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"],
    plugins: {
      react,
    },
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...globals.browser,
        process: "readonly",
      },
    },
    settings: {
      react: {
        version: "detect",
      },
    },
    rules: {
      // Use react plugin recommended rules but turn off ones that conflict with the codebase
      ...react.configs.recommended.rules,

      // The codebase imports React implicitly (React 17+ JSX transform)
      "react/react-in-jsx-scope": "off",

      // Allow prop-types to be skipped since the project doesn't use them
      "react/prop-types": "off",

      // Allow unescaped entities in JSX (common in this codebase)
      "react/no-unescaped-entities": "off",

      // Arrow function components don't need display names
      "react/display-name": "off",

      // Relax unused vars to warn only, allow underscore-prefixed vars
      // Disabled: existing code has some intentionally unused vars (e.g. destructured state)
      "no-unused-vars": "off",
    },
  },
  // Test file overrides - add jest globals
  {
    files: ["**/__tests__/**/*.{js,jsx}", "**/*.test.{js,jsx}", "**/setupTests.js"],
    languageOptions: {
      globals: {
        ...globals.jest,
      },
    },
  },
];
