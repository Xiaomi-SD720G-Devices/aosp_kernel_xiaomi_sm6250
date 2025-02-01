#!/usr/bin/env python3

import os
import subprocess
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

# Constants
KERNEL_DIR = Path.cwd()
MODEL = "Xiaomi"
DEVICE = "Miatoll"
DEFCONFIG = "vendor/xiaomi/miatoll_defconfig"

IMAGE = KERNEL_DIR / "out/arch/arm64/boot/Image.gz"
DTBO = KERNEL_DIR / "out/arch/arm64/boot/dtbo.img"
DTB = KERNEL_DIR / "out/arch/arm64/boot/dts/qcom/cust-atoll-ab.dtb"

VERBOSE = 0
ZIPNAME = "RedCherry"
COMPILER = "aosp"
LINKER = "ld.lld"
LOG_FILE = KERNEL_DIR / "log.txt"
ANYKERNEL_DIR = KERNEL_DIR / "AnyKernel3"

# Helpers
def log(message):
    with open(LOG_FILE, "a") as f:
        f.write(message + "\n")
    print(message)

def run_cmd(cmd, cwd=None, shell=False, live=False):
    if live:
        process = subprocess.Popen(
            cmd, cwd=cwd, shell=shell, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        for line in process.stdout:
            print(line, end='')
            with open(LOG_FILE, "a") as f:
                f.write(line)
        process.wait()
        return process
    else:
        process = subprocess.run(
            cmd, cwd=cwd, shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        log(process.stdout)
        return process

def truncate_log():
    open(LOG_FILE, "w").close()

def get_kernel_version():
    try:
        result = subprocess.run(["make", "kernelversion"], capture_output=True, text=True)
        version = result.stdout.strip()
        if "grep" in version or not version:
            return "unknown"
        return version
    except:
        return "unknown"

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d-%H%M")

def clean_previous_files():
    log("Cleaning previous kernel files and build environment...")
    for file in ANYKERNEL_DIR.glob("RedCherry-kernel*.zip"):
        file.unlink()
    for file in ["Image.gz", "dtbo.img"]:
        (ANYKERNEL_DIR / file).unlink(missing_ok=True)
    shutil.rmtree(ANYKERNEL_DIR / "dtb", ignore_errors=True)

    run_cmd(["make", "clean"], live=True)
    run_cmd(["make", "mrproper"], live=True)

def clone_toolchains():
    log(f"Cloning toolchain for compiler: {COMPILER}")

    if not (KERNEL_DIR / "clang").exists():
        (KERNEL_DIR / "clang").mkdir()
        os.chdir(KERNEL_DIR / "clang")
        run_cmd([
            "wget",
            "https://github.com/userariii/AOSP-clang/releases/download/clang-r530567/clang-r530567.tar.gz"
        ], live=True)
        run_cmd(["tar", "-xvf", "clang-r530567.tar.gz"], live=True)
        os.chdir(KERNEL_DIR)

    if not (KERNEL_DIR / "gcc").exists():
        run_cmd([
            "git", "clone", "--depth=1",
            "https://github.com/LineageOS/android_prebuilts_gcc_linux-x86_aarch64_aarch64-linux-android-4.9.git",
            "gcc"
        ], live=True)

    if not (KERNEL_DIR / "gcc32").exists():
        run_cmd([
            "git", "clone", "--depth=1",
            "https://github.com/LineageOS/android_prebuilts_gcc_linux-x86_arm_arm-linux-androideabi-4.9.git",
            "gcc32"
        ], live=True)

    if not ANYKERNEL_DIR.exists():
        run_cmd([
            "git", "clone", "--depth=1",
            "https://github.com/userariii/AnyKernel3.git",
            "AnyKernel3"
        ], live=True)

def determine_threads():
    smt_path = Path("/sys/devices/system/cpu/smt/active")
    if smt_path.exists() and smt_path.read_text().strip() == "1":
        return os.cpu_count() * 2
    return os.cpu_count()

def set_env_vars():
    clang_version = run_cmd([str(KERNEL_DIR / "clang/bin/clang"), "--version"]).stdout.splitlines()[0]
    os.environ.update({
        "KBUILD_COMPILER_STRING": clang_version,
        "ARCH": "arm64",
        "SUBARCH": "arm64",
        "KBUILD_BUILD_HOST": "Linux",
        "KBUILD_BUILD_USER": "CRUECY",
        "DISTRO": subprocess.getoutput(". /etc/os-release && echo $NAME"),
        "PATH": f"{KERNEL_DIR}/clang/bin:{KERNEL_DIR}/gcc/bin:{KERNEL_DIR}/gcc32/bin:" + os.environ["PATH"]
    })

def compile_kernel(threads):
    log("Starting compilation...")
    start = datetime.now()

    run_cmd(["make", f"O=out", DEFCONFIG], live=True)

    build_cmd = [
        "make", f"-j{threads}", "O=out", "ARCH=arm64",
        "CC=clang", "CROSS_COMPILE=aarch64-linux-gnu-",
        "CROSS_COMPILE_ARM32=arm-linux-gnueabi-",
        "HOSTCC=clang", "HOSTCXX=clang++",
        "HOSTCFLAGS=-fuse-ld=lld -Wno-unused-command-line-argument",
        f"LD={LINKER}", "LLVM=1", "LLVM_IAS=1",
        "AR=llvm-ar", "NM=llvm-nm", "OBJCOPY=llvm-objcopy",
        "OBJDUMP=llvm-objdump", "STRIP=llvm-strip",
        "READELF=llvm-readelf", "OBJSIZE=llvm-size",
        f"V={VERBOSE}"
    ]
    run_cmd(build_cmd, live=True)

    elapsed = (datetime.now() - start).seconds
    log(f"Compilation took {elapsed} seconds.")

def zip_kernel(final_zip):
    log("Starting zipping process...")
    (ANYKERNEL_DIR / "dtb").mkdir(parents=True, exist_ok=True)

    if all(f.exists() for f in [IMAGE, DTBO, DTB]):
        shutil.copy(IMAGE, ANYKERNEL_DIR)
        shutil.copy(DTBO, ANYKERNEL_DIR)
        shutil.copy(DTB, ANYKERNEL_DIR / "dtb")

        os.chdir(ANYKERNEL_DIR)
        run_cmd(["zip", "-r9", final_zip, "."], live=True)
        with open(final_zip, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        log(f"MD5: {md5}")
        os.chdir(KERNEL_DIR)
    else:
        log("Error: One or more required files are missing!")
        if not IMAGE.exists(): log(f"Missing: {IMAGE}")
        if not DTBO.exists(): log(f"Missing: {DTBO}")
        if not DTB.exists(): log(f"Missing: {DTB}")
        exit(1)

def main():
    truncate_log()
    clean_previous_files()
    clone_toolchains()
    threads = determine_threads()
    log(f"Number of threads: {threads}")
    set_env_vars()

    kernel_version = get_kernel_version()
    timestamp = get_timestamp()
    final_zip = f"{ZIPNAME}-kernel-v{kernel_version}-{DEVICE}-{timestamp}.zip"

    compile_kernel(threads)
    zip_kernel(final_zip)

    log("Script completed successfully. Press Enter to exit...")
    input()

if __name__ == "__main__":
    main()
