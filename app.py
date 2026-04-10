import os
import uuid
import asyncio
from typing import List, Optional, Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

try:
    import higgsfield_client
except ImportError as e:
    raise RuntimeError(
        "Missing dependency 'higgsfield-client'. Install requirements.txt first."
    ) from e


HF_IMAGE_MODEL_ID = os.getenv("HF_IMAGE_MODEL_ID", "YOUR_IMAGE_MODEL_ID")
HF_VIDEO_MODEL_ID = os.getenv("HF_VIDEO_MODEL_ID", "YOUR_VIDEO_MODEL_ID")
HF_DEFAULT_RESOLUTION = os.getenv("HF_DEFAULT_RESOLUTION", "2K")
HF_DEFAULT_ASPECT_RATIO = os.getenv("HF_DEFAULT_ASPECT_RATIO", "9:16")
HF_VIDEO_QUALITY = os.getenv("HF_VIDEO_QUALITY", "standard")
HF_VIDEO_DURATION = int(os.getenv("HF_VIDEO_DURATION", "5"))
APP_ENV = os.getenv("APP_ENV", "development")


class GenerateImagesRequest(BaseModel):
    frame_01_prompt: str = Field(..., min_length=10)
    frame_02_prompt: str = Field(..., min_length=10)
    frame_03_prompt: str = Field(..., min_length=10)
    aspect_ratio: str = Field(default=HF_DEFAULT_ASPECT_RATIO)
    resolution: str = Field(default=HF_DEFAULT_RESOLUTION)
    camera_fixed: bool = Field(default=True)


class GenerateVideoRequest(BaseModel):
    video_prompt: str = Field(..., min_length=10)
    image_urls: List[str] = Field(..., min_length=1)
    aspect_ratio: str = Field(default=HF_DEFAULT_ASPECT_RATIO)
    duration: int = Field(default=HF_VIDEO_DURATION, ge=1, le=15)
    quality: str = Field(default=HF_VIDEO_QUALITY)
    motion_strength: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class HealthResponse(BaseModel):
    ok: bool
    env: str
    image_model_id: str
    video_model_id: str


app = FastAPI(
    title="Higgsfield Bridge Server",
    version="1.0.0",
    description="Bridge API for n8n -> Higgsfield image/video generation.",
)


def _assert_env_ready() -> None:
    missing = []
    if not (os.getenv("HF_KEY") or (os.getenv("HF_API_KEY") and os.getenv("HF_API_SECRET"))):
        missing.append("HF_KEY or HF_API_KEY + HF_API_SECRET")
    if HF_IMAGE_MODEL_ID == "YOUR_IMAGE_MODEL_ID":
        missing.append("HF_IMAGE_MODEL_ID")
    if HF_VIDEO_MODEL_ID == "YOUR_VIDEO_MODEL_ID":
        missing.append("HF_VIDEO_MODEL_ID")
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Server configuration incomplete: {', '.join(missing)}"
        )


async def _subscribe_async(model_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: higgsfield_client.subscribe(model_id, arguments=arguments)
    )


async def _generate_single_image(
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    camera_fixed: bool,
) -> str:
    result = await _subscribe_async(
        HF_IMAGE_MODEL_ID,
        arguments={
            "prompt": prompt,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "camera_fixed": camera_fixed,
        },
    )

    images = result.get("images") or []
    if not images or not images[0].get("url"):
        raise HTTPException(status_code=502, detail=f"Image generation returned no usable URL: {result}")
    return images[0]["url"]


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        ok=True,
        env=APP_ENV,
        image_model_id=HF_IMAGE_MODEL_ID,
        video_model_id=HF_VIDEO_MODEL_ID,
    )


@app.post("/generate-images")
async def generate_images(payload: GenerateImagesRequest):
    _assert_env_ready()

    prompts = [
        payload.frame_01_prompt,
        payload.frame_02_prompt,
        payload.frame_03_prompt,
    ]

    image_urls = []
    for prompt in prompts:
        url = await _generate_single_image(
            prompt=prompt,
            aspect_ratio=payload.aspect_ratio,
            resolution=payload.resolution,
            camera_fixed=payload.camera_fixed,
        )
        image_urls.append(url)

    return {
        "job_id": str(uuid.uuid4()),
        "image_model_id": HF_IMAGE_MODEL_ID,
        "image_urls": image_urls,
    }


@app.post("/generate-video")
async def generate_video(payload: GenerateVideoRequest):
    _assert_env_ready()

    arguments: Dict[str, Any] = {
        "prompt": payload.video_prompt,
        "input_images": payload.image_urls,
        "aspect_ratio": payload.aspect_ratio,
        "duration": payload.duration,
        "quality": payload.quality,
    }

    if payload.motion_strength is not None:
        arguments["motion_strength"] = payload.motion_strength

    result = await _subscribe_async(HF_VIDEO_MODEL_ID, arguments=arguments)

    video_url = None
    if isinstance(result.get("video"), dict):
        video_url = result["video"].get("url")
    if not video_url:
        videos = result.get("videos") or []
        if videos and isinstance(videos[0], dict):
            video_url = videos[0].get("url")

    if not video_url:
        raise HTTPException(status_code=502, detail=f"Video generation returned no usable URL: {result}")

    return {
        "job_id": str(uuid.uuid4()),
        "video_model_id": HF_VIDEO_MODEL_ID,
        "video_url": video_url,
        "raw_result": result,
    }
