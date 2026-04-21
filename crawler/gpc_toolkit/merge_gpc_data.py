#!/usr/bin/env python3
"""
Merge GPC data with existing cookie collection results.

This script combines the newly collected GPC data (Profile 5) with
the existing data from other profiles (1, 11, 2, 3, 4, 6, 9).
"""

import pandas as pd
import sys
from datetime import datetime

def merge_gpc_data(scenario):
    """Merge GPC data for a specific scenario (banner_present or banner_not_present)"""

    old_file = f"result/cookies_{scenario}.csv"
    gpc_file = f"result/cookies_{scenario}_gpc.csv"
    output_file = f"result/cookies_{scenario}_complete.csv"
    backup_file = f"result/cookies_{scenario}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    print(f"\nProcessing: {scenario}")
    print("=" * 60)

    # Check if files exist
    try:
        df_old = pd.read_csv(old_file)
        print(f"Loaded existing data: {len(df_old)} rows, {len(df_old.columns)} columns")
    except FileNotFoundError:
        print(f"Error: {old_file} not found!")
        return False

    try:
        df_gpc = pd.read_csv(gpc_file)
        print(f"Loaded GPC data: {len(df_gpc)} rows, {len(df_gpc.columns)} columns")
    except FileNotFoundError:
        print(f"Error: {gpc_file} not found! Run GPC collection first.")
        return False

    # Backup old file
    df_old.to_csv(backup_file, index=False)
    print(f"Backed up existing data to: {backup_file}")

    # Check if gpc_enabled already exists
    if 'gpc_enabled' in df_old.columns:
        print("Warning: gpc_enabled column already exists, dropping it...")
        df_old = df_old.drop('gpc_enabled', axis=1)

    # Merge on website + cookie_name
    print("\nMerging data...")
    df_merged = df_old.merge(
        df_gpc[['website', 'cookie_name', 'gpc_enabled']],
        on=['website', 'cookie_name'],
        how='left'
    )

    # Save merged result
    df_merged.to_csv(output_file, index=False)
    print(f"Saved merged data to: {output_file}")

    # Statistics
    print("\nMerge Statistics:")
    print(f"   - Total rows: {len(df_merged)}")
    print(f"   - Rows with GPC data: {df_merged['gpc_enabled'].notna().sum()}")
    print(f"   - GPC coverage: {100 * df_merged['gpc_enabled'].notna().sum() / len(df_merged):.1f}%")

    # Show column order
    print(f"\nColumn order in output:")
    cols = df_merged.columns.tolist()
    for i, col in enumerate(cols, 1):
        print(f"   {i:2d}. {col}")

    return True

def analyze_gpc_effectiveness():
    """Analyze GPC effectiveness compared to other privacy signals"""

    print("\n\n" + "=" * 60)
    print("GPC EFFECTIVENESS ANALYSIS")
    print("=" * 60)

    for scenario in ['banner_present', 'banner_not_present']:
        file = f"result/cookies_{scenario}_complete.csv"

        try:
            df = pd.read_csv(file)
        except FileNotFoundError:
            print(f"Skipping analysis for {scenario} - file not found")
            continue

        print(f"\n{scenario.replace('_', ' ').title()}")
        print("-" * 60)

        # Count cookies by profile
        profiles = ['initial_cookies', 'do_not_track', 'gpc_enabled', 'consent_reject', 'ublock']
        profile_counts = {}

        for profile in profiles:
            if profile in df.columns:
                count = df[profile].notna().sum()
                profile_counts[profile] = count
                print(f"   {profile:20s}: {count:6d} cookies")

        # Calculate reductions
        if 'initial_cookies' in profile_counts:
            initial = profile_counts['initial_cookies']
            print(f"\n   Reduction from baseline:")

            for profile in ['do_not_track', 'gpc_enabled', 'consent_reject', 'ublock']:
                if profile in profile_counts:
                    count = profile_counts[profile]
                    reduction = 100 * (initial - count) / initial if initial > 0 else 0
                    print(f"      {profile:20s}: {reduction:5.1f}% reduction")

        # Category breakdown for GPC
        if 'category' in df.columns and 'gpc_enabled' in df.columns:
            gpc_cookies = df[df['gpc_enabled'].notna()]
            if len(gpc_cookies) > 0:
                print(f"\n   GPC Cookies by Category:")
                category_counts = gpc_cookies['category'].value_counts()
                for cat, count in category_counts.items():
                    print(f"      {cat:30s}: {count:5d}")

def main():
    print("=" * 60)
    print("GPC DATA MERGE SCRIPT")
    print("=" * 60)

    # Merge both scenarios
    success_bp = merge_gpc_data('banner_present')
    success_nbp = merge_gpc_data('banner_not_present')

    if success_bp or success_nbp:
        # Analyze effectiveness
        analyze_gpc_effectiveness()

        print("\n\nMERGE COMPLETE!")
        print("\nNext steps:")
        print("   1. Review the complete CSV files")
        print("   2. Verify gpc_enabled column is populated")
        print("   3. Use the data in your paper!")
        print("\nOutput files:")
        print("   - result/cookies_banner_present_complete.csv")
        print("   - result/cookies_banner_not_present_complete.csv")
    else:
        print("\nMerge failed! Check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
