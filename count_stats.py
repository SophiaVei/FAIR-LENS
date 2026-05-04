import pandas as pd

def run():
    # Final results stats
    df_tri = pd.read_csv('outputs/tri_results_master.csv')
    rel = df_tri[df_tri['relevant'] == True]
    print(f"Final Unique Papers: {rel['title'].nunique()}")
    print(f"Final Unique Venues: {rel['venue'].nunique()}")
    
    # Screening stats (Title & Abstract)
    # We need to look at the total pool BEFORE title/abs screening.
    # lens.py outputs 'outputs/prefilter_results.csv' (all records after basic filters)
    # and 'outputs/prefilter_kept.csv' (matched records)
    
    df_lens = pd.read_csv('data/raw/lens.csv')
    
    kept_count = len(df_lens)
    
    # Breakdown of matched:
    both = df_lens[(df_lens['match_title'] == True) & (df_lens['match_abs'] == True)].shape[0]
    title_only = df_lens[(df_lens['match_title'] == True) & (df_lens['match_abs'] == False)].shape[0]
    abs_only = df_lens[(df_lens['match_title'] == False) & (df_lens['match_abs'] == True)].shape[0]
    
    print(f"Kept after T&A: {kept_count}")
    print(f"  - Matched BOTH Title & Abstract: {both}")
    print(f"  - Matched Title ONLY: {title_only}")
    print(f"  - Matched Abstract ONLY: {abs_only}")

if __name__ == "__main__":
    run()
