/**
 * Environment variable validation tests
 * 
 * This file can be used to test environment variable validation
 * Run with: npx tsx src/lib/env.test.ts (if tsx is installed)
 * Or import and test in your test suite
 */

import { getEnv, validateEnv } from './browser/env';

/**
 * Test environment configuration
 * This is a simple validation script, not a full test suite
 */
export function testEnvConfig(): void {
  console.log('Testing environment configuration...\n');

  // Get env config (lazy-loaded)
  const env = getEnv();

  // Test Entra ID config
  console.log('Entra ID Configuration:');
  console.log('  Tenant ID:', env.entraId.tenantId ? '✓ Set' : '✗ Missing');
  console.log('  Client ID:', env.entraId.clientId ? '✓ Set' : '✗ Missing');
  console.log('  Authority:', env.entraId.authority);

  // Test App URLs
  console.log('\nApplication URLs:');
  console.log('  App URL:', env.app.url);
  console.log('  API URL:', env.app.apiUrl);

  // Test Feature Flags
  console.log('\nFeature Flags:');
  console.log('  Google Sign-In:', env.features.enableGoogleSignIn ? 'Enabled' : 'Disabled');
  console.log('  Email OTP:', env.features.enableEmailOTP ? 'Enabled' : 'Disabled');

  // Test Environment
  console.log('\nEnvironment:');
  console.log('  Development:', env.isDevelopment);
  console.log('  Production:', env.isProduction);

  // Validate
  console.log('\nValidating environment...');
  try {
    validateEnv();
    console.log('  ✓ All required environment variables are set');
  } catch (error) {
    console.error('  ✗ Validation failed:', error instanceof Error ? error.message : error);
  }
}

// Run test if this file is executed directly
if (require.main === module) {
  testEnvConfig();
}
