#!/bin/bash

echo "========================================"
echo "  GPC Missing Websites Collection"
echo "========================================"
echo ""
echo "Websites to collect: $(wc -l < websites_to_collect_gpc.txt)"
echo ""
echo "Starting collection..."
echo ""

node collect_missing_gpc.js

echo ""
echo "Collection completed!"
echo "Check missing_gpc_collection.log for details"
