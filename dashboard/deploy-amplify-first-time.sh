#!/bin/bash

# Amplify Gen 2 First-Time Deployment Script for EC2
# This script sets up and deploys the Amplify backend on a fresh EC2 instance

set -e  # Exit on any error

echo "=========================================="
echo "Amplify Gen 2 First-Time Setup for EC2"
echo "=========================================="
echo ""
echo "This script uses AWS profile: amplify"
echo "See AWS_PROFILE_SETUP.md for setup instructions"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the dashboard directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: Please run this script from the dashboard directory${NC}"
    exit 1
fi

# Function to print section headers
print_header() {
    echo -e "\n${GREEN}==> $1${NC}"
}

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Check prerequisites
print_header "Checking prerequisites..."

if ! command_exists node; then
    echo -e "${RED}Node.js is not installed. Please install Node.js first.${NC}"
    exit 1
fi

if ! command_exists npm; then
    echo -e "${RED}npm is not installed. Please install npm first.${NC}"
    exit 1
fi

echo "Node version: $(node --version)"
echo "npm version: $(npm --version)"

# 2. Check AWS credentials
print_header "Checking AWS credentials..."

if ! command_exists aws; then
    echo -e "${RED}AWS CLI not found. Please install AWS CLI first.${NC}"
    exit 1
fi

# Check if 'amplify' profile exists and works
if aws sts get-caller-identity --profile amplify >/dev/null 2>&1; then
    echo -e "${GREEN}AWS credentials verified for profile 'amplify'.${NC}"
    export AWS_PROFILE=amplify
else
    echo -e "${RED}AWS profile 'amplify' not found or not working.${NC}"
    echo "Please configure the 'amplify' profile using:"
    echo "  aws configure --profile amplify"
    echo ""
    echo "Or check your ~/.aws/credentials and ~/.aws/config files"
    exit 1
fi

# 3. Install dependencies
print_header "Installing dependencies..."

if [ ! -d "node_modules" ]; then
    echo "Installing npm packages..."
    npm install
else
    echo "node_modules exists. Checking for updates..."
    npm install
fi

# 4. Verify Amplify structure
print_header "Verifying Amplify backend structure..."

if [ ! -d "amplify" ]; then
    echo -e "${RED}Error: amplify directory not found${NC}"
    exit 1
fi

if [ ! -f "amplify/backend.ts" ]; then
    echo -e "${RED}Error: amplify/backend.ts not found${NC}"
    exit 1
fi

if [ ! -f "amplify/auth/resource.ts" ]; then
    echo -e "${RED}Error: amplify/auth/resource.ts not found${NC}"
    exit 1
fi

if [ ! -f "amplify/tsconfig.json" ]; then
    echo -e "${YELLOW}Warning: amplify/tsconfig.json not found. Creating it...${NC}"
    cat > amplify/tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "esModuleInterop": true,
    "strict": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "inlineSources": true,
    "outDir": "./build"
  },
  "include": ["**/*.ts"],
  "exclude": ["node_modules", "build", "cdk.out"]
}
EOF
    echo -e "${GREEN}Created amplify/tsconfig.json${NC}"
fi

echo -e "${GREEN}Amplify structure verified successfully.${NC}"

# 5. Clean any existing build artifacts
print_header "Cleaning existing build artifacts..."

rm -rf amplify/build
rm -rf amplify/cdk.out
rm -rf .amplify
rm -rf node_modules/.cache

echo "Cleaned build artifacts."

# 6. Set deployment region
print_header "Configuring deployment region..."
print_header "Configuring deployment region..."

if [ -z "$AWS_REGION" ]; then
    export AWS_REGION="us-east-1"
    echo "AWS_REGION not set. Using default: us-east-1"
else
    echo "Using AWS_REGION: $AWS_REGION"
fi

# 7. Deploy Amplify sandbox
print_header "Deploying Amplify sandbox..."

echo -e "${YELLOW}This will create AWS resources in your account.${NC}"
echo -e "${YELLOW}Press Ctrl+C to cancel, or wait 5 seconds to continue...${NC}"
sleep 5

echo "Starting deployment..."
echo "Using AWS profile: amplify"
npx ampx sandbox --identifier devuser --profile amplify

echo -e "\n${GREEN}=========================================="
echo "Deployment process started successfully!"
echo "==========================================${NC}"
echo ""
echo "The sandbox will continue running in the background."
echo "Monitor the output above for any errors."
echo ""
echo "Once deployment completes, you should see:"
echo "  - Backend synthesized"
echo "  - Type checks completed"
echo "  - CloudFormation stack created/updated"
echo ""
echo "To stop the sandbox, press Ctrl+C"
