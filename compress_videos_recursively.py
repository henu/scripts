#!/usr/bin/env python3
import cv2
import os
import magic
import random
import subprocess
import sys


def handle_path(path, videofiles):
    if os.path.isdir(path):
        for child in os.listdir(path):
            handle_path(os.path.join(path, child), videofiles)
    else:
        file_size = os.path.getsize(path)
        if file_size == 0:
            return

        # If file is not a video
        file_mimetype = magic.Magic(magic.MAGIC_MIME).from_file(path)
        if not file_mimetype.startswith('video/'):
            return

        # Get Video details
        video = cv2.VideoCapture(path)
        if not video.isOpened():
            return
        frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if frames < 2:
            return

        ratio = frames * width * height / file_size
        videofiles.append((path, ratio))


if __name__ == '__main__':

    constant_rate_factor = 32

    videofiles = []
    for arg in sys.argv[1:]:
        handle_path(arg, videofiles)
    for videofile in sorted(videofiles, key=lambda t: t[1]):
        answer = input('Ratio: {:.0f}, path: {}, Convert? [y/N/q] '.format(videofile[1], videofile[0]))
        if answer == 'q':
            break
        if answer == 'y':
            basename, _ext = os.path.splitext(videofile[0])
            temp_filename = '{}_temp_{}.mp4'.format(basename, random.randint(1, 99999999))
            new_filename = '{}.mp4'.format(basename)
            subprocess.run(
                [
                    'ffmpeg',
                    '-i', videofile[0],
                    '-vf', 'format=yuv420p',
                    '-codec:v', 'libx264',
                    '-crf', str(constant_rate_factor),
                    '-codec:a', 'aac',
                    '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',
                    temp_filename,
                ],
                stdout=subprocess.PIPE,
            )
            old_file_size = os.path.getsize(videofile[0])
            new_file_size = os.path.getsize(temp_filename)
            while True:
                answer2 = input('File size reduced {:.0f} %. Approve? [y/N/p] '.format(100 * (1 - new_file_size / old_file_size)))
                if answer2 == 'y':
                    os.remove(videofile[0])
                    os.rename(temp_filename, new_filename)
                    break
                if answer2 == 'p':
                    subprocess.run(
                        [
                            'mplayer',
                            '-fs',
                            videofile[0], temp_filename,
                        ],
                        stdout=subprocess.PIPE,
                    )
                else:
                    os.remove(temp_filename)
                    break
