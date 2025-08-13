from modal import Image

image = (
    Image
    # Change this base image to whatever torch/cuda version you want
    .from_registry("pytorch/pytorch:2.6.0-cuda12.6-cudnn9-devel")
    .env(
        {
            # Set Torch CUDA Compatbility to be for RTX 4090, T4, L40s, and A100
            # If using a different GPU, make sure its torch cuda architecture version is added to the list
            "TORCH_CUDA_ARCH_LIST": "5.0;6.0;6.1;7.0;7.5;8.0;8.6;8.9",
            # Set environment variable to avoid interactive prompts from installing packages
            "DEBIAN_FRONTEND": "noninteractive",
            "TZ": "America/New_York",
            "OptiX_INSTALL_DIR": "/opt/OptiX_7.4",
            "CUDAARCHS": "50;60;61;70;75;80;86;89",
            "LD_LIBRARY_PATH": "/slang_install/lib/",
        }
    )
    # Install system dependencies
    .run_commands(
        "apt-get update && apt-get install -y \
            openssh-server \
            wget \
            git \
            cmake \
            unzip \
            build-essential \
            libglew-dev \
            libassimp-dev \
            libboost-all-dev \
            libgtk-3-dev \
            libopencv-dev \
            libglfw3-dev \
            libavdevice-dev \
            libavcodec-dev \
            libeigen3-dev \
            libxxf86vm-dev \
            libembree-dev \
            libcgal-dev \
            libglm-dev \
            && rm -rf /var/lib/apt/lists/*"
    )
    .workdir("/root/workspace")

    ###### Your Code Here ######
    # Would recommend pulling the repo from github (we later overwrite it with the current local directory) 
    # eg: .run_commands("git clone https://github.com/<repo-name>.git -b <optional-branch-name> --recursive .")

    # Install (avoid conda installs because they don't work well in dockerfile situations)
    # Separating these on separate lines helps if there are errors (previous lines will be cached) especially on the large package installs
    # eg:
    # .run_commands("pip install -e .")
    # .run_commands("pip install submodules/diff-gaussian-rasterization")
    # Note: If your run_commands step needs access to a gpu it's actually possible to do that through "run_commands(gpu='T4', ...)"
    # Install Slang
    .run_commands(
        "wget https://github.com/shader-slang/slang/releases/download/v2025.6.4/slang-2025.6.4-linux-x86_64.zip \
            && mkdir /slang_install \
            && unzip slang-2025.6.4-linux-x86_64.zip -d /slang_install \
            && cp /slang_install/bin/* /usr/bin/ \
            && rm slang-2025.6.4-linux-x86_64.zip"
    )
    # Install abseil-cpp from source
    .run_commands(
        "git clone https://github.com/abseil/abseil-cpp.git /tmp/abseil-cpp \
            && cd /tmp/abseil-cpp \
            && mkdir build \
            && cd build \
            && cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON .. \
            && make -j$(nproc) \
            && make install \
            && ldconfig \
            && rm -rf /tmp/abseil-cpp"
    )

    # Clone the repo
    .run_commands(
        "git clone https://github.com/N-Demir/ever_training.git --recursive -b nvs-leaderboard ."
    )
    # OptiX move and Python deps
    .run_commands(
        "mv optix /opt/OptiX_7.4"
    )
    .run_commands(
        "pip install -r requirements.txt"
    )
    # Project install
    .run_commands(
        "bash install.bash"
    )
)