export AUTOMORPH_DATA=$(pwd)/AUTOMORPH_DATA
export PYTHONPATH=/home/xujia/miniconda3/envs/automorph/bin/python
alias python=$PYTHONPATH
export CUDA_VISIBLE_DEVICES=1

echo "### Generate resolution ###"
python generate_resolution.py
echo "### Done ###"

# STEP 1 IMAGE PREPROCESSING (EXTRA BACKGROUND REMOVE, SQUARE)
echo "### Image Preprocessing ###"
python M0_Preprocess/EyeQ_process_multiprocess.py
echo "### Done ###"

# STEP 2 IMAGE QUALITY ASSESSMENT
echo "### Image Quality Assessment ###"
sh M1_Retinal_Image_quality_EyePACS/test_outside.sh
python M1_Retinal_Image_quality_EyePACS/merge_quality_assessment.py
echo "### Done ###"

# STEP 3 OPTIC DISC & VESSEL & ARTERY/VEIN SEG
echo "### Vessel Segmentation ###"
sh M2_Vessel_seg/test_outside.sh
sh M2_Artery_vein/test_outside.sh
sh M2_lwnet_disc_cup/test_outside.sh
echo "### Done ###"

# STEP 4 METRIC MEASUREMENT
echo "### Feature measuring ###"
python M3_feature_zone/retipy/create_datasets_disc_centred_B.py
python M3_feature_zone/retipy/create_datasets_disc_centred_C.py
python M3_feature_zone/retipy/create_datasets_macular_centred_B.py
python M3_feature_zone/retipy/create_datasets_macular_centred_C.py
echo "### Done ###"

echo "### Feature measuring ###"
python M3_feature_whole_pic/retipy/create_datasets_macular_centred.py
python M3_feature_whole_pic/retipy/create_datasets_disc_centred.py
echo "### Done ###"

echo "### Merge csv ###"
python csv_merge.py
echo "### Done ###"
