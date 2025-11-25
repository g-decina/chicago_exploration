import geopandas as gpd
import pandas as pd
import numpy as np
import typer
import re
import shutil

from termcolor import colored
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import pairwise_distances_argmin_min

from app.config import *

app = typer.Typer()
    
def sanitize_filename(name: str) -> str:
    '''
    Removes slashes and special characters to prevent filesystem errors.
    Limits the filename to 150 characters.
    '''
    if len(name) > 150:
        name = name[:149]
    return re.sub(r'[\\/*?:<>|]', '_', name)

def parse_naics_blob(blob, digits: int = 4):
    '''
    Parses a concatenated NAICS string into a clean Code:Desc dictionary.
    Handles 'NAICS', 'NAICS07', 'NAICS12' prefixes.
    '''
    # 1. Regex Pattern
    # (NAICS\d*)  -> Group 1: Captures 'NAICS', 'NAICS07', 'NAICS12'
    # \s+         -> One or more spaces
    # (\d{4})     -> Group 2: Captures exactly 4-digit codes
    # \s+         -> One or more spaces
    # (.*?)       -> Group 3: Captures the Description (non-greedy)
    # (?=NAICS|$) -> Lookahead: Stops capturing when it hits the next 'NAICS' or end of string
    pattern = re.compile(fr'(NAICS\d*)\s+(\d{{{digits}}})\s+(.*?)(?=NAICS|$)', re.DOTALL)
    
    naics_map = {}
    
    for match in pattern.finditer(blob):
        prefix, code, raw_desc = match.groups()
        
        if len(code) != digits:
            continue
        
        # 2. Cleaning the Description
        clean_desc = raw_desc.strip()
        
        # Remove the artifact where the code (or a similar number) 
        # is stuck to the end of the text (e.g., '...manufacturing325220')
        # We look for a digit sequence at the very end of the string
        clean_desc = re.sub(r'\d+$', '', clean_desc)
        
        # Save to dict (Key=Description, Value=Code)
        # Description is the key because that is what we embed later
        if len(clean_desc) > 0:
            naics_map[clean_desc] = code

    return naics_map

def condense_labels(
    current_labels: list,
    model: SentenceTransformer,
    distance_threshold: float = 0.4
) -> dict:
    '''
    Groups labels using a distance threshold instead of fixed n_clusters.
    distance_threshold=0.4 means "Don't merge clusters if they are more than 0.4 distinct (cosine dist)".
    Returns a dictionary : {Old Label: New Label}
    '''
    
    embeddings = model.encode(current_labels)
    
    if len(current_labels) < 2:
        return {label: label for label in current_labels}
    
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        linkage='ward'
    )
    cluster_assignment = clustering.fit_predict(embeddings)
    
    label_map = {}
    
    df_clusters = pd.DataFrame({
        'label': current_labels,
        'cluster': cluster_assignment,
        'embedding': list(embeddings)
    })
    
    for c_id in df_clusters['cluster'].unique():
        cluster_members = df_clusters[df_clusters['cluster'] == c_id]
        
        member_embeddings = np.stack(cluster_members['embedding'].values)
        
        centroid = np.mean(member_embeddings, axis=0)
        
        closest_idx, _ = pairwise_distances_argmin_min([centroid], member_embeddings)
        representative_label = cluster_members.iloc[closest_idx[0]]['label']
        
        # Map all members to this representative label
        for member in cluster_members['label'].tolist():
            label_map[member] = representative_label
            
    return label_map

