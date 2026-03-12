#!/bin/bash
set -e

echo "Tearing down ContextAnchor AWS Infrastructure..."

# Ensure we're in the infrastructure directory
cd "$(dirname "$0")"

# Region handling
REGION=$(aws configure get region || echo "eu-north-1")
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            REGION="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo "Attempting teardown in region: $REGION"

# Check for stacks in other common regions to warn user
for CHECK_REGION in "us-east-1" "eu-north-1"; do
    if [ "$CHECK_REGION" != "$REGION" ]; then
        STACK_COUNT=$(aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE ROLLBACK_COMPLETE --region "$CHECK_REGION" --query "StackSummaries[?contains(StackName, 'ContextAnchor')].StackName" --output text | wc -w)
        if [ "$STACK_COUNT" -gt 0 ]; then
            echo "Warning: Found $STACK_COUNT ContextAnchor stack(s) in $CHECK_REGION. You may need to run teardown --region $CHECK_REGION separately."
        fi
    fi
done

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
read -p "Are you sure you want to destroy all ContextAnchor AWS resources in $REGION? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Teardown aborted."
    exit 1
fi

# Destroy stacks
echo "Destroying ContextAnchor stacks in $REGION..."
$CDK_CMD destroy --all --force --region "$REGION"

echo "Teardown complete for region $REGION!"