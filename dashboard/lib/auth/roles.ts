/**
 * User role management utilities
 */

import { fetchAuthSession, fetchUserAttributes, getCurrentUser } from 'aws-amplify/auth';

export type UserRole = 'admin' | 'user';

/**
 * Get the current user's role
 * @returns The user's role or null if not authenticated
 */
export async function getUserRole(): Promise<UserRole | null> {
  try {
    const attributes = await fetchUserAttributes();
    const role = attributes['custom:role'] as UserRole | undefined;
    
    // Default to 'user' if no role is set
    return role || 'user';
  } catch (error) {
    console.error('Error fetching user role:', error);
    return null;
  }
}

/**
 * Check if the current user is an admin
 * @returns true if user is an admin, false otherwise
 */
export async function isAdmin(): Promise<boolean> {
  const role = await getUserRole();
  return role === 'admin';
}

/**
 * Check if the current user is a regular user
 * @returns true if user is a regular user, false otherwise
 */
export async function isRegularUser(): Promise<boolean> {
  const role = await getUserRole();
  return role === 'user';
}

/**
 * Get current user information including role
 */
export async function getCurrentUserInfo() {
  try {
    const user = await getCurrentUser();
    const attributes = await fetchUserAttributes();
    const role = (attributes['custom:role'] as UserRole) || 'user';
    
    return {
      userId: user.userId,
      username: user.username,
      email: attributes.email,
      role,
      attributes,
    };
  } catch (error) {
    console.error('Error fetching user info:', error);
    return null;
  }
}
