#This is SH file for LearningAIM

seed_number=42
dataset_name='ALL-AV'
test_checkpoint=1401

python M2_Artery_vein/test_outside.py --batch-size=8 \
--dataset=${dataset_name} \
--job_name=20210724_${dataset_name}_randomseed \
--checkstart=${test_checkpoint} \
--uniform=True