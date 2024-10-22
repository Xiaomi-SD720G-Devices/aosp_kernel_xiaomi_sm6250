#!/usr/bin/env bash

#
# Script For Building Android Kernel
#

##----------------------------------------------------------##
# Specify Kernel Directory
KERNEL_DIR="$(pwd)"

# Device Name and Model
MODEL=Xiaomi
DEVICE=Miatoll

# Kernel Version Code
VERSION="v1.0"

# Kernel Defconfig
DEFCONFIG=vendor/xiaomi/miatoll_defconfig

# Files
IMAGE=${KERNEL_DIR}/out/arch/arm64/boot/Image.gz
DTBO=${KERNEL_DIR}/out/arch/arm64/boot/dtbo.img
DTB=${KERNEL_DIR}/out/arch/arm64/boot/dts/qcom/cust-atoll-ab.dtb

# Verbose Build
VERBOSE=0

# Kernel Version
KERVER=$(make kernelversion)
COMMIT_HEAD=$(git log --oneline -1)

# Date and Time
DATE=$(TZ=Asia/Kolkata date +"%Y%m%d-%T")
TANGGAL=$(date +"%F%S")

# Final Zip Name
ZIPNAME=RedCherry
FINAL_ZIP=${ZIPNAME}-kernel-v${KERVER}-${DEVICE}-${TANGGAL}.zip

# Compiler and Linker
COMPILER=aosp
LINKER=ld.lld

# Log File
LOG_FILE="log.txt"

##------------------------------------------------------##
# Truncate log file at the start
: > "$LOG_FILE"

# Prevent Terminal Auto-Close on Errors
trap 'echo "Script finished. Press any key to exit..."; read -n 1' EXIT

