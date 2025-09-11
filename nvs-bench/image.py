from pathlib import Path, PurePosixPath

from modal import Image, Volume

method_name = Path.cwd().name
assert method_name != "nvs-bench", (
    "nvs-bench must be called from the method's directory, not the nvs-bench subdirectory. Eg: `modal run nvs-bench/image.py`."
)

nvs_bench_volume = Volume.from_name("nvs-bench", create_if_missing=True)

modal_volumes: dict[str | PurePosixPath, Volume] = {
    "/nvs-bench": nvs_bench_volume,
    # "/root/.cursor-server": Volume.from_name("cursor-volume", create_if_missing=True),
}

image = (
    Image.from_registry("halfpotato/ever:latest")
    # Install git and various other helper dependencies
    .run_commands(
        "apt-get update && apt-get install -y \
            openssh-server \
            git \
            wget \
            unzip \
            cmake \
            build-essential \
            ninja-build \
            libglew-dev \
            libassimp-dev \
            libboost-all-dev \
            libgtk-3-dev \
            libopencv-dev \
            libglfw3-dev \
            libavdevice-dev \
            libavcodec-dev \
            libeigen3-dev \
            libtbb-dev \
            libopenexr-dev \
            libxi-dev \
            libxrandr-dev \
            libxxf86vm-dev \
            libxxf86dga-dev \
            libxxf86vm-dev"
    )
    # Install gsutil (for downloading datasets the first time)
    .apt_install("curl", "ca-certificates", "gnupg")
    .run_commands(
        "curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -",
        "echo 'deb https://packages.cloud.google.com/apt cloud-sdk main' | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list",
        "apt-get update && apt-get install -y google-cloud-cli",
    )
    # For tracking GPU usage
    .run_commands("pip install gpu_tracker")
    # Install Ever training
    .workdir("/ever_training")
    .run_commands("/opt/conda/bin/conda run -n ever pip install tensorly")
    .add_local_dir(Path.cwd(), "/ever_training")
)
