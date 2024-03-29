#!/usr/bin/python
# v1.3
#   Special filename case, where filename has valid data but EXIF is screwed up
#   Fix re-strings and other little things.
# v1.2
#   More exif keys for dates. This makes it possible to handle some videos
#   too.
# v1.1
#   Can now read date from filename, if not found from exif data.
# v1.0
#   Basic stuff works

import calendar
import datetime
import os
import pytz
import random
import re
import subprocess
import sys
import time

def run_command(args):
    p = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    output = p.communicate()
    if p.returncode:
        raise Exception(output[1].splitlines())
    return output[0].splitlines()

def read_exif(path):
    exif_raw = run_command(['exiftool', '-t', path])
    result = {}
    for line in exif_raw:
        keypair = line.split('\t')
        result[keypair[0]] = keypair[1]
    return result

def get_member_as_string_if_exists(d, k):
    if not k in d: return ''
    else: return str(d[k])

def to_unix_timestamp(year, month, day, hour, minute, second):
    if year < 1800:
        return -1
    t = (year, month, day, hour, minute, second, 0, 0, 0)
    return calendar.timegm(t)

def from_unix_timestamp(timestamp, timestamp_in_utc=False):
    if timestamp_in_utc:
        dt = datetime.datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC)
        return dt.astimezone(pytz.timezone('Europe/Helsinki')).strftime('%Y-%m-%d %H.%M.%S')
    t = time.gmtime(timestamp)
    return time.strftime('%Y-%m-%d %H.%M.%S', t)

# Tries to read date as unix timestamp. Returns -1 if this is impossible
def try_to_read_date(date_str):
    # First try with am/pm
    m = re.match(r'(?P<year>[0-9]{2,4})[_\-.:](?P<month>[0-9]{1,2})[_\-.:](?P<day>[0-9]{1,2})[_\-.: ](?P<hour>[0-9]{1,2})[_\-.:](?P<min>[0-9]{1,2})[_\-.:](?P<sec>[0-9]{1,2})[_\-.:](?P<ampm>(pm|PM|am|AM))', date_str)
    if m:
        # Convert hours to sensible format
        ampm = m.groupdict()['ampm']
        hour = int(m.groupdict()['hour'])
        if ampm == 'am' or ampm == 'AM':
            if hour == 12:
                hour = 0
        else:
            if hour != 12:
                hour += 12
        unixtime = to_unix_timestamp(int(m.groupdict()['year']), int(m.groupdict()['month']), int(m.groupdict()['day']), hour, int(m.groupdict()['min']), int(m.groupdict()['sec']))
        # Discard too old dates
        if unixtime <= 0: return -1
        return unixtime
    # Try without am/pm
    m = re.match(r'(?P<year>[0-9]{2,4})[_\-.:](?P<month>[0-9]{1,2})[_\-.:](?P<day>[0-9]{1,2})[_\-.: ](?P<hour>[0-9]{1,2})[_\-.:](?P<min>[0-9]{1,2})[_\-.:](?P<sec>[0-9]{1,2})', date_str)
    if m:
        unixtime = to_unix_timestamp(int(m.groupdict()['year']), int(m.groupdict()['month']), int(m.groupdict()['day']), int(m.groupdict()['hour']), int(m.groupdict()['min']), int(m.groupdict()['sec']))
        # Discard too old dates
        if unixtime <= 0: return -1
        return unixtime
    # Try without characters between numbers
    m = re.match(r'(?P<year>[0-9]{4})(?P<month>[0-9]{2})(?P<day>[0-9]{2})[_\-.: ]?(?P<hour>[0-9]{2})(?P<min>[0-9]{2})(?P<sec>[0-9]{2})', date_str)
    if m:
        unixtime = to_unix_timestamp(int(m.groupdict()['year']), int(m.groupdict()['month']), int(m.groupdict()['day']), int(m.groupdict()['hour']), int(m.groupdict()['min']), int(m.groupdict()['sec']))
        # Discard too old dates
        if unixtime <= 0: return -1
        return unixtime
    return -1

