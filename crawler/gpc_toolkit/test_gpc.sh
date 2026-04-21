#!/bin/bash
# Test GPC collection on 5 websites

cd "$(dirname "$0")"

echo "Testing GPC data collection on 5 websites..."
echo ""

# Backup original config reference
cp js/cookie_profile_test.js js/cookie_profile_test.js.backup

# Update to use test config
sed -i '' 's|path.join(__dirname, "config.json")|path.join(__dirname, "config_test_gpc.json")|' js/cookie_profile_test.js

# Run test
echo "Running test collection..."
node js/cookie_profile_test.js 2>&1 | tee test_gpc.log

# Restore original
mv js/cookie_profile_test.js.backup js/cookie_profile_test.js

echo ""
echo "Test complete!"
echo ""
echo "Results:"
if [ -f "result/test_gpc_output.csv" ]; then
    echo "   - Output file: result/test_gpc_output.csv"
    echo "   - Total rows: $(wc -l < result/test_gpc_output.csv)"
    echo "   - Headers: $(head -1 result/test_gpc_output.csv)"
    echo ""
    echo "Sample data (first 3 cookies):"
    head -4 result/test_gpc_output.csv | tail -3
else
    echo "   No output file created - check test_gpc.log for errors"
fi

echo ""
echo "Full log saved to: test_gpc.log"
