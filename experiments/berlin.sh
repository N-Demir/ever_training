gcloud storage rsync -r gs://tour_storage/data/zipnerf/berlin ~/data/zipnerf/berlin
python train.py -s ~/data/zipnerf/berlin -m ~/output/zipnerf_berlin_ever --eval --test_iterations -1 -r 1 --images images_2  --position_lr_init 4e-5 --position_lr_final 4e-7 --percent_dense 0.0005 --tmin 0 
python metrics.py -m ~/output/zipnerf_berlin_ever
gcloud storage cp -r ~/output/zipnerf_berlin_ever gs://tour_storage/output/zipnerf_berlin_ever