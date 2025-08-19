#!/bin/bash
set -e

# Auto-detect repo name as method; fallback to current directory if not a git repo
method_name="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"
method_name="${method_name// /_}"

# Check if scene argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <dataset/scene>"
    echo "Example: $0 mipnerf360/bicycle"
    exit 1
fi

scene=$1

expected_output_folder="/nvs-leaderboard-output/$scene/$method_name/test_renders"

# Remove the output folder if it already exists
rm -rf /nvs-leaderboard-output/$scene/$method_name

# Record start time
start_time=$(date +%s)

######## START OF YOUR CODE ########
# Train using the train split in the dataset folder
# eg: python train.py --data /nvs-leaderboard-data/$scene --output /nvs-leaderboard-output/$scene/$method_name/

# TODO: For zipnerf/alameda, should use GLO args to be comparable to zipnerf
/opt/conda/bin/conda run -n ever python train.py -s /nvs-leaderboard-data/$scene -m /nvs-leaderboard-output/$scene/$method_name/ --eval --test_iterations -1 --iterations 10

# Render the test split
# eg: python render.py --data /nvs-leaderboard-data/$scene --output /nvs-leaderboard-output/$scene/$method_name/ 

/opt/conda/bin/conda run -n ever python render.py -s /nvs-leaderboard-data/$scene -m /nvs-leaderboard-output/$scene/$method_name/ --eval

# At the end, move your renders into the `expected_output_folder`
# eg: mv /nvs-leaderboard-output/$scene/$method_name/test/ours_30000/renders $expected_output_folder

mv /nvs-leaderboard-output/$scene/$method_name/test/ours_10/renders $expected_output_folder
######## END OF YOUR CODE ########

# Record end time and show duration
end_time=$(date +%s)
echo $((end_time - start_time)) > /nvs-leaderboard-output/$scene/$method_name/training_time.txt
