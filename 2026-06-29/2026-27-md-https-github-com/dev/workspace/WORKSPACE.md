# IMU+Visual Fusion Pipeline — Workspace

## Current Status
- P0 Steps 1-3: DONE (fusion_pipeline.py working)
- P0 Step 4: Drift baseline analysis — TODO
- P0 Step 5: End-to-end validation — TODO
- P1: Hardware (OK1126B) — PENDING
- P1: Timestamp sync — PENDING

## Key Files
- `work/IMU_Fusion/fusion_pipeline.py` — Main fusion pipeline
- `work/IMU_Fusion/pipeline_logger.py` — Logging module
- `work/IMU_Fusion/diagnose.py` — Pre-flight diagnostic
- `outputs/logs/` — Run logs and bug tracker
- `agiletact/` — GitHub synced repo

## Hardware
- D435i: S/N 261222075307, FW 5.17.0.10
- IMU Glove: COM122, 460800 baud, 35-byte frames
- GPU: RTX 4080 Laptop (12GB), ViTPose + HAMER
