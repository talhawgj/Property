"use client"

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getUserRole, type UserRole } from '@/lib/auth/roles';

interface RoleGuardProps {
  children: React.ReactNode;
  allowedRoles: UserRole[];
  fallbackPath?: string;
  loadingComponent?: React.ReactNode;
}

/**
 * Component that guards routes based on user roles
 * Redirects to fallback path if user doesn't have required role
 */
export function RoleGuard({ 
  children, 
  allowedRoles, 
  fallbackPath = '/user-dashboard',
  loadingComponent 
}: RoleGuardProps) {
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
  const router = useRouter();

  useEffect(() => {
    async function checkRole() {
      const role = await getUserRole();
      
      if (!role) {
        // Not authenticated - let auth flow handle it
        setIsAuthorized(false);
        return;
      }

      const authorized = allowedRoles.includes(role);
      setIsAuthorized(authorized);

      if (!authorized && fallbackPath) {
        router.push(fallbackPath);
      }
    }

    checkRole();
  }, [allowedRoles, fallbackPath, router]);

  if (isAuthorized === null) {
    return loadingComponent || (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-foreground">Checking permissions...</div>
      </div>
    );
  }

  if (!isAuthorized) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-foreground">Access Denied</div>
      </div>
    );
  }

  return <>{children}</>;
}
