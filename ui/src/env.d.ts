/**
 * Environment Variables Type Definitions
 */

declare namespace NodeJS {
  interface ProcessEnv {
    /** Backend API URL */
    BACKEND_URL?: string;
    /** Node environment */
    NODE_ENV: 'development' | 'production' | 'test';
  }
}