##------------------------------------------------------##
# Clean Existing Files and Kernel Build Environment
function clean_previous_files() {
    echo "Cleaning previous kernel files and build environment..." | tee -a "$LOG_FILE"

    # Remove old zip files
    rm -f AnyKernel3/RedCherry-kernel*.zip

    # Remove previous kernel build outputs in AnyKernel3
    rm -f AnyKernel3/Image.gz AnyKernel3/dtbo.img
    rm -rf AnyKernel3/dtb/*

    # Perform a clean build: make clean and make mrproper
    make clean && make mrproper | tee -a "$LOG_FILE"
}

##------------------------------------------------------##
# Clone ToolChain
function cloneTC() {
    echo "Cloning toolchain for compiler: $COMPILER" | tee -a "$LOG_FILE"

    if [ ! -d "${KERNEL_DIR}/clang" ]; then
        mkdir clang && cd clang || exit 1
        wget -q https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+archive/refs/heads/master/clang-r498229b.tar.gz
        tar -xf clang*
        cd .. || exit 1
    else
        echo "Directory 'clang' already exists. Skipping download." | tee -a "$LOG_FILE"
    fi

    if [ ! -d "${KERNEL_DIR}/gcc" ]; then
        git clone https://github.com/LineageOS/android_prebuilts_gcc_linux-x86_aarch64_aarch64-linux-android-4.9.git --depth=1 gcc
    fi

    if [ ! -d "${KERNEL_DIR}/gcc32" ]; then
        git clone https://github.com/LineageOS/android_prebuilts_gcc_linux-x86_arm_arm-linux-androideabi-4.9.git --depth=1 gcc32
    fi

    PATH="${KERNEL_DIR}/clang/bin:${KERNEL_DIR}/gcc/bin:${KERNEL_DIR}/gcc32/bin:$PATH"

    if [ ! -d AnyKernel3 ]; then
        git clone --depth=1 https://github.com/userariii/AnyKernel3.git -b Forza
    else
        echo "Directory 'AnyKernel3' already exists. Skipping download." | tee -a "$LOG_FILE"
    fi
}

##------------------------------------------------------##
# Determine the number of threads for compilation
function determine_threads() {
    echo "Determining number of threads..." | tee -a "$LOG_FILE"
    if [ "$(cat /sys/devices/system/cpu/smt/active)" = "1" ]; then
        THREADS=$(expr $(nproc --all) \* 2)
    else
        THREADS=$(nproc --all)
    fi
    echo "Number of threads: $THREADS" | tee -a "$LOG_FILE"
}

##------------------------------------------------------##
# Export Variables
function exports() {
    if [ -d "${KERNEL_DIR}/clang" ]; then
        export KBUILD_COMPILER_STRING=$(${KERNEL_DIR}/clang/bin/clang --version | head -n 1)
    fi

    export ARCH=arm64
    export SUBARCH=arm64
    export LOCALVERSION="-${VERSION}"
    export KBUILD_BUILD_HOST=Linux
    export KBUILD_BUILD_USER="CRUECY"
    export DISTRO=$(source /etc/os-release && echo "${NAME}")
}

##------------------------------------------------------##
# Compile the Kernel
function compile() {
    START=$(date +"%s")
    echo "Starting compilation..." | tee -a "$LOG_FILE"

    make O=out $DEFCONFIG | tee -a "$LOG_FILE"

    make -kj$THREADS O=out ARCH=arm64 CC=clang \
        CROSS_COMPILE=aarch64-linux-gnu- CROSS_COMPILE_ARM32=arm-linux-gnueabi- HOSTCC=clang HOSTCXX=clang++ \
        HOSTCFLAGS="-fuse-ld=lld -Wno-unused-command-line-argument" LD=$LINKER LLVM=1 LLVM_IAS=1 AR=llvm-ar \
        NM=llvm-nm OBJCOPY=llvm-objcopy OBJDUMP=llvm-objdump STRIP=llvm-strip READELF=llvm-readelf OBJSIZE=llvm-size \
        V=$VERBOSE 2>&1 | tee -a "$LOG_FILE"

    END=$(date +"%s")
    DIFF=$((END - START))
    echo "Compilation took $DIFF seconds." | tee -a "$LOG_FILE"
}

##------------------------------------------------------##
# Zip the Kernel with Exception Handling
function zipping() {
    echo "Starting zipping process..." | tee -a "$LOG_FILE"

    # Ensure the dtb directory exists
    mkdir -p AnyKernel3/dtb

    # Remove any existing zip file with the same name to avoid duplicates
    if [ -f "AnyKernel3/$FINAL_ZIP" ]; then
        echo "Removing existing zip: $FINAL_ZIP" | tee -a "$LOG_FILE"
        rm "AnyKernel3/$FINAL_ZIP"
    fi

    if [[ -f $IMAGE && -f $DTBO && -f $DTB ]]; then
        cp "$IMAGE" AnyKernel3/
        cp "$DTBO" AnyKernel3/
        cp "$DTB" AnyKernel3/dtb/
        cd AnyKernel3 || exit 1

        # Create the zip only once
        zip -r9 "$FINAL_ZIP" * | tee -a "../$LOG_FILE"
        MD5CHECK=$(md5sum "$FINAL_ZIP" | cut -d' ' -f1)
        echo "MD5: $MD5CHECK" | tee -a "../$LOG_FILE"
        cd ..
    else
        echo "Error: One or more required files are missing!" | tee -a "$LOG_FILE"
        [[ ! -f $IMAGE ]] && echo "Missing: $IMAGE" | tee -a "$LOG_FILE"
        [[ ! -f $DTBO ]] && echo "Missing: $DTBO" | tee -a "$LOG_FILE"
        [[ ! -f $DTB ]] && echo "Missing: $DTB" | tee -a "$LOG_FILE"
        exit 1
    fi
}

##------------------------------------------------------##
# Execute Functions
clean_previous_files   # Clean up before building
cloneTC                # Clone necessary toolchains
determine_threads      # Determine the number of threads
exports                # Export necessary variables
compile                # Compile the kernel
zipping                # Zip the compiled files

# Keep the terminal open after completion
echo "Script completed successfully. Press any key to exit..." | tee -a "$LOG_FILE"
read -n 1
