gcloud storage rsync -r gs://tour_storage/data/tandt/truck ~/data/tandt/truck
python train.py -s ~/data/tandt/truck -m ~/output/tandt_truck_ever --eval
python metrics.py -m ~/output/tandt_truck_ever
gcloud storage cp -r ~/output/tandt_truck_ever gs://tour_storage/output/tandt_truck_ever