def try_to_get_date_from_filename_primary(filename):
    """ This is for some software that screws up the
    EXIF data, but leaves correct date to filename.
    """

    m = re.search(r'^(?P<date>[0-9]{8}_[0-9]{6})\.', filename)
    if m:
        return m.groupdict()['date']
    m = re.search(r'InShot_(?P<date>[0-9]{8}_[0-9]{6})[0-9]{3}\.jpg', filename)
    if m:
        return m.groupdict()['date']
    m = re.search(r'org_[0-9a-f]{16}_(?P<unixtime>[0-9]{10})[0-9]{3}(\.|_)', filename)
    if m:
        unixtime = int(m.groupdict()['unixtime'])
        return from_unix_timestamp(unixtime, timestamp_in_utc=True)
    return '';

def try_to_get_date_from_filename_secondary(filename):
    # First try with am/pm
    m = re.search(r'(?P<date>[0-9]{4}[_\-.:][0-9]{2}[_\-.:][0-9]{2}[_\-.: ][0-9]{2}[_\-.:][0-9]{2}[_\-.:][0-9]{2}[_\-.:](pm|PM|am|AM))', filename)
    if m:
        return m.groupdict()['date']
    # Try without am/pm
    m = re.search(r'(?P<date>[0-9]{4}[_\-.:][0-9]{2}[_\-.:][0-9]{2}[_\-.: ][0-9]{2}[_\-.:][0-9]{2}[_\-.:][0-9]{2})', filename)
    if m:
        return m.groupdict()['date']
    return "";

def read_photo(path):
    exif = read_exif(path)

    # Form identification for camera
    cam_id = ''
    cam_id += get_member_as_string_if_exists(exif, 'Camera Model Name')
    cam_id += get_member_as_string_if_exists(exif, 'Make')
    cam_id += get_member_as_string_if_exists(exif, 'Maker Note Version')
    cam_id += get_member_as_string_if_exists(exif, 'Serial Number')

    # Get date
    date = -1
    if date < 0: date = try_to_read_date(try_to_get_date_from_filename_primary(os.path.basename(path)))
    if date < 0: date = try_to_read_date(get_member_as_string_if_exists(exif, 'Create Date'))
    if date < 0: date = try_to_read_date(get_member_as_string_if_exists(exif, 'Date/Time Original'))
    if date < 0: date = try_to_read_date(get_member_as_string_if_exists(exif, 'Date Time'))
    if date < 0: date = try_to_read_date(get_member_as_string_if_exists(exif, 'Create Date'))
    if date < 0: date = try_to_read_date(get_member_as_string_if_exists(exif, 'Media Create Date'))
    if date < 0: date = try_to_read_date(get_member_as_string_if_exists(exif, 'Track Create Date'))
    if date < 0: date = try_to_read_date(get_member_as_string_if_exists(exif, 'Modify Date'))
    if date < 0: date = try_to_read_date(get_member_as_string_if_exists(exif, 'Media Modify Date'))
    if date < 0: date = try_to_read_date(get_member_as_string_if_exists(exif, 'Track Modify Date'))
    if date < 0: date = try_to_read_date(get_member_as_string_if_exists(exif, 'File Modification Date/Time'))
    if date < 0: date = try_to_read_date(try_to_get_date_from_filename_secondary(os.path.basename(path)))
    if date < 0: date = 0

    # Form final information
    result = {}
    result['path'] = path
    result['cam_id'] = cam_id
    result['date'] = date

    # Decide some name for camera
    random.seed(cam_id)
    name = ''
    for i in range(2):
        name += random.choice('bcdfghjklmnpqrstvwxz')
        name += random.choice('aeiouy')
    result['cam_name'] = name.capitalize()

    return result

