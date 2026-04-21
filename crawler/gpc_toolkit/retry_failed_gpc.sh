#!/bin/bash

# Retry Failed GPC Collection Script
# Attempts to collect cookies from previously failed websites with enhanced settings

echo "================================================"
echo "  GPC Retry Collection for Failed Websites"
echo "================================================"
echo ""

cd "$(dirname "$0")"

# Check if failed_websites.txt exists
if [ ! -f "failed_websites.txt" ]; then
    echo "Error: failed_websites.txt not found!"
    echo "Please wait for main collection to complete first."
    exit 1
fi

FAILED_COUNT=$(wc -l < failed_websites.txt)
echo "Found $FAILED_COUNT failed websites to retry"
echo ""

# Backup existing GPC result files before retry
if [ -f "result/cookies_banner_present_gpc.csv" ]; then
    echo "Backing up existing GPC results..."
    cp result/cookies_banner_present_gpc.csv result/cookies_banner_present_gpc_before_retry.csv
    echo "   Backed up: cookies_banner_present_gpc.csv"
fi

if [ -f "result/cookies_banner_not_present_gpc.csv" ]; then
    cp result/cookies_banner_not_present_gpc.csv result/cookies_banner_not_present_gpc_before_retry.csv
    echo "   Backed up: cookies_banner_not_present_gpc.csv"
fi

echo ""
echo "Starting retry process..."
echo "   - Timeout: 120 seconds (2x original)"
echo "   - Retry attempts: 3 per website"
echo "   - Exponential backoff between retries"
echo ""
echo "Estimated time: $(echo "scale=1; $FAILED_COUNT * 2.5 / 60" | bc) - $(echo "scale=1; $FAILED_COUNT * 4 / 60" | bc) hours"
echo ""
echo "Progress will be logged to: retry_gpc_collection.log"
echo "================================================"
echo ""

# Run the retry script
node js/retry_failed_gpc.js 2>&1 | tee retry_gpc_collection.log

echo ""
echo "Retry process complete!"
echo "Check retry_gpc_collection.log for details"
