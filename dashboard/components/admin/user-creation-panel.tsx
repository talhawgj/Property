"use client"

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { createAdminUser, createRegularUser } from '@/lib/auth/admin';
import { UserPlus, Shield, User as UserIcon } from 'lucide-react';

export function UserCreationPanel() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  const handleCreateUser = async (role: 'admin' | 'user') => {
    if (!email || !password) {
      setMessage({ type: 'error', text: 'Email and password are required' });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const result = role === 'admin' 
        ? await createAdminUser(email, password)
        : await createRegularUser(email, password);

      if (result.success) {
        setMessage({ type: 'success', text: result.message || 'User created successfully' });
        setEmail('');
        setPassword('');
      } else {
        setMessage({ type: 'error', text: result.error || 'Failed to create user' });
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'An error occurred' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary/10 rounded">
          <UserPlus className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground">Create New User</h3>
          <p className="text-sm text-muted-foreground">Add admin or regular users to the system</p>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-foreground mb-2">
            Email
          </label>
          <Input
            id="email"
            type="email"
            placeholder="user@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-foreground mb-2">
            Password
          </label>
          <Input
            id="password"
            type="password"
            placeholder="Min 8 chars, include uppercase, lowercase, numbers, symbols"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={loading}
          />
          <p className="text-xs text-muted-foreground mt-1">
            Must be at least 8 characters with uppercase, lowercase, numbers, and symbols
          </p>
        </div>

        <div className="flex gap-3 pt-2">
          <Button
            onClick={() => handleCreateUser('admin')}
            disabled={loading}
            className="flex-1 gap-2"
            variant="default"
          >
            <Shield className="w-4 h-4" />
            Create Admin
          </Button>
          <Button
            onClick={() => handleCreateUser('user')}
            disabled={loading}
            className="flex-1 gap-2"
            variant="outline"
          >
            <UserIcon className="w-4 h-4" />
            Create User
          </Button>
        </div>

        {message && (
          <div className={`p-3 rounded ${
            message.type === 'success' 
              ? 'bg-green-500/10 text-green-600 border border-green-500/20' 
              : 'bg-red-500/10 text-red-600 border border-red-500/20'
          }`}>
            <p className="text-sm">{message.text}</p>
          </div>
        )}
      </div>

      <div className="mt-6 pt-6 border-t border-border">
        <h4 className="text-sm font-medium text-foreground mb-3">Role Descriptions</h4>
        <div className="space-y-2 text-sm">
          <div className="flex items-start gap-2">
            <Badge variant="default" className="mt-0.5">Admin</Badge>
            <p className="text-muted-foreground">
              Full access to admin portal, analytics, property catalogue, and all features
            </p>
          </div>
          <div className="flex items-start gap-2">
            <Badge variant="outline" className="mt-0.5">User</Badge>
            <p className="text-muted-foreground">
              Access to personal dashboard with limited features
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
}
