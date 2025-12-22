# UI-TARS Setup Guide

## Quick Setup for Your HuggingFace Endpoint

Based on your deployment at: `https://x1z03h47yuwrjfni.us-east-1.aws.endpoints.huggingface.cloud`

### 1. Configure Environment Variables

Add to `/home/zren/new_massgen/MassGen/.env`:

```bash
# UI-TARS HuggingFace Inference Endpoint
UI_TARS_API_KEY=hf_xxxxxxxxxxxxx
UI_TARS_ENDPOINT=https://x1z03h47yuwrjfni.us-east-1.aws.endpoints.huggingface.cloud
```

**To get your HuggingFace token:**
1. Go to https://huggingface.co/settings/tokens
2. Create a new token or copy an existing one
3. Replace `hf_xxxxxxxxxxxxx` with your actual token

### 2. Install Dependencies

```bash
cd /home/zren/new_massgen/MassGen

# Install required packages
pip install openai playwright docker

# Install browsers for Playwright
playwright install chromium

# Optional: Install UI-TARS parser for advanced features
pip install ui-tars
```

### 3. Test Browser Automation

```bash
# Test with headless browser
massgen --config massgen/configs/tools/custom_tools/ui_tars_complete_example.yaml \
  "Search Google for 'Python asyncio' and summarize the first result"

# Test with visible browser (if DISPLAY is available)
DISPLAY=:20 massgen --config massgen/configs/tools/custom_tools/ui_tars_complete_example.yaml \
  "Navigate to Wikipedia and search for 'artificial intelligence'"
```

### 4. Test Docker Automation (Optional)

```bash
# Setup Docker container with X11
cd /home/zren/new_massgen/MassGen/scripts
./setup_docker_cua.sh

# Test Docker automation
massgen --config massgen/configs/tools/custom_tools/ui_tars_docker_example.yaml \
  "Open Firefox and browse to github.com"

# Enable VNC visualization (optional)
./enable_vnc_viewer.sh
vncviewer localhost:5900
```

## Your Endpoint Details

- **Model**: ByteDance-Seed/UI-TARS-1.5-7B
- **Engine**: vLLM (vllm/vllm-openai:v0.11.0)
- **GPU**: Nvidia A100 (1x GPU, 80 GB)
- **Region**: AWS us-east-1
- **Cost**: $2.50/hour while running
- **Scale-to-zero**: After 1 hour of inactivity

## Configuration Files

Three YAML configurations are available:

1. **ui_tars_browser_example.yaml** - Basic browser automation template
2. **ui_tars_docker_example.yaml** - Docker/Linux desktop automation template
3. **ui_tars_complete_example.yaml** - Complete example with your endpoint configured

## Example Tasks

### Simple Web Search
```bash
massgen --config massgen/configs/tools/custom_tools/ui_tars_complete_example.yaml \
  "Search for 'OpenAI GPT-4' on Google"
```

### Multi-Step Workflow
```bash
massgen --config massgen/configs/tools/custom_tools/ui_tars_complete_example.yaml \
  "Go to GitHub, search for 'ui-tars', open the first result, and tell me what the project is about"
```

### Complex Interaction
```bash
massgen --config massgen/configs/tools/custom_tools/ui_tars_complete_example.yaml \
  "Navigate to HackerNews, find the top story about AI, open it, and summarize the discussion"
```

### Docker Desktop Task
```bash
massgen --config massgen/configs/tools/custom_tools/ui_tars_docker_example.yaml \
  "Open Firefox, navigate to wikipedia.org, and search for 'machine learning'"
```

## Troubleshooting

### Issue: "UI-TARS API key not found"

**Solution**: Ensure `.env` file has `UI_TARS_API_KEY` set with your HuggingFace token.

### Issue: "UI-TARS endpoint not found"

**Solution**: Ensure `.env` file has `UI_TARS_ENDPOINT` set to your endpoint URL:
```bash
UI_TARS_ENDPOINT=https://x1z03h47yuwrjfni.us-east-1.aws.endpoints.huggingface.cloud
```

### Issue: "Playwright not installed"

**Solution**:
```bash
pip install playwright
playwright install chromium
```

### Issue: Endpoint returns errors

**Check endpoint status** at: https://ui.endpoints.huggingface.co/

Ensure:
- Endpoint is running (not scaled to zero)
- Model revision is up to date (683d002)
- No recent deployment errors

### Issue: Actions seem off-target

**Solution**: Verify display resolution matches configuration:
- Default config uses 1440x900
- Adjust `display_width` and `display_height` in YAML if needed

## Cost Management

Your endpoint costs $2.50/hour while running:

- **Scale-to-zero enabled**: Endpoint automatically stops after 1 hour of inactivity
- **Typical task cost**: $0.05-0.20 per task (5-10 minutes)
- **Monthly estimate**: ~$75-150 if used 1-2 hours daily

**To minimize costs:**
1. Let endpoint scale to zero when not in use
2. Use headless browser mode (faster, fewer screenshots)
3. Set appropriate `max_iterations` to avoid runaway tasks

## Next Steps

1. ✅ Environment variables configured in `.env`
2. ✅ Dependencies installed
3. ✅ Test browser automation with simple task
4. ⬜ Try complex multi-step workflows
5. ⬜ Optional: Setup Docker for desktop automation
6. ⬜ Optional: Enable VNC for visual monitoring

## Support

- **UI-TARS GitHub**: https://github.com/bytedance/UI-TARS
- **HuggingFace Model**: https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B
- **Paper**: https://arxiv.org/abs/2501.12326
- **Discord**: https://discord.gg/pTXwYVjfcs

For MassGen-specific issues, check the tool documentation:
- `massgen/tool/_ui_tars_computer_use/README.md`
- `massgen/tool/_ui_tars_computer_use/TOOL.md`
