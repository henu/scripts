#!/usr/bin/env python3
import cv2
import os
import magic
import random
import subprocess
import sys


DEFAULT_CONSTANT_RATE_FACTOR = 28

AUTO_DISCARD_RATIO = 1.25


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


def convert_video(source, target, crf, angle):
    args = [
            'ffmpeg',
            '-loglevel', 'quiet',
            '-i', source,
            '-vf', 'format=yuv420p',
            '-codec:v', 'libx264',
            '-crf', str(crf),
            '-codec:a', 'aac',
            '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',
        ]
    if angle != 0:
        args.append('-vf')
        args.append(','.join(['transpose=1'] * angle))
    args.append(target)
    subprocess.run(args, stdout=subprocess.PIPE)


if __name__ == '__main__':

    videofiles = []
    for arg in sys.argv[1:]:
        handle_path(arg, videofiles)
    exit = False
    for videofile in sorted(videofiles, key=lambda t: t[1]):
        print('Converting {} (ratio: {:.1f})'.format(videofile[0], videofile[1]))
        basename, _ext = os.path.splitext(videofile[0])
        temp_filename = '{}_temp_{}.mp4'.format(basename, random.randint(1, 99999999))
        new_filename = '{}.mp4'.format(basename)
        angle = 0
        crf = DEFAULT_CONSTANT_RATE_FACTOR
        convert_video(videofile[0], temp_filename, crf, angle)
        old_file_size = os.path.getsize(videofile[0])
        new_file_size = os.path.getsize(temp_filename)

        # If compression is too bad, then automatically discard
        if new_file_size * AUTO_DISCARD_RATIO > old_file_size:
            print('File size reduced only {:.0f} %, which is too low. Skipping.'.format(100 * (1 - new_file_size / old_file_size)))
            os.remove(temp_filename)
            continue

        while True:
            answer = input('File size reduced {:.0f} %. Approve? [y/N/p/b/q/r/R/+/-] '.format(100 * (1 - new_file_size / old_file_size)))
            if answer == 'q':
                os.remove(temp_filename)
                exit = True
                break
            if answer == 'y':
                os.remove(videofile[0])
                os.rename(temp_filename, new_filename)
                break
            if answer == 'p':
                subprocess.run(
                    [
                        'mplayer',
                        '-fs',
                        '-really-quiet',
                        temp_filename,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
            elif answer == 'b':
                subprocess.run(
                    [
                        'mplayer',
                        '-fs',
                        '-really-quiet',
                        videofile[0], temp_filename,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
            elif answer in ['r', 'R'] or (answer and (answer == '+' * len(answer) or answer == '-' * len(answer))):
                if answer == 'r':
                    angle = (angle + 1) % 4
                elif answer == 'R':
                    angle = (angle + 3) % 4
                elif answer == '+' * len(answer):
                    crf -= len(answer)
                elif answer == '-' * len(answer):
                    crf += len(answer)
                print('Converting again with CRF {} and angle {}...'.format(crf, angle))
                os.remove(temp_filename)
                convert_video(videofile[0], temp_filename, crf, angle)
                old_file_size = os.path.getsize(videofile[0])
                new_file_size = os.path.getsize(temp_filename)
            else:
                os.remove(temp_filename)
                break
        if exit:
            break
