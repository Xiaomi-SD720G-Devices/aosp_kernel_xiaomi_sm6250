#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path

# Global variables
C_PATH = Path.cwd() / "clang"
DEVICE = ["miatoll"]
ARCH = "arm64"

def print_box(lines):
    width = max(len(line) for line in lines)
    border = '-' * (width + 4)
    print(f" -{border}-")
    print(f"| {' ' * (width)} |")
    for line in lines:
        print(f"| {line.ljust(width)} |")
    print(f"| {' ' * (width)} |")
    print(f" -{border}-")

def prompt_menu():
    print("\n\033[1;32m\tRegeneration Method")
    print_box([
        "1. Regenerate full defconfigs",
        "2. Regenerate with Savedefconfig",
        "e. EXIT"
    ])
    choice = input("\033[0;36mEnter your choice or press 'e' to go back to shell: \033[0m").strip()
    return choice

def clone_clang():
    if not C_PATH.exists():
        print("\n\033[1;33mClang not found! Cloning AOSP clang...\033[0m")
        C_PATH.mkdir(parents=True, exist_ok=True)
        os.chdir(C_PATH)
        subprocess.run([
            "wget", "https://github.com/userariii/AOSP-clang/releases/download/clang-r530567/clang-r530567.tar.gz"
        ], check=True)
        subprocess.run(["tar", "-xvf", "clang-r530567.tar.gz"], check=True)
        os.remove("clang-r530567.tar.gz")
        os.chdir("..")

def run_make(device, config, savedefconfig_cmd=None):
    dfcf = f"vendor/xiaomi/{device}_defconfig"
    dfcf_path = Path("arch") / ARCH / "configs" / dfcf

    cmd = ["make", f"O=regen", dfcf]
    if savedefconfig_cmd:
        cmd.append(savedefconfig_cmd)
    
    print(f"\033[0;36m\n[*] Running command: {' '.join(cmd)}\033[0m")
    subprocess.run(cmd, check=True)
    
    regen_config = Path("regen") / config
    dfcf_path.parent.mkdir(parents=True, exist_ok=True)
    regen_config.replace(dfcf_path)
    
    subprocess.run(["rm", "-rf", "regen"])
    subprocess.run(["git", "add", str(dfcf_path)])

def main():
    if not DEVICE:
        print("\033[1;31mError! Device name is not pre-defined\033[0m")
        sys.exit(1)

    choice = prompt_menu()
    if choice == "1":
        config = ".config"
        commit_msg = "miatoll_defconfig: Regenerate Defconfig"
        savedefconfig_cmd = None
    elif choice == "2":
        config = "defconfig"
        commit_msg = "miatoll_defconfig: Regenerate with Savedefconfig"
        savedefconfig_cmd = "savedefconfig"
    elif choice.lower() == "e":
        print("\n\033[0;36mExiting...\033[0m")
        sys.exit(0)
    else:
        print("\n\033[1;31mError! Invalid option chosen\033[0m")
        sys.exit(1)

    # Prepare build environment
    clone_clang()
    os.environ["PATH"] = f"{C_PATH}/bin:{os.environ['PATH']}"
    os.environ["ARCH"] = ARCH
    os.environ["LLVM"] = "1"
    os.environ["LLVM_IAS"] = "1"

    # Run regeneration
    for dev in DEVICE:
        run_make(dev, config, savedefconfig_cmd)

    # Commit changes
    subprocess.run(["git", "commit", "-sm", commit_msg])

if __name__ == "__main__":
    main()
