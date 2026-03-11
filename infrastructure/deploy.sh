#!/bin/bash
set -e

echo "Deploying ContextAnchor AWS Infrastructure..."

# Check prerequisites
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js (>= 18.0.0) first."
    exit 1
fi

if ! command -v npx &> /dev/null; then
    echo "Error: npx is not installed. Please install npm/npx first."
    exit 1
fi

if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.11+ first."
    exit 1
fi

# Ensure we're in the infrastructure directory
cd "$(dirname "$0")"

# Set up virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt -r requirements-dev.txt -q

# Install AWS CDK locally if not installed globally
if ! command -v cdk &> /dev/null; then
    echo "AWS CDK not found globally. It will be run via npx."
    CDK_CMD="npx aws-cdk"
else
    CDK_CMD="cdk"
fi

# Bootstrap environment if needed (optional, could be commented out if already bootstrapped)
echo "Bootstrapping AWS CDK environment..."
$CDK_CMD bootstrap

# Run tests before deployment
echo "Running infrastructure unit tests..."
pytest tests/

# Synthesize CloudFormation template
echo "Synthesizing CloudFormation template..."
$CDK_CMD synth

# Deploy stacks
echo "Deploying ContextAnchor stack..."
$CDK_CMD deploy --all --require-approval never

echo "Deployment complete! You can now configure your ContextAnchor CLI with the API endpoint provided in the outputs."