# DragonMaid 7 Character Prompt Sheet 2026-08-21

This folder converts the attached pasted prompt text into a reproducible
ComfyUI batch.

Base checkpoint:

`sdxl\waiIllustriousSDXL_v150.safetensors`

Canvas:

`832x1216`

Sampler:

`dpmpp_2m`, `karras`, `28 steps`, `CFG 5.0`, `denoise 1.0`

Output prefix:

`D:\DMT-AI-Studio\output\DragonMaid\SevenCharacterSheet_20260821`

Character LoRAs:

- `dragonmaid_public_illustrious_v4\01_House_dragonmaid_illuXL_v1.safetensors`
- `dragonmaid_public_illustrious_v4\02_Kitchen_dragonmaid_illuXL_v1.1.safetensors`
- `dragonmaid_public_illustrious_v4\03_Parlor_dragonmaid_illuXL_v1.1.safetensors`
- `dragonmaid_curated_v4\04_小蓝_Laundry-SFW-only-pilot20-r32.safetensors`
- `dragonmaid_public_illustrious_v4\05_Nurse_dragonmaid_illuXL_v1.1.safetensors`
- `dragonmaid_public_illustrious_v4\06_Latys_dragonmaid_illuXL_v2.safetensors`
- `dragonmaid_public_illustrious_v4\07_Chamber_dragonmaid_illuXL_v1.1.safetensors`

Note:

小蓝 uses the SFW-only LoRA and includes an extra child-protection negative
block. Do not use adult or romantic prompts for her.
