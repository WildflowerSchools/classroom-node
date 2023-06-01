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

    STREAMING_SERVER_ENABLE: bool = TRUE
    STREAMING_SERVER_HOST: str = ""
    STREAMING_SERVER_PORT: int = 8000

    MINIO_ENABLE: bool = False

    MINIO_BUCKET: str = "videos"
    MINIO_FOLDER: str = None
    MINIO_KEY: str = ""
    MINIO_SECRET: str = ""
    MINIO_SERVICE_HOST: str = ""
    MINIO_SERVICE_PORT: int = 9000

    CLASSROOM_ENVIRONMENT_ID: str = None

    HONEYCOMB_URI: str = "https://honeycomb.api.wildflower-tech.org/graphql"
    HONEYCOMB_DOMAIN: str = "wildflowerschools.auth0.com"
    HONEYCOMB_CLIENT_ID: str = None
    HONEYCOMB_CLIENT_SECRET: str = None
    HONEYCOMB_AUDIENCE: str = "wildflower-tech.org"

    FINALIZE_VIDEO_IN_BACKGROUND: bool = (
        False  # Dangerous - could lead to many FFMPEG jobs which could take down the Pi
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
