# Getting Started on ZGX Fury (GB300)

This guide explains how to download the NVIDIA Nemotron 3 Super 120B NVFP4 model
and run it with the HP+Infinity container on a ZGX Fury (GB300) system.

## 1. Check the Prerequisites

Before you begin, ensure that your system meets the following requirements.

- Use a ZGX Fury system with an NVIDIA GB300 GPU.
- Have at least 144 GB of free disk space available.
- Install Docker and ensure that your user belongs to the `docker` group.
- Ensure that the NVIDIA driver and
  [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  are installed and configured to allow Docker containers to access the GPU.
- Maintain an internet connection during downloads and at runtime. FlashInfer
  downloads attention-kernel artifacts when needed.
- Install the Hugging Face CLI, which provides the `hf` command.
- Optionally, install `jq` to format and filter the container status output.

If the Hugging Face CLI is not installed, install it with the following command.

```bash
curl -LsSf https://hf.co/cli/install.sh | bash
```

Follow the installer's instructions to make `hf` available in your shell. Verify
that the command is available before continuing.

```bash
hf --help
```

## 2. Download the Model

Download the model at the exact revision expected by the launcher.
Choose **one** of the following options. **Do not run both download commands.**

### Option A: Use the Default Cache

Use this option if you want to store the model in the standard Hugging Face Hub
cache location.

```bash
hf download nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
  --revision ff433f5493e25d631c9f12b5d55c674229923d02
```

### Option B: Use a Custom Cache

Use this option instead of Option A if you want to store the model in a custom
cache location. Export `HF_HUB_CACHE` and pass that same directory to
`hf download`.

```bash
export HF_HUB_CACHE=/path/to/huggingface/cache
hf download nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 \
  --revision ff433f5493e25d631c9f12b5d55c674229923d02 \
  --cache-dir "$HF_HUB_CACHE"
```

Replace the example path with your actual cache directory. It must be the Hub
cache directory that contains
`models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4`, not the model's
`snapshots` directory. Keep `HF_HUB_CACHE` exported when you launch the container,
and export it again if you open a new shell.

The container runs as user ID `10001`. Ensure that the model cache files are
readable and the directories are traversable by this user.

## 3. Pull the Container Image

Download the HP+Infinity container image.

```bash
docker pull public.ecr.aws/s8i0z9d5/prod/infinity-nemotron-3-super-120b-nvfp4:1.3.0rc24-rc1
```

## 4. Start the Container

Open a terminal in the directory containing the provided `run.sh` launcher.
Run all remaining launcher commands from this directory.

Make the launcher executable before running it.

```bash
chmod +x run.sh
```

Start the container and load the model with the default settings.

```bash
./run.sh
```

The launcher starts the container in the background and prints its container ID.
By default, the container is named `hp-nemotron-serve`, and the service is
accessible only from the local system at `http://127.0.0.1:8000`. A container ID
does not mean that the model is ready. Check readiness in the next step.

### Use a Larger Context Window

To allow up to 122,880 input tokens and 131,072 total tokens, use the following
command instead of the default launch command. These limits correspond to a
120K input context and a 128K total context, including generated output.

```bash
MAX_INPUT_LEN=122880 MAX_SEQ_LEN=131072 ./run.sh
```

### Change the Host Binding and Port

To listen on all host network interfaces at port `9000`, use the following
command instead of the default launch command.

```bash
HP_BIND_ADDRESS=0.0.0.0 HP_HOST_PORT=9000 ./run.sh
```

Binding to `0.0.0.0` makes the service reachable from other systems when your
network and firewall allow it. Restrict access to trusted clients.

You can combine these settings in a single launch command.

```bash
HP_BIND_ADDRESS=0.0.0.0 HP_HOST_PORT=9000 \
  MAX_INPUT_LEN=122880 MAX_SEQ_LEN=131072 ./run.sh
```

If the container already exists, stop it as described
in step 6 before launching it again with different settings.

## 5. Wait for the Container to Become Healthy

The first cold start can take 10 to 20 minutes or longer while the model loads
and runtime artifacts are prepared. Allow startup to complete before sending
requests.

Run the following command periodically to check the container state.

```bash
./run.sh status
```

This command returns Docker's container state as JSON, including its health
status. It does not query the service's HTTP health endpoint directly.

If `jq` is installed, format the output with the following command.

```bash
./run.sh status | jq
```

To display only the current health status, use the following command.

```bash
./run.sh status | jq -r '.Health.Status'
```

Wait until the health status changes from `starting` to `healthy`. If the
container becomes `unhealthy` or exits, inspect its logs for errors.

```bash
./run.sh logs
```

Press `Ctrl+C` to stop following the logs. This does not stop the container.

## 6. Stop the Container

Stop and remove the container with the following command.

```bash
./run.sh stop
```

This command leaves the downloaded model, container image, and Docker runtime
cache volume in place. To start the service again, rerun your chosen launch
command from step 4.