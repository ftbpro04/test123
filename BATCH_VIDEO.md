# One-click H3 full-video processing

In the dashboard, open **Process full video · automatic chunks**. Select one source video and one identity image, edit the prompt if desired, then click **Process full video** once. Splitting, sequential generation, trimming and joining are automatic. Download the finished MP4 from the Jobs section.

Defaults: 5-second chunks, fixed seed 123456789, longest edge 768, Character Swap V1.5 strength 1, FL2V Turbo8 strength 1, 8 steps, er_sde, normal scheduler, CFG 1. The image, prompt, seed and LoRA settings are fixed for the whole job. The dashboard submits the same rgthree Power Lora Loader graph used by the bundled workflow to ComfyUI's local queue.

The source is converted to 24 fps. Each chunk is padded by holding its last frame to H3's supported frame count (at least 124), including the short final segment. Generated results are trimmed to the corresponding source frame count. The final video retains the original audio by default (AAC); uncheck that option for silent output. Duration matches the normalized source to within one 24-fps frame. H3 does not guarantee exact motion, head-only isolation, or seamless boundaries. A fixed seed is not temporal conditioning across independent chunks.

Keep the pod running; the browser may be closed. After a failed chunk or pod restart, click **Resume** in Jobs. Completed chunks are reused and a pending ComfyUI job is reconciled before another is submitted. Only one full-video job runs at a time. Existing manual ComfyUI requests may delay it. Models must finish downloading before generation can succeed.

Persistent job files live in `/workspace/h3-batch/<job-id>/`, including state, per-chunk API prompts, rendered chunks and `final.mp4`. References and padded input clips live in `/workspace/ComfyUI/input/h3-batch/<job-id>/`. Generated raw results live in `/workspace/ComfyUI/output/h3-batch/<job-id>/`. Files remain for recovery; remove completed job folders manually when no longer needed. Never remove active job folders. A persistent `/workspace` volume is required to survive instance destruction.

The feature ships inside the Docker image. Start a new instance using the new image after its build completes; rebooting an old container does not install new dashboard code. No extra ports, model downloads or API keys are required.

Validation: `python -m unittest discover -s tests -v`. Tests run real FFmpeg splitting, padding, final-tail trimming, stitching, audio retention and resume, with a mocked ComfyUI generation response. HTTP tests check authorization, uploads, immutable running inputs, listing and downloads. GPU inference remains to be validated on a provisioned pod.