@app.command()
def main(
    input_file: Path = typer.Option(
        RAW_COMPANY_DATA, 
        '--input', 
        '-i', 
        help='Path to the raw GeoJSON company data file.'
    ),
    output_dir: Path = typer.Option(
        DATA_DIR, 
        '--output', 
        '-o', 
        help = 'Directory to save the processed parquet files.'
    ),
    naics_file: Path = typer.Option(
        Path('data/raw/industry-titles.csv'),
        '--naics',
        '-n',
        help = 'Path to the NAICS CSV file.'
    ),
    naics_digits: int = typer.Option(
        4,
        '--digits',
        '-d',
        help='NAICS Level used for clustering (2-6)'
    ),
    clustering_threshold: float = typer.Option(
        0.5,
        '--threshold',
        '-t',
        help='Distance threshold for merging (0.3=strict, 0.8=loose).'
    )
):
    '''
    Processes a raw GeoJSON file downloaded from the City of Chicago's Data Portal (https://data.cityofchicago.org/).
    This script extracts the business activity IDs and saves the data into separate Parquet files for each ID.
    An index file is written with all unique IDs and associated label.
    '''
    # --- 1. Loading Data ---
    # Company Data
    print(colored(f'Processing raw GeoJSON file: {input_file}', 'blue', attrs=['bold']))
    df = gpd.read_file(input_file)
    
    clean_df = df.loc[:, [ACT_COL, NAME_COL, DESC_COL, 'geometry']].copy()
    
    # NAICS Labels
    print(colored(f'Parcing NAICS dictionary...', 'blue'))
    naics_list = pd.read_csv(naics_file)
    full_text_blob = ' '.join(naics_list['industry_title'].dropna().astype(str).tolist())
    
    clean_naics_dict = parse_naics_blob(full_text_blob, digits=naics_digits)
    naics_descriptions = list(clean_naics_dict.keys())
    
    print(f'Loaded {len(naics_descriptions)} unique NAICS categories.')
    
    # --- 2. Generate Embeddings ---
    print(colored('Loading SentenceTransformers Model...', 'yellow'))
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print(colored('Embedding NAICS standards...', 'yellow'))
    corpus_embeddings = model.encode(
        naics_descriptions, 
        convert_to_tensor=True, 
        show_progress_bar=True
    )
    
    unique_activities = clean_df[DESC_COL].dropna().unique().tolist()
    print(colored(f'Embedding {len(unique_activities)} unique raw activities...', 'yellow'))
    query_embeddings = model.encode(unique_activities, convert_to_tensor=True, show_progress_bar=True)

    print(colored('Matching activities to nearest NAICS code...', 'yellow'))
    # Top 1 Search
    search_results = util.semantic_search(
        query_embeddings, 
        corpus_embeddings, 
        top_k=1
    )
    
    initial_map = {}

    for i, result_list in enumerate(search_results):
        best_match = result_list[0]
        
        score = best_match['score']
        corpus_idx = best_match['corpus_id']
        
        if score > 0.4:
            initial_map[unique_activities[i]] = naics_descriptions[corpus_idx]
        else:
            initial_map[unique_activities[i]] = 'Unclassified'
    
    
    # Apply map
    clean_df['clean_activity'] = clean_df[DESC_COL].map(initial_map)
    # Map the description to the code
    clean_df['naics_code'] = clean_df['clean_activity'].map(clean_naics_dict)

    # --- 4. CONDENSE LABELS ---
    found_labels = [x for x in clean_df['clean_activity'].unique()]
    tight_label_map = condense_labels(found_labels, model, clustering_threshold)
    tight_label_map["Unclassified"] = "Unclassified"
    
    clean_df['clean_activity'] = clean_df['clean_activity'].map(tight_label_map)
    
    # Map codes (This will map to the code of the representative label)
    clean_df['naics_code'] = clean_df['clean_activity'].map(clean_naics_dict)

    # --- 5. SAVE RESULTS ---
    unique_clean_labels = clean_df['clean_activity'].unique()
    
    print(f'Total records: {len(clean_df):,d}.')
    print(f'Reduced {len(unique_activities)} raw categories -> {len(unique_clean_labels)} NAICS categories.')
    
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    saved_count = 0
    for label in unique_clean_labels:
        if pd.isna(label) or label == '':
            continue
            
        # Isolate data
        subset_df = clean_df[clean_df['clean_activity'] == label]
        
        # Handle Unclassified separately or sanitize name
        fname = 'Unclassified' if label == 'Unclassified' else sanitize_filename(label)
        output_path = output_dir / f'{fname}.parquet'
            
        gpd.GeoDataFrame(subset_df).to_parquet(output_path)
        saved_count += 1

    # Save Index
    index_df = pd.DataFrame({
        'raw_activity': list(tight_label_map.keys()),
        'clean_activity': list(tight_label_map.values())
    })
    index_df = index_df[index_df['clean_activity'] != 'Unclassified'].copy()
    index_df['naics_code'] = index_df['clean_activity'].map(clean_naics_dict)
    index_df = index_df.sort_values(by='clean_activity')
    
    index_df.to_csv(output_dir / 'cluster_index.csv', index=False)

    print(colored(f'Processing complete. {saved_count} files created.', 'green', attrs=['bold']))

if __name__ == '__main__':
    app()