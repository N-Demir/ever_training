import os
from pathlib import Path
import shlex
import socket
import subprocess
import threading
import time
import modal

from modal_image import image

# Can use the prebuilt image as well
#from modal_image import image; image
#modal.Image.from_registry("halfpotato/ever:latest", add_python="3.12")
#modal.Image.from_dockerfile(Path(__file__).parent / "Dockerfile", add_python="3.12")
app = modal.App("ever-training", image=image
    # GCloud
    #TODO: Install gcloud
    .run_commands("apt-get update && apt-get install -y curl gnupg && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    echo \"deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main\" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    apt-get update && apt-get install -y google-cloud-cli")
    .add_local_file(Path.home() / "gcs-tour-project-service-account-key.json", "/root/gcs-tour-project-service-account-key.json", copy=True)
    .run_commands(
        "gcloud auth activate-service-account --key-file=/root/gcs-tour-project-service-account-key.json",
        "gcloud config set project tour-project-442218",
        "gcloud storage ls"
    )
    .env({"GOOGLE_APPLICATION_CREDENTIALS": "/root/gcs-tour-project-service-account-key.json"})
    .run_commands("gcloud storage ls")
    # # SSH server
    .apt_install("openssh-server")
    .run_commands(
        "mkdir -p /run/sshd" #, "echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config", "echo 'root: ' | chpasswd" #TODO: uncomment this if the key approach doesn't work
    )
    .add_local_file(Path.home() / ".ssh/id_rsa.pub", "/root/.ssh/authorized_keys", copy=True)
    # Install and configure Git
    .run_commands("apt-get install -y git")
    .run_commands("git config --global pull.rebase true")
    .run_commands("git config --global user.name 'Nikita Demir'")
    .run_commands("git config --global user.email 'nikitde1@gmail.com'")
)

@app.function(
    timeout=3600 * 24,
    gpu="T4",
    secrets=[modal.Secret.from_name("wandb-secret"), modal.Secret.from_name("github-token")],
    volumes={"/root/.cursor-server": modal.Volume.from_name("cursor-server", create_if_missing=True), 
             "/root/data": modal.Volume.from_name("data", create_if_missing=True),
             "/root/output": modal.Volume.from_name("output", create_if_missing=True),
             "/root/ever_training": modal.Volume.from_name("ever-training", create_if_missing=True)}
)
def run(experiment_script: str) -> None:
    #! This is a joke. Thank god for conda run and fuck modal
    #! Need conda absolute path
    #! Need to use conda run to define what environment because conda init && activate are impossible to make work together
    #! Need to use bash -c run a script that could have multiple lines
    subprocess.run(f"cd ~/ever_training && /opt/conda/bin/conda run -n ever --no-capture-output bash -c {shlex.quote(experiment_script)}", shell=True)


@app.local_entrypoint()
def main(experiment_path_str: str):
    """Experiment path can be a directory or a file.

    If it's a directory, runs all the experiments in it in parallel.
    If it's a file, runs the experiment specified by the file.
    """
    experiment_path = Path(experiment_path_str)
    # If the experiment path is a directory, run all the experiments in it in parallel
    if experiment_path.is_dir():
        for experiment in experiment_path.iterdir():
            modal_run = run.spawn(experiment.read_text().replace("\n", " && "))
    else:
        modal_run = run.spawn(experiment_path.read_text().replace("\n", " && "))

    modal_run.get()