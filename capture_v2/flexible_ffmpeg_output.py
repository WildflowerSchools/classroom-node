import signal
import subprocess

import prctl

from picamera2.outputs import FfmpegOutput

class FlexibleFfmpegOutput(FfmpegOutput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start(self):
        general_options = ['-loglevel', 'warning',
                           '-y']  # -y means overwrite output without asking
        # We have to get FFmpeg to timestamp the video frames as it gets them. This isn't
        # ideal because we're likely to pick up some jitter, but works passably, and I
        # don't have a better alternative right now.
        video_input = ['-use_wallclock_as_timestamps', '1',
                       '-thread_queue_size', '64',  # necessary to prevent warnings
                       '-i', '-',
                       '-b:v', '4M']
        video_codec = ['-c:v', 'h264_v4l2m2m',
                       '-f', 'mp4']
        audio_input = []
        audio_codec = []
        if self.audio:
            audio_input = ['-itsoffset', str(self.audio_sync),
                           '-f', 'pulse',
                           '-sample_rate', str(self.audio_samplerate),
                           '-thread_queue_size', '512',  # necessary to prevent warnings
                           '-i', self.audio_device]
            audio_codec = ['-b:a', str(self.audio_bitrate),
                           '-c:a', self.audio_codec]

        command = ['ffmpeg'] + general_options + audio_input + video_input + \
            audio_codec + video_codec + self.output_filename.split()
        # The preexec_fn is a slightly nasty way of ensuring FFmpeg gets stopped if we quit
        # without calling stop() (which is otherwise not guaranteed).
        self.ffmpeg = subprocess.Popen(command, stdin=subprocess.PIPE, preexec_fn=lambda: prctl.set_pdeathsig(signal.SIGKILL))
        self.recording = True
        
        super(FfmpegOutput, self).start()
