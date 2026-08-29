# Merge all GPC data files into a single combined file.
import pandas as pd
import os

print("=" * 70)
print("Merging All GPC Data")
print("=" * 70)
print()

file1 = 'gpc_only_data/cookies_banner_present_gpc.csv'
file2 = 'gpc_only_data/cookies_banner_not_present_gpc.csv'
file3 = 'gpc_only_data/cookies_missing_gpc.csv'
output_file = 'gpc_only_data/all_gpc_data.csv'

dfs = []

print("Loading existing GPC files...")
df1 = pd.read_csv(file1, on_bad_lines='skip')
print(f"  [OK] {file1}: {len(df1)} rows, {df1['website'].nunique()} sites")
dfs.append(df1)

df2 = pd.read_csv(file2, on_bad_lines='skip')
print(f"  [OK] {file2}: {len(df2)} rows, {df2['website'].nunique()} sites")
dfs.append(df2)

if os.path.exists(file3):
    df3 = pd.read_csv(file3, on_bad_lines='skip')
    print(f"  [OK] {file3}: {len(df3)} rows, {df3['website'].nunique()} sites")
    dfs.append(df3)
else:
    print(f"  [WARN] {file3} not found (run collection first)")

print()

print("Merging all data...")
merged_df = pd.concat(dfs, ignore_index=True)

total_rows = len(merged_df)
total_sites = merged_df['website'].nunique()

print(f"  [OK] Total rows: {total_rows}")
print(f"  [OK] Total unique websites: {total_sites}")
print()

if 'gpc_enabled' in merged_df.columns:
    gpc_series = merged_df['gpc_enabled'].astype(str).str.strip()
    gpc_count = (gpc_series.ne('') & gpc_series.ne('nan') & gpc_series.ne('None')).sum()
    print(f"  [OK] Total GPC cookies: {gpc_count}")
print()

print(f"Saving merged file: {output_file}")
merged_df.to_csv(output_file, index=False)
print(f"  [OK] Saved {total_rows} rows")
print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Combined {len(dfs)} files")
print(f"Total websites: {total_sites}")
print(f"Total cookies: {total_rows}")
print(f"Output: {output_file}")
print("=" * 70)
