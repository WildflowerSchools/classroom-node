import os

from pydantic import BaseSettings


class Settings(BaseSettings):
    VIDEO_CLIP_DURATION: int = 10
    VIDEO_CLIP_FRAME_RATE: int = 10
    VIDEO_CLIP_OUTPUT_DIR: str = f"{os.getcwd()}/output"

    CAMERA_CAPTURE_FRAME_RATE: int = 30

    SERVER_HOST: str = ''
    SERVER_PORT: int = 8000

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
