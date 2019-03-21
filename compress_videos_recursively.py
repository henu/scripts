#!/usr/bin/env python3
import cv2
import os
import sys


def handle_path(path, videofiles):
    if os.path.isdir(path):
        for child in os.listdir(path):
            handle_path(os.path.join(path, child), videofiles)
    else:
        file_size = os.path.getsize(path)
        if file_size == 0:
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
    videofiles = []
    for arg in sys.argv[1:]:
        handle_path(arg, videofiles)
    print('Top 10 videofiles with worst compression')
    for videofile in sorted(videofiles, key=lambda t: t[1])[0:10]:
        print(videofile[0], videofile[1])
