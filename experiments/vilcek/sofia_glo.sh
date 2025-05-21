gcloud storage rsync -r gs://tour_storage/data/vilcek/sofia ~/data/vilcek/sofia
python train.py -s ~/data/vilcek/sofia -m ~/output/sofia_glo --eval --test_iterations -1  --enable_GLO --glo_lr 0 --checkpoint_iterations 7000 30000  -r 1 --images images --position_lr_init 4e-5 --position_lr_final 4e-7 --percent_dense 0.0005 --tmin 0 
python metrics.py -m ~/output/sofia_glo
gcloud storage cp -r ~/output/sofia_glo gs://tour_storage/output/sofia_glo