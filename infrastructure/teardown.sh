#!/bin/bash
set -e

echo "Tearing down ContextAnchor AWS Infrastructure..."

# Ensure we're in the infrastructure directory
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found. Please run this script from the infrastructure directory."
    exit 1
fi

source .venv/bin/activate

if ! command -v cdk &> /dev/null; then
    CDK_CMD="npx aws-cdk"
else
    CDK_CMD="cdk"
fi

# Confirm teardown
read -p "Are you sure you want to destroy all ContextAnchor AWS resources? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Teardown aborted."
    exit 1
fi

# Destroy stacks
echo "Destroying ContextAnchor stack..."
$CDK_CMD destroy --all --force

echo "Teardown complete!"