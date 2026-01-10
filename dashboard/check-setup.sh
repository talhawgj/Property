#!/bin/bash

# GIS Admin Portal - Quick Start Script
# This script helps verify your setup

echo "=================================="
echo "🚀 GIS Admin Portal Quick Check"
echo "=================================="
echo ""

# Check if node_modules exists
if [ -d "node_modules" ]; then
    echo "✅ Dependencies installed"
else
    echo "❌ Dependencies not installed. Run: npm install"
fi

# Check if .env.local exists
if [ -f ".env.local" ]; then
    echo "✅ Environment file exists (.env.local)"
    
    # Check if required env vars are set
    if grep -q "your_user_pool_id" .env.local; then
        echo "⚠️  User Pool ID not configured - Update .env.local"
    else
        echo "✅ User Pool ID configured"
    fi
    
    if grep -q "your_user_pool_client_id" .env.local; then
        echo "⚠️  Client ID not configured - Update .env.local"
    else
        echo "✅ Client ID configured"
    fi
    
    if grep -q "your_api_key_here" .env.local; then
        echo "⚠️  GIS API Key not configured - Update .env.local"
    else
        echo "✅ GIS API Key configured"
    fi
else
    echo "❌ Environment file missing (.env.local)"
fi

echo ""
echo "=================================="
echo "📚 Next Steps:"
echo "=================================="
echo ""
echo "1. Configure AWS Cognito:"
echo "   → Read AMPLIFY_SETUP.md for detailed instructions"
echo ""
echo "2. Update .env.local with your AWS credentials"
echo ""
echo "3. Create your first admin user in Cognito"
echo ""
echo "4. Start the development server:"
echo "   → npm run dev"
echo ""
echo "5. Visit http://localhost:3000"
echo ""
echo "=================================="
echo "📖 Documentation:"
echo "=================================="
echo "• AMPLIFY_SETUP.md  - AWS Cognito setup guide"
echo "• README.md         - Project overview"
echo "• SETUP_COMPLETE.md - What's been implemented"
echo ""
