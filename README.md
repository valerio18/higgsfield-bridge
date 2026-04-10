# Higgsfield Bridge Server for n8n

This FastAPI app gives you two simple endpoints for your n8n workflow:

- `POST /generate-images`
- `POST /generate-video`

It is designed so n8n talks to **your bridge server**, and the bridge server talks to Higgsfield through the official Python SDK.

## What you still need to fill in

You still need to insert the correct model IDs for:
- `HF_IMAGE_MODEL_ID` = your Nano Banana 2 model ID
- `HF_VIDEO_MODEL_ID` = your Kling 3.0 model ID

Those exact IDs are intentionally left as placeholders.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app:app --reload
```

## Railway deployment

1. Create a new Railway project
2. Upload these files or connect the repo
3. Add environment variables from `.env.example`
4. Deploy
5. Use the generated domain in n8n

Your base URL will look like:
`https://your-app-name.up.railway.app`

Then in n8n use:
- `https://your-app-name.up.railway.app/generate-images`
- `https://your-app-name.up.railway.app/generate-video`

## n8n request body examples

### /generate-images
```json
{
  "frame_01_prompt": "{{$json.frame_01_prompt}}",
  "frame_02_prompt": "{{$json.frame_02_prompt}}",
  "frame_03_prompt": "{{$json.frame_03_prompt}}",
  "aspect_ratio": "{{$json.aspect_ratio}}"
}
```

### /generate-video
```json
{
  "video_prompt": "{{$json.video_prompt}}",
  "image_urls": {{$json.image_urls}},
  "aspect_ratio": "{{$json.aspect_ratio}}"
}
```

## Notes

The official Higgsfield Python SDK README shows:
- installation via `pip install higgsfield-client`
- authentication through `HF_KEY` or `HF_API_KEY` + `HF_API_SECRET`
- `subscribe(...)` usage with a model ID and generation arguments. citeturn378263search1

Community Higgsfield tooling also notes that video generation expects a required `prompt` and `input_images` as an array. citeturn548903view0
