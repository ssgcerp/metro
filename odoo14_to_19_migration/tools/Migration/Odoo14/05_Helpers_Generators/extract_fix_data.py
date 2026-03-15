
import pandas as pd
import json
import os

def extract_fix_data(report_file):
    df = pd.read_excel(report_file)
    
    # 1. Handle Duplicates
    matched = df[df['Status'] == 'Matched']
    # Group by O14 payment (Name/ID)
    groups = matched.groupby('Name/ID')
    
    to_delete_ids = []
    summary_dups = []
    
    for name, group in groups:
        if len(group) > 1:
            # Sort by state (prefer posted/paid) and then ID (prefer older/original if applicable)
            # Assuming 'state' values: 'posted', 'draft', 'cancel'
            # We want to keep one.
            sorted_group = group.sort_values(by=['O19 State', 'O19 ID'], ascending=[False, True])
            
            keep_row = sorted_group.iloc[0]
            del_rows = sorted_group.iloc[1:]
            
            to_delete_ids.extend(del_rows['O19 ID'].tolist())
            summary_dups.append({
                'O14 Name': name,
                'Keep ID': keep_row['O19 ID'],
                'Delete IDs': del_rows['O19 ID'].tolist()
            })
            
    # 2. Handle Missing
    missing = df[df['Status'] == 'Missing']
    missing_names = missing['Name/ID'].tolist()
    
    # 3. Save to JSON for the next tool to use
    fix_data = {
        'to_delete_ids': list(set(to_delete_ids)),
        'missing_names': missing_names,
        'summary_duplicates_count': len(summary_dups)
    }
    
    # Debug: Print top 10 largest groups
    summary_dups.sort(key=lambda x: len(x['Delete IDs']), reverse=True)
    print("\nTop 10 largest duplicate groups:")
    for item in summary_dups[:10]:
        print(f"O14: {item['O14 Name']} - Matches: {len(item['Delete IDs']) + 1}")

    with open('cleanup_data.json', 'w') as f:
        json.dump(fix_data, f, indent=4)
        
    print(f"Extracted {len(to_delete_ids)} duplicate IDs and {len(missing_names)} missing names.")
    print("Cleanup data saved to cleanup_data.json")

if __name__ == "__main__":
    # Find latest refined report
    files = [f for f in os.listdir('.') if f.startswith('payment_audit_refined_') and f.endswith('.xlsx')]
    if files:
        latest = sorted(files)[-1]
        extract_fix_data(latest)
    else:
        print("No audit report found.")
