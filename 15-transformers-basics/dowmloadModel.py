import huggingface_hub

# huggingface_hub.snapshot_download(
#   repo_id="Qwen/Qwen3-0.6B",
#   local_dir=".\models/Qwen3-0.6B",
# )

huggingface_hub.snapshot_download(
  repo_id="zai-org/chatglm3-6b",
  local_dir=".\models/chatglm3-6b",
)