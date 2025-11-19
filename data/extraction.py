import geopandas as gpd
import pandas as pd
import typer
import re

from termcolor import colored
from sklearn.cluster import AgglomerativeClustering
from sentence_transformers import SentenceTransformer
from app.config import *

app = typer.Typer()

def sanitize_filename(name: str) -> str:
    """Removes slashes and special characters to prevent filesystem errors."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)

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
    )
):
    '''
    Processes a raw GeoJSON file downloaded from the City of Chicago's Data Portal (https://data.cityofchicago.org/).
    This script extracts the business activity IDs and saves the data into separate Parquet files for each ID.
    An index file is written with all unique IDs and associated label.
    '''
    # --- 1. Loading Data ---
    
    print(colored(f'Processing raw GeoJSON file: {input_file}', 'blue', attrs=['bold']))
    df = gpd.read_file(input_file)
    
    clean_df = df.loc[:, [ACT_COL, NAME_COL, DESC_COL, 'geometry']].copy()
    
    # --- 2. NLP Clustering ---
    
    print(colored('Running semantic clustering...', 'yellow'))
    
    # Extracting unique raw description
    unique_activities = clean_df[DESC_COL].dropna().unique().tolist()
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(
        unique_activities, 
        show_progress_bar=True
    )
    
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=3.5,
        metric='euclidean',
        linkage='ward'
    )
    cluster_ids = clustering.fit_predict(embeddings)
    
    cluster_map = {}
    temp_df = pd.DataFrame({
        'text': unique_activities,
        'cluster': cluster_ids
    })
    
    print(colored('Consolidating Labels based on Frequency...', 'yellow'))
    activity_counts = clean_df[DESC_COL].value_counts().to_dict()
    
    for cluster_id in temp_df['cluster'].unique():
        members = temp_df[temp_df['cluster'] == cluster_id]['text'].tolist()
        clean_label = max(members, key=lambda x: activity_counts.get(x, 0))
        
        for member in members:
            cluster_map[member] = clean_label
    
    clean_df['clean_activity'] = clean_df[DESC_COL].map(cluster_map)
    
    # --- 3. Saving Consolidated Files ---
    unique_clean_labels = clean_df['clean_activity'].unique()
    
    print(f'Total records: {len(clean_df):,d}.')
    print(f'Reduced {len(unique_activities)} raw categories -> {len(unique_clean_labels)} semantic clusters substitued.')
    print(f'Saving partitions to {output_dir}...')
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Processing records by activity code
    for label in unique_clean_labels:
        if pd.isna(label) or label == '':
            continue
        subset_df = clean_df[clean_df['clean_activity'] == label]
        safe_name = sanitize_filename(str(label))
        output_path = DATA_DIR / f'{safe_name}.parquet'
            
        gpd.GeoDataFrame(subset_df).to_parquet(output_path)
    
    # --- 4. Creating the Index File ---
    index_df = pd.DataFrame({
        'raw_activity': list(cluster_map.keys()),
        'clean_activity': list(cluster_map.values())
    }).sort_values('clean_activity')

    index_path = DATA_DIR / f'cluster_index.csv'
    index_df.to_csv(index_path, index=False)
    
    print(f'Cluster index saved to {index_path}.')
    print(colored('Processing complete.', 'green', attrs=['bold']))
    
if __name__ == '__main__':
    app()