#!/bin/bash
# Run full GPC data collection (Profile 5 only)

cd "$(dirname "$0")"


echo ""
echo "Press Ctrl+C to stop at any time (progress will be saved)"
echo ""
read -p "Press ENTER to start collection..."

# Backup existing results
if [ -f "result/cookies_banner_present_gpc.csv" ]; then
    echo "Backing up existing GPC results..."
    cp result/cookies_banner_present_gpc.csv result/cookies_banner_present_gpc_backup_$(date +%Y%m%d_%H%M%S).csv
fi

# Backup original config reference
echo "Configuring script for GPC-only collection..."
cp js/cookie_profile_test.js js/cookie_profile_test.js.backup

# Update to use GPC-only config
sed -i '' 's|path.join(__dirname, "config.json")|path.join(__dirname, "config_gpc_only.json")|' js/cookie_profile_test.js

# Run full collection
echo ""
echo "Starting collection at $(date)"
echo "Logging to: gpc_collection.log"
echo ""

node js/cookie_profile_test.js 2>&1 | tee gpc_collection.log

# Restore original
mv js/cookie_profile_test.js.backup js/cookie_profile_test.js

echo ""
echo "Collection complete at $(date)!"
echo ""
echo "Results:"
if [ -f "result/cookies_banner_present_gpc.csv" ]; then
    BP_ROWS=$(wc -l < result/cookies_banner_present_gpc.csv)
    echo "   - Banner present: $BP_ROWS rows in cookies_banner_present_gpc.csv"
fi
if [ -f "result/cookies_banner_not_present_gpc.csv" ]; then
    NBP_ROWS=$(wc -l < result/cookies_banner_not_present_gpc.csv)
    echo "   - Banner not present: $NBP_ROWS rows in cookies_banner_not_present_gpc.csv"
fi

echo ""
echo "Full log saved to: gpc_collection.log"
echo ""
echo "Next steps:"
echo "   1. Review the log for any errors"
echo "   2. Run merge_gpc_data.py to combine with existing data"
echo "   3. Verify GPC column is populated"
