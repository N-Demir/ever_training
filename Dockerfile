# Use NVIDIA CUDA base image with Python 3.10
FROM pytorch/pytorch:2.6.0-cuda12.6-cudnn9-devel

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV OptiX_INSTALL_DIR=/opt/OptiX_7.4
ENV TORCH_CUDA_ARCH_LIST=5.0;6.0;6.1;7.0;7.5;8.0;8.6;8.9
ENV CUDAARCHS=50 60 61 70 75 80 86 89
ENV LD_LIBRARY_PATH=/slang_install/lib/

# Install system dependencies
RUN apt-get update && apt-get install -y \
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
    && rm -rf /var/lib/apt/lists/*

# Install Slang
RUN wget https://github.com/shader-slang/slang/releases/download/v2025.6.4/slang-2025.6.4-linux-x86_64.zip \
    && mkdir /slang_install \
    && unzip slang-2025.6.4-linux-x86_64.zip -d /slang_install \
    && cp /slang_install/bin/* /usr/bin/ \
    && rm slang-2025.6.4-linux-x86_64.zip

# Install abseil-cpp from source
RUN git clone https://github.com/abseil/abseil-cpp.git /tmp/abseil-cpp \
    && cd /tmp/abseil-cpp \
    && mkdir build \
    && cd build \
    && cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_POSITION_INDEPENDENT_CODE=ON .. \
    && make -j$(nproc) \
    && make install \
    && ldconfig \
    && rm -rf /tmp/abseil-cpp

WORKDIR /root/workspace

# Clone the ever_training repository
RUN git clone https://github.com/N-Demir/ever_training.git --recursive -b nvs-leaderboard .

RUN mv optix /opt/OptiX_7.4
RUN pip install -r requirements.txt

# Run the project's install script within the 'ever' env
RUN bash install.bash