def print_lines(lines):
    # First calculate widths of columns
    col_widths = []
    for line in lines:
        for col_id in range(len(line)):
            col_width = len(str(line[col_id]))
            if len(col_widths) == col_id:
                col_widths.append(col_width)
            else:
                col_widths[col_id] = max(col_widths[col_id], col_width)
    # Then print
    for line in lines:
        line_str = ''
        for col_id in range(len(line)):
            cell = str(line[col_id])
            line_str += cell;
            line_str += ' ' * (1 + col_widths[col_id] - len(cell))
        print line_str

def order_by_date(photos):
    return sorted(photos, key = lambda photo: photo['date'])

def print_photos(photos, cams):
    last_date = 0
    lines = []
    lines.append(['Photo', 'Camera', 'Alias', 'Date', 'Unixtime', 'Time diff'])
    for photo in photos:
        time_diff = photo['date'] - last_date
        last_date = photo['date']
        lines.append([photo['path'], cams[photo['cam_id']], photo['cam_name'], from_unix_timestamp(photo['date']), photo['date'], time_diff])
    print_lines(lines);

def main():

    # Read all photos and used cameras
    print 'Analyzing photos...'
    photos = []
    cam_ids = set()
    for arg_id in range(1, len(sys.argv)):
        sys.stdout.write('\r' + str(100 * (arg_id - 1) / (len(sys.argv) - 1)) + ' %')
        sys.stdout.flush()
        photo = read_photo(sys.argv[arg_id])
        photos.append(photo)
        cam_ids.add(photo['cam_id'])
    sys.stdout.write('\r100 %\n')
    sys.stdout.flush()

    # Form mapping of camera IDs
    cam_ids = sorted(cam_ids)
    cams = {}
    for cam_id in cam_ids:
        cams[cam_id] = len(cams) + 1

    print 'It seems there is ' + str(len(cam_ids)) + ' cameras.'

    print 'Here are the photos, ordered by date:'
    photos = order_by_date(photos)
    print_photos(photos, cams)

    while True:

        userinput = raw_input('> ')
        userinput = userinput.split()

        if len(userinput) > 0 and userinput[0] == 'addtime':
            if len(userinput) < 2:
                print 'ERROR: Missing camera ID and time!'
            elif len(userinput) < 3:
                print 'ERROR: Missing time!'
            else:
                cam_id = int(userinput[1])
                addtime = int(userinput[2])
                for photo in photos:
                    if cams[photo['cam_id']] == cam_id:
                        photo['date'] += addtime
        elif len(userinput) > 0 and userinput[0] == 'list':
            photos = order_by_date(photos)
            print_photos(photos, cams)
        elif len(userinput) > 0 and userinput[0] == 'quit':
            break
        elif len(userinput) > 0 and userinput[0] == 'rename':
            photos = order_by_date(photos)
            max_seen_date = 0
            for photo in photos:
                date = int(photo['date'])
                # Ensure two photos have no same date
                while date <= max_seen_date:
                    date = date + 1
                max_seen_date = date
                # Form new filename
                old_path = photo['path']
                parent_and_filename = os.path.split(old_path)
                extension = os.path.splitext(parent_and_filename[1])[1]
                new_path = os.path.join(parent_and_filename[0], from_unix_timestamp(date) + extension)

                print old_path + ' ---> ' + new_path
                os.rename(old_path, new_path)
            break
        elif len(userinput) > 0 and userinput[0] == 'forget':
            if len(userinput) < 1:
                print 'ERROR: Missing camera ID!'
            else:
                cam_id = int(userinput[1])
                photo_i = 0
                while photo_i < len(photos):
                    photo = photos[photo_i]
                    if cams[photo['cam_id']] == cam_id:
                        del photos[photo_i]
                    else:
                        photo_i += 1
        else:
            print 'ERROR: Invalid command!'
            print 'Commands are:'
            print '\taddtime <CAMERA_ID> <SECONDS>'
            print '\tlist'
            print '\tquit'
            print '\trename'
            print '\tforget <CAMERA_ID>'

if __name__ == '__main__':
    main()
