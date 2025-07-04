import os
from pathlib import Path
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
    .add_local_file(local_path="viewer_requirements.txt", remote_path="/viewer_requirements.txt", copy=True)
    .run_commands(
        # Install packages from requirements.txt within the 'ever' environment
        "/opt/conda/bin/conda run -n ever pip install -r /viewer_requirements.txt",
    )
    ### Viewer installation instructions
    .add_local_file("startup_install.sh", "/root/startup_install.sh", copy=True)
    .run_commands("bash /root/startup_install.sh")
    ### Add the local viewer and ever code
    # TODO: May not work because its missing the build things, so maybe this needs to be added to root and overwritten
    .workdir("/ever_training")
    .add_local_dir(".", "/ever_training")
)


LOCAL_PORT = 9090


def wait_for_port(host, port, q):
    start_time = time.monotonic()
    while True:
        try:
            with socket.create_connection(("localhost", 22), timeout=30.0):
                break
        except OSError as exc:
            time.sleep(0.01)
            if time.monotonic() - start_time >= 30.0:
                raise TimeoutError("Waited too long for port 22 to accept connections") from exc
        q.put((host, port))


@app.function(
    timeout=3600 * 24,
    gpu="T4",
    secrets=[modal.Secret.from_name("wandb-secret"), modal.Secret.from_name("github-token")],
    volumes={"/root/.cursor-server": modal.Volume.from_name("cursor-server", create_if_missing=True), 
             "/root/data": modal.Volume.from_name("data", create_if_missing=True),
             "/root/output": modal.Volume.from_name("output", create_if_missing=True),
            #  "/root/ever_training": modal.Volume.from_name("ever-training", create_if_missing=True),
            #  "/root/viser": modal.Volume.from_name("viser", create_if_missing=True)
             }
)
def launch_ssh_server(q):
    with modal.forward(22, unencrypted=True) as tunnel:
        ### Startup Commands
        # Set env vars
        import os
        import shlex
        from pathlib import Path

        output_file = Path.home() / "env_variables.sh"

        with open(output_file, "w") as f:
            for key, value in os.environ.items():
                escaped_value = shlex.quote(value)
                f.write(f'export {key}={escaped_value}\n')
        subprocess.run("echo 'source ~/env_variables.sh' >> ~/.bashrc", shell=True)

        # Install whatever is needed at startup
        # subprocess.run("bash /root/startup_install.sh", shell=True)
        ### End Startup Commands

        host, port = tunnel.tcp_socket
        threading.Thread(target=wait_for_port, args=(host, port, q)).start()
        subprocess.run(["/usr/sbin/sshd", "-D"])  # TODO: I don't know why I need to start this here


def start_server():
    import sshtunnel

    with modal.Queue.ephemeral() as q:
        launch_ssh_server.spawn(q)
        host, port = q.get()
        print(f"SSH server running at {host}:{port}")

        server = sshtunnel.SSHTunnelForwarder(
            (host, port),
            ssh_username="root",
            ssh_password=" ",
            remote_bind_address=("127.0.0.1", 22),
            local_bind_address=("127.0.0.1", LOCAL_PORT),
            allow_agent=False,
        )

        try:
            server.start()
            print(f"SSH tunnel forwarded to localhost:{server.local_bind_port}")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down SSH tunnel...")
        finally:
            server.stop()

@app.function(
    timeout=3600 * 24,
    gpu="T4",
    secrets=[modal.Secret.from_name("wandb-secret"), modal.Secret.from_name("github-token")],
    volumes={
             "/root/data": modal.Volume.from_name("data", create_if_missing=True),
             "/root/output": modal.Volume.from_name("output", create_if_missing=True),
            #  "/root/ever_training": modal.Volume.from_name("ever-training", create_if_missing=True),
             }
)
def start_viewer():
    with modal.forward(8888) as tunnel:
        print("Viewer will run at")
        print(tunnel.url)
        print("Starting up will take like a minute or more")

        subprocess.run(
            "/opt/conda/bin/conda run -n ever python -u simple_viewer.py -m ~/output/zipnerf_nyc_ever/ --port 8888",
            shell=True,
        )


@app.local_entrypoint()
def main(server: bool = False):
    if server:
        start_server()
    
    start_viewer.remote()