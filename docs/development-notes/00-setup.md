# Phase 0 - Foundation

Goal: solid WSL2 + Docker + GPU passthrough. This is where 80% of "weird" project issues come from.

## What this phase does

Verifies the environment can run GPU containers. If `nvidia-smi` works inside a Docker container, everything downstream will work.

## Status

- Windows 11 with WSL2
- NVIDIA driver (current)
- CUDA visible in WSL2 (`nvidia-smi`)
- Docker Desktop with WSL2 backend
- NVIDIA Container Toolkit
- GPU passthrough verified with test container

## Diagnostic commands (reference)

### PowerShell (Windows host)
```powershell
wsl --status
nvidia-smi
```

### WSL2 (Ubuntu)
```bash
nvidia-smi   # should show the GPU
```

### Docker (GPU passthrough)
```bash
docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi
```

If the last command shows the RTX 3050 inside the container, Phase 1 is ready to go.

## Common issues

| Symptom | Fix |
|---|---|
| `nvidia-smi` not found in WSL | Update Windows NVIDIA driver to >= 525 |
| Docker `--gpus all` not recognized | Install NVIDIA Container Toolkit |
| `permission denied` on Docker | `sudo usermod -aG docker $USER`, restart WSL |
| WSL2 not enabled | `dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart` |

## Next

[Phase 1 - LLM Serving](../phase-1-llm-serving/README.md)
