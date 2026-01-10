/**
 * Admin utilities for user management
 * These functions should only be called by authenticated admin users
 */

import { signUp, type SignUpInput } from 'aws-amplify/auth';
import { type UserRole } from './roles';

export interface CreateUserInput {
  email: string;
  password: string;
  role: UserRole;
  autoConfirm?: boolean;
}

/**
 * Create a new user with a specific role
 * This function should only be used by admin users
 * 
 * @param input User creation parameters
 * @returns The created user's details
 */
export async function createUserWithRole(input: CreateUserInput) {
  try {
    const signUpParams: SignUpInput = {
      username: input.email,
      password: input.password,
      options: {
        userAttributes: {
          email: input.email,
          'custom:role': input.role,
        },
        // Auto-confirm can be enabled in dev/testing environments
        // In production, users should verify their email
      },
    };

    const { userId, isSignUpComplete, nextStep } = await signUp(signUpParams);

    return {
      success: true,
      userId,
      isSignUpComplete,
      nextStep,
      message: `User created successfully with role: ${input.role}`,
    };
  } catch (error: any) {
    console.error('Error creating user:', error);
    return {
      success: false,
      error: error.message || 'Failed to create user',
    };
  }
}

/**
 * Create an admin user
 * Convenience wrapper for createUserWithRole
 */
export async function createAdminUser(email: string, password: string) {
  return createUserWithRole({
    email,
    password,
    role: 'admin',
  });
}

/**
 * Create a regular user
 * Convenience wrapper for createUserWithRole
 */
export async function createRegularUser(email: string, password: string) {
  return createUserWithRole({
    email,
    password,
    role: 'user',
  });
}

/**
 * Note: To update an existing user's role, you'll need to use AWS Cognito Admin APIs
 * which require AWS SDK and appropriate IAM permissions.
 * This can be implemented in a backend Lambda function.
 * 
 * Example backend implementation needed:
 * - Lambda function with Cognito admin permissions
 * - API endpoint to call the Lambda
 * - Function to call: adminUpdateUserAttributes
 */

export const USER_MANAGEMENT_NOTES = `
# User Management Guide

## Creating Users

### Method 1: Through AWS Cognito Console
1. Go to AWS Cognito Console
2. Select your User Pool
3. Click "Create user"
4. Fill in email and password
5. Add custom attribute: custom:role = "admin" or "user"

### Method 2: Through Code (for admin interfaces)
Use the createUserWithRole() function:

\`\`\`typescript
import { createAdminUser, createRegularUser } from '@/lib/auth/admin';

// Create an admin
await createAdminUser('admin@example.com', 'SecurePass123!');

// Create a regular user
await createRegularUser('user@example.com', 'SecurePass123!');
\`\`\`

### Method 3: AWS CLI
\`\`\`bash
aws cognito-idp admin-create-user \\
  --user-pool-id <your-pool-id> \\
  --username admin@example.com \\
  --user-attributes Name=email,Value=admin@example.com Name=custom:role,Value=admin \\
  --temporary-password TempPass123!
\`\`\`

## Default Behavior
- Users without a role attribute default to "user"
- Admins see the full admin portal
- Regular users are redirected to /user-dashboard

## Updating User Roles
To change a user's role after creation, use AWS Cognito Console:
1. Go to the user in Cognito
2. Edit attributes
3. Set custom:role to "admin" or "user"

Or use AWS CLI:
\`\`\`bash
aws cognito-idp admin-update-user-attributes \\
  --user-pool-id <your-pool-id> \\
  --username user@example.com \\
  --user-attributes Name=custom:role,Value=admin
\`\`\`
`;
