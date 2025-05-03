gcloud storage rsync -r gs://tour_storage/data/youtube/75_first_ave_undistorted ~/data/youtube/75_first_ave_undistorted
python train.py -s ~/data/youtube/75_first_ave_undistorted -m ~/output/75_first_ave_undistorted --eval --test_iterations -1 -r 1 --images images  --position_lr_init 4e-5 --position_lr_final 4e-7 --percent_dense 0.0005 --tmin 0 
python metrics.py -m ~/output/75_first_ave_undistorted
gcloud storage cp -r ~/output/75_first_ave_undistorted gs://tour_storage/output/75_first_ave_undistorted