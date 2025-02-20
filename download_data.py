from google.cloud import storage
import os
from tqdm import tqdm

# Initialize GCS client
storage_client = storage.Client()
BUCKET_NAME = "music-caps"
DATASET_PATH = "FakeMusicCaps"
LOCAL_DATA_DIR = "/home/navin/repos/FakeMusicCaps/data/"  # adjust this path as needed

# Get bucket
bucket = storage_client.bucket(BUCKET_NAME)

def download_folder(prefix):
    if not os.path.exists(LOCAL_DATA_DIR):
        print(f"Creating directory {LOCAL_DATA_DIR}")
        os.makedirs(LOCAL_DATA_DIR)
    
    print(f"Downloading files from GCS...")
    blobs = list(bucket.list_blobs(prefix=prefix))
    print(f"Found {len(blobs)} files")

    existing = 0
    new = 0
    print(f"Downloading files to {LOCAL_DATA_DIR}...")
    for blob in tqdm(blobs):
        # Get the local path
        local_path = os.path.join(LOCAL_DATA_DIR, blob.name)
        
        # Skip if file exists and sizes match
        if os.path.exists(local_path):
            if os.path.getsize(local_path) == blob.size:
                existing += 1
                continue
        
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        # Download the file
        blob.download_to_filename(local_path)
        new += 1

    print(f"\nDownload complete!")
    print(f"Skipped existing files: {existing}")
    print(f"Downloaded new files: {new}")
    print(f"Total files: {existing + new}")

# Download all model folders
download_folder(DATASET_PATH)