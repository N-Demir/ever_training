# ---
# deploy: true
# cmd: ["modal", "serve", "10_integrations/streamlit/serve_streamlit.py"]
# ---

# # Run and share Streamlit apps

# This example shows you how to run a Streamlit app with `modal serve`, and then deploy it as a serverless web app.

# ![example streamlit app](./streamlit.png)

# This example is structured as two files:

# 1. This module, which defines the Modal objects (name the script `serve_streamlit.py` locally).

# 2. `app.py`, which is any Streamlit script to be mounted into the Modal
# function ([download script](https://github.com/modal-labs/modal-examples/blob/main/10_integrations/streamlit/app.py)).

import shlex
import subprocess
from pathlib import Path

import modal
from modal_image import image

app = modal.App(name="vizer", image=image
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
    ### Viewer installation instructions
    .add_local_file(local_path="viewer_requirements.txt", remote_path="/viewer_requirements.txt", copy=True)
    .run_commands(
        # Install packages from requirements.txt within the 'ever' environment
        "/opt/conda/bin/conda run -n ever pip install -r /viewer_requirements.txt",
    )
    .add_local_file("startup_install.sh", "/root/startup_install.sh", copy=True)
    .run_commands("bash /root/startup_install.sh")
    ### Add the local viewer and ever code
    # TODO: May not work because its missing the build things, so maybe this needs to be added to root and overwritten
    .workdir("/ever_training")
    .add_local_dir(".", "/ever_training")
)

@app.function(gpu="T4", volumes={
    "/root/data": modal.Volume.from_name("data", create_if_missing=True),
    "/root/output": modal.Volume.from_name("output", create_if_missing=True),
},
    timeout=600,
)
# @modal.concurrent(max_inputs=100) # Commented out because I'm not sure if the processes should run separately...
@modal.web_server(8888, startup_timeout=90)
def run():
    print("Starting the viewer!")
    subprocess.Popen(
        "/opt/conda/bin/conda run -n ever python -u simple_viewer.py -m ~/output/zipnerf_nyc_ever/ --port 8888",
        shell=True,
    )


# ## Iterate and Deploy

# While you're iterating on your screamlit app, you can run it "ephemerally" with `modal serve`. This will
# run a local process that watches your files and updates the app if anything changes.

# ```shell
# modal serve serve_streamlit.py
# ```

# Once you're happy with your changes, you can deploy your application with

# ```shell
# modal deploy serve_streamlit.py
# ```

# If successful, this will print a URL for your app that you can navigate to from
# your browser 🎉 .