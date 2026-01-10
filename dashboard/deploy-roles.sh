#!/bin/bash

echo "================================"
echo "Deploying User Role System"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "amplify/auth/resource.ts" ]; then
    echo "❌ Error: Please run this script from the saaya-dashboard root directory"
    exit 1
fi

echo "✓ Found amplify directory"
echo ""

# Check for node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
else
    echo "✓ Dependencies already installed"
fi
echo ""

# Deploy Amplify backend
echo "🚀 Deploying Amplify backend with custom user attributes..."
echo ""
echo "This will update your Cognito User Pool to support the custom:role attribute."
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

npx ampx sandbox --once

echo ""
echo "================================"
echo "Deployment Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Create your first admin user (see USER_ROLES_GUIDE.md)"
echo "2. Test login with admin and regular users"
echo "3. Access admin portal at: http://localhost:3000"
echo "4. Regular users will be redirected to: http://localhost:3000/user-dashboard"
echo ""
echo "Documentation: USER_ROLES_GUIDE.md"
echo ""
