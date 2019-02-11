import os

import ffmpeg

from camnode.workers import app


@app.task(name="process-captured-video")
def send_data(assignment_id, parent_data_point_id, video_path):
    output_path = f'{os.environ["CN_FRAMES_OUTPUT"]}/{assignment_id}-{ts}-%04d.jpg'
    (
    ffmpeg
        .input(name)
        .filter('fps', fps=5, round='up')
        .output(output_path)
        .run()
    )
    # app.send_task("honeycomb-send-data", args=[assignment_id, parent_data_point_id, ])
