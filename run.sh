#!/bin/bash  
# RUN FILE FOR AUTOMORPH
# YUKUN ZHOU 2023-08-24

date
# STEP 0 - prepare AUTOMORH_DATA directory and clean up results
export AUTOMORPH_DATA=$(pwd)/AUTOMORPH_DATA
python automorph_data.py


# 移动图像到AUTOMORPH_DATA/images

# 创建
python generate_resolution.py

# STEP 1 IMAGE PREPROCESSING (EXTRA BACKGROUND REMOVE, SQUARE)
python M0_Preprocess/EyeQ_process_multiprocess.py

# STEP 2 IMAGE QUALITY ASSESSMENT
echo "### Image Quality Assessment ###"
sh M1_Retinal_Image_quality_EyePACS/test_outside.sh
python M1_Retinal_Image_quality_EyePACS/merge_quality_assessment.py

# STEP 3 OPTIC DISC & VESSEL & ARTERY/VEIN SEG
sh M2_Vessel_seg/test_outside.sh
sh M2_Artery_vein/test_outside.sh
sh M2_lwnet_disc_cup/test_outside.sh

# STEP 4 METRIC MEASUREMENT
echo "### Feature measuring ###"
python M3_feature_zone/retipy/create_datasets_disc_centred_B.py
python M3_feature_zone/retipy/create_datasets_disc_centred_C.py
python M3_feature_zone/retipy/create_datasets_macular_centred_B.py
python M3_feature_zone/retipy/create_datasets_macular_centred_C.py


python M3_feature_whole_pic/retipy/create_datasets_macular_centred.py
python M3_feature_whole_pic/retipy/create_datasets_disc_centred.py

python csv_merge.py

echo "### Done ###"

date
