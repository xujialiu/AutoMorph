import fundus_prep as prep
import os
import pandas as pd
from PIL import ImageFile
import shutil
from multiprocessing import Pool, cpu_count
from functools import partial

ImageFile.LOAD_TRUNCATED_IMAGES = True

AUTOMORPH_DATA = os.getenv("AUTOMORPH_DATA", ".")


def process_image(image_path, resolution_df, save_path):
    try:
        # Skip if already processed
        output_filename = f"{image_path.split('.')[0]}.png"
        output_path = os.path.join(save_path, output_filename)
        if os.path.exists(output_path):
            return None

        # Get resolution from DataFrame
        resolution = resolution_df.loc[resolution_df['fundus'] == image_path, 'res'].values[0]
        
        # Load image
        img_path = os.path.join(AUTOMORPH_DATA, "images", image_path)
        img = prep.imread(img_path)
        
        # Process image with clean parameters for each process
        radius, centre_w, centre_h = [], [], []
        r_img, _, _, _, radius, centre_w, centre_h = prep.process_without_gb(
            img, img, radius, centre_w, centre_h
        )
        
        # Validate results
        if not radius or not centre_w or not centre_h:
            return None
        
        # Save processed image
        prep.imwrite(output_path, r_img)
        
        return {
            'name': output_filename,
            'radius': radius[-1],  # Get last added element
            'centre_w': centre_w[-1],
            'centre_h': centre_h[-1],
            'resolution': resolution,
        }
    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        return None


def process(image_list, save_path):
    # Load resolution data once
    resolution_df = pd.read_csv(f"{AUTOMORPH_DATA}/resolution_information.csv")
    
    # Create worker partial with fixed parameters
    worker = partial(process_image, resolution_df=resolution_df, save_path=save_path)
    
    # Use all available CPUs
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(worker, image_list)
    
    # Filter valid results
    valid_results = [r for r in results if r is not None]
    
    # Collect data
    data_dict = {
        'Name': [r['name'] for r in valid_results],
        'centre_w': [r['centre_w'] for r in valid_results],
        'centre_h': [r['centre_h'] for r in valid_results],
        'radius': [r['radius'] for r in valid_results],
        'resolution': [r['resolution'] for r in valid_results],
    }
    
    # Calculate derived fields
    data_dict['Scale'] = [r * 2 / 912 for r in data_dict['radius']]
    data_dict['Scale_resolution'] = [r * s * 1000 
                                   for r, s in zip(data_dict['resolution'], data_dict['Scale'])]
    
    # Save final CSV
    pd.DataFrame(data_dict).to_csv(
        f"{AUTOMORPH_DATA}/Results/M0/crop_info.csv", 
        index=False, 
        encoding='utf8'
    )


if __name__ == "__main__":
    # Cleanup and setup
    images_dir = os.path.join(AUTOMORPH_DATA, "images")
    if os.path.exists(os.path.join(images_dir, ".ipynb_checkpoints")):
        shutil.rmtree(os.path.join(images_dir, ".ipynb_checkpoints"))
    
    # Create output directory
    save_dir = os.path.join(AUTOMORPH_DATA, "Results", "M0", "images")
    os.makedirs(save_dir, exist_ok=True)
    
    # Get sorted image list
    image_list = sorted([
        f for f in os.listdir(images_dir) 
        if os.path.isfile(os.path.join(images_dir, f))
    ])
    
    # Start processing
    process(image_list, save_dir)