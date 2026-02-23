#!/bin/bash

# Comprehensive Test Runner for AI Employee System

set -e  # Exit on any error

echo "🚀 AI Employee System Test Runner"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${2}${1}${NC}"
}

# Check if Python is available
if ! command -v python &> /dev/null; then
    print_status "❌ Python not found. Please install Python 3.10+." $RED
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ $(echo "$PYTHON_VERSION < 3.10" | bc -l) -eq 1 ]]; then
    print_status "❌ Python 3.10+ required. Found: $PYTHON_VERSION" $RED
    exit 1
fi
print_status "✅ Python $PYTHON_VERSION detected" $GREEN

# Set environment variables
export SECRET_KEY="test-secret-key-for-testing-12chars"
export JWT_SECRET_KEY="test-jwt-secret-key-for-testing-12chars"
export ENVIRONMENT="test"

# Function to check if API server is running
check_api_server() {
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Start API server if not running
if ! check_api_server; then
    print_status "🔧 Starting API server..." $YELLOW

    # Start server in background
    python ai_employee/api/server.py > server.log 2>&1 &
    SERVER_PID=$!

    # Wait for server to start
    for i in {1..30}; do
        if check_api_server; then
            print_status "✅ API server started (PID: $SERVER_PID)" $GREEN
            break
        fi
        echo -n "."
        sleep 1
    done

    if ! check_api_server; then
        print_status "❌ Failed to start API server" $RED
        print_status "Check server.log for details:" $YELLOW
        tail -20 server.log
        exit 1
    fi
else
    print_status "✅ API server already running" $GREEN
fi

# Run comprehensive tests
print_status "🧪 Running comprehensive tests..." $YELLOW
python test_implementation.py
TEST_EXIT_CODE=$?

# Stop server if we started it
if [ ! -z "$SERVER_PID" ]; then
    print_status "🛑 Stopping API server..." $YELLOW
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
fi

# Check test results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_status "🎉 All tests passed successfully!" $GREEN

    # Show quick summary
    if [ -f "test_report.json" ]; then
        python -c "
import json
with open('test_report.json') as f:
    report = json.load(f)
summary = report['summary']
print(f'📊 Summary: {summary[\"passed\"]}/{summary[\"total\"]} tests passed ({summary[\"pass_rate\"]:.1f}%)')
"
    fi
else
    print_status "❌ Some tests failed" $RED

    # Show failed tests
    if [ -f "test_report.json" ]; then
        python -c "
import json
with open('test_report.json') as f:
    report = json.load(f)
print('\n❌ Failed Tests:')
for result in report['results']:
    if result['status'] == 'FAIL':
        print(f'  - {result[\"test\"]}: {result[\"message\"]}')
"
    fi
fi

# Additional checks
print_status "\n🔍 Additional System Checks..." $YELLOW

# Check critical files
CRITICAL_FILES=(
    "ai_employee/utils/security.py"
    "ai_employee/utils/backup_manager.py"
    "ai_employee/utils/monitoring.py"
    "ai_employee/web/dashboard/index.html"
    "docs/deployment_guide.md"
    "docs/backup_and_restore.md"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        print_status "✅ $file (${size} bytes)" $GREEN
    else
        print_status "❌ $file (missing)" $RED
    fi
done

# Check configuration
if [ -f ".env" ]; then
    print_status "✅ .env file exists" $GREEN
else
    print_status "⚠️  .env file not found (using defaults)" $YELLOW
fi

# Check database
DB_PATH="ai_employee/database/ai_employee.db"
if [ -f "$DB_PATH" ]; then
    size=$(stat -f%z "$DB_PATH" 2>/dev/null || stat -c%s "$DB_PATH" 2>/dev/null)
    print_status "✅ Database exists (${size} bytes)" $GREEN
else
    print_status "⚠️  Database not found (will be created on first run)" $YELLOW
fi

# Print final status
echo ""
echo "=================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_status "🎯 SYSTEM READY FOR PRODUCTION!" $GREEN
    echo ""
    echo "Next steps:"
    echo "1. Review test_report.json for detailed results"
    echo "2. Check deployment documentation in docs/"
    echo "3. Configure production environment variables"
    echo "4. Set up SSL certificates"
    echo "5. Configure monitoring alerts"
else
    print_status "⚠️  SYSTEM NEEDS ATTENTION" $YELLOW
    echo ""
    echo "To fix issues:"
    echo "1. Review failed tests above"
    echo "2. Check server.log for errors"
    echo "3. Verify all dependencies are installed"
    echo "4. Run: pip install -r requirements.txt"
fi
echo "=================================="

exit $TEST_EXIT_CODE