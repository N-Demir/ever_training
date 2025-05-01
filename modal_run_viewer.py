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
    .run_commands(
        # Chain all nvm/node/yarn related commands in one shell session
        # Export NVM_DIR, create dir, install nvm, source it, install node, setup yarn, use node
        (
            'export NVM_DIR="$HOME/.nvm" && '
            'mkdir -p "$NVM_DIR" && '
            'curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash && '
            '[ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh" && '  # Source nvm
            'nvm install 23.9.0 && '
            'corepack prepare yarn@4.7.0 --activate && '
            'nvm use v23.9.0 && corepack enable'
        ),
        # Uninstall viser installed via pip earlier, if needed (runs in a separate shell)
        "/opt/conda/bin/conda run -n ever pip uninstall -y viser",
    )
    .add_local_file("startup_install.sh", "/root/startup_install.sh", copy=True)
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
             "/root/ever_training": modal.Volume.from_name("ever-training", create_if_missing=True),
             "/root/viser": modal.Volume.from_name("viser", create_if_missing=True)}
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
        subprocess.run("bash /root/startup_install.sh", shell=True)
        ### End Startup Commands

        host, port = tunnel.tcp_socket
        threading.Thread(target=wait_for_port, args=(host, port, q)).start()
        subprocess.run(["/usr/sbin/sshd", "-D"])  # TODO: I don't know why I need to start this here

@app.local_entrypoint()
def main():
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
