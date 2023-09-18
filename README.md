## README



### train
cd into each model* dir and train separately.

model1：
```
python run_net.py --cfg configs/EPIC-Sounds/slowfast/SLOWFASTAUDIO_8x8_R50.yaml NUM_GPUS 1 OUTPUT_DIR ./output EPICSOUNDS.AUDIO_DATA_FILE ../../data/EPIC_audio.hdf5 EPICSOUNDS.ANNOTATIONS_DIR ../ TRAIN.CHECKPOINT_FILE_PATH ./SLOWFAST_VGG.pyth
```

model2:
```
python run_net.py --cfg configs/EPIC-Sounds/slowfast/SLOWFASTAUDIO_8x8_R50.yaml NUM_GPUS 1 OUTPUT_DIR ./output EPICSOUNDS.AUDIO_DATA_FILE ../../data/EPIC_audio.hdf5 EPICSOUNDS.ANNOTATIONS_DIR ../ TRAIN.CHECKPOINT_FILE_PATH ./SLOWFAST_EPIC_SOUNDS.pyth
```

model3:
```
python run_net.py --cfg configs/EPIC-Sounds/slowfast/SLOWFASTAUDIO_8x8_R50.yaml NUM_GPUS 1 OUTPUT_DIR ./output EPICSOUNDS.AUDIO_DATA_FILE ../../data/EPIC_audio.hdf5 EPICSOUNDS.ANNOTATIONS_DIR ../ TRAIN.CHECKPOINT_FILE_PATH ./SLOWFAST_EPIC_SOUNDS.pyth MODEL.FREEZE_BACKBONE True 
```

model4:
```
python run_net.py --cfg configs/EPIC-Sounds/slowfast/SLOWFASTAUDIO_8x8_R50.yaml NUM_GPUS 1 OUTPUT_DIR ./output EPICSOUNDS.AUDIO_DATA_FILE ../../data/EPIC_audio.hdf5 EPICSOUNDS.ANNOTATIONS_DIR ../ TRAIN.CHECKPOINT_FILE_PATH ./SLOWFAST_EPIC_SOUNDS.pyth MODEL.FREEZE_BACKBONE True 
```


### test

Run test in each dir and you will get 4 result file.

For example:
```
python run_net.py --cfg configs/EPIC-Sounds/slowfast/SLOWFASTAUDIO_8x8_R50.yaml TRAIN.ENABLE False TEST.ENABLE True NUM_GPUS 1 OUTPUT_DIR ./output EPICSOUNDS.AUDIO_DATA_FILE ../../data/EPIC_audio.hdf5 EPICSOUNDS.ANNOTATIONS_DIR ../ TEST.CHECKPOINT_FILE_PATH ./SLOWFAST_EPIC_SOUNDS.pyth EPICSOUNDS.TEST_LIST EPIC_Sounds_recognition_test_timestamps.pkl
```

Then run `merge.py` will generate final submisson.