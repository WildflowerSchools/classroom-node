import os

from pydantic import BaseSettings


class Settings(BaseSettings):
    VIDEO_CLIP_DURATION: int = 10
    VIDEO_CLIP_FRAME_RATE: int = 10
    VIDEO_CLIP_STAGING_DIR: str = f"{os.getcwd()}/staging"
    VIDEO_CLIP_OUTPUT_DIR: str = f"{os.getcwd()}/output"

    CAMERA_CAPTURE_FRAME_RATE: int = 30
    CAMERA_H_FLIP: bool = False
    CAMERA_V_FLIP: bool = False

    SERVER_HOST: str = ""
    SERVER_PORT: int = 8000

    MINIO_ENABLE: bool = False

    MINIO_BUCKET: str = "videos"
    MINIO_FOLDER: str = None
    MINIO_KEY: str = ""
    MINIO_SECRET: str = ""
    MINIO_SERVICE_HOST: str = ""
    MINIO_SERVICE_PORT: int = 9000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
