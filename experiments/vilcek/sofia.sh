gcloud storage rsync -r gs://tour_storage/data/vilcek/sofia ~/data/vilcek/sofia
python train.py -s ~/data/vilcek/sofia -m ~/output/sofia --eval --test_iterations -1 -r 1 --images images  --position_lr_init 4e-5 --position_lr_final 4e-7 --percent_dense 0.0005 --tmin 0 
python metrics.py -m ~/output/sofia
gcloud storage cp -r ~/output/sofia gs://tour_storage/output/sofia