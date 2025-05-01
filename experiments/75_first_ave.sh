gcloud storage rsync -r gs://tour_storage/data/youtube/75_first_ave ~/data/youtube/75_first_ave
python train.py -s ~/data/youtube/75_first_ave -m ~/output/75_first_ave_ever --eval --test_iterations -1 -r 1 --images images_2  --position_lr_init 4e-5 --position_lr_final 4e-7 --percent_dense 0.0005 --tmin 0 
python metrics.py -m ~/output/75_first_ave_ever
gcloud storage cp -r ~/output/75_first_ave_ever gs://tour_storage/output/75_first_ave_ever