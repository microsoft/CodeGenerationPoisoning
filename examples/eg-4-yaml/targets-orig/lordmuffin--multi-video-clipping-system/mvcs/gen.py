# Process incoming Request into YAML???

# More realistically a YAML Function/class for ingesting incoming data into yaml.

# Need something generic overall

# Also specific for our format.

# EXAMPLE YAML
# ------------
#
# Here is a sample `clip.yaml`.
#
#     # Absolute path to the OBS recording directory (source videos)
#     video-dir: "c:/OBS Captures"
#
#     # Absolute path to the directory to save clips to (must already exist)
#     output-dir: "c:/OBS Clips"
#
#     # List of source videos (identified by timestamp-based naming convention)
#     videos:
#       - date: "2020-01-01T00:00:00"
#         # Virtual "start" time in the source video (for output filename)
#         epoch: "0"
#
#         # Base title for all clips (for output filename)
#         title: "video 1"
#
#         # List of clips to create
#         clips:
#           - time: "0 - 5:00"
#             title: "first five minutes of the video"
#           - time: "1:30:00 - 1:30:01"
#             title: "one second long"
#
#       - date: "2020-01-02T00:00:00"
#         epoch: "15"
#         title: "video 2"
#         clips:
#           - time: "0 - 15"
#             title: "before the epoch"
#           - time: "15 - 30"
#             title: "on the epoch"
#           - time: "30 - 45"
#             title: "after the epoch"

import os.path
from os.path import isfile, join
from os import listdir
import yaml
from datetime import datetime
from datetime import timedelta
import pathlib
from mvcs.config import Config
from mvcs.time import datetime_from_str, datetime_to_str, timedelta_from_str, timedelta_to_str, timedelta_to_path_str
from mvcs.job import Video
from mvcs.error import Error

def generate_template(document, output_dir, video_dir):
    # Example YAML
    data = {
        'video-dir': str(video_dir),
        'output-dir': str(output_dir),
        'videos': []
    }

    print(yaml.safe_dump(data))
    stream = open(document, 'w')
    yaml.safe_dump(data, stream)
    stream.close()

def check_template(document, output_dir, video_dir):
    print("Checking for template: " + str(document))
    if os.path.isfile(document):
        print('YAML File detected.')

    else:
        print('Generating the file for you.')
        generate_template(document, output_dir, video_dir)
        check_template(document, output_dir, video_dir)

# def path_str(self, date: datetime.datetime, epoch: datetime.timedelta, title: str) -> str:
#     date_str = (date + epoch).strftime("%Y-%m-%d %H:%M:%S")
#     start_str = timedelta_to_path_str(self.start - epoch)
#     path_str = f"{date_str} - T+{start_str} - {title} - {self.title}.mkv"
#     return re.sub(r"[/\:]", "-", path_str.casefold())

def current_time():
    return datetime.now()

def latest_video(config: Config, date_time, extension, path):
    onlyfiles = [f for f in listdir(path) if isfile(join(path, f))]
    extension = [item for item in onlyfiles if extension in item]

    video_list = []

    for item in extension:
        video = Video.from_path(config, pathlib.Path(item))._replace(title=item)

        video_list.append(video)

    video_list = sorted(video_list, key=lambda x: x.date)
    return video_list[-1]

def add_video(document, date_time, epoch, title):
    date_time = datetime_to_str(date_time.date)
    print(date_time)
    print(type(date_time))
    with open(document, "r") as f:
        contents = yaml.safe_load(f)

    print(contents['videos'])
    # Check for existing video.

    if not contents['videos']:
        print("videos is empty")
        # Add Video
        print("Before: ", contents)
        print(date_time)
        data = {
            'date': date_time,
            'epoch': epoch,
            'title': title,
            'clips': []
        }
                
        contents['videos'].append(data)
        print("After: ", contents)

        with open(document, "w") as f:
            yaml.safe_dump(contents, f)

        return date_time
        print("End of video function.")

    if contents['videos']:
        print("Starting with Videos.")
        for video in contents['videos']:
            print(video)
            print("Vidoes Section Exists.")
            if video['date'] == date_time:
                print("Found Existing Video.")

                return "Found Existing Video."
        
            else:
                print("Running else statement!!!")
                # Add Video
                print("Before: ", contents)
                print(date_time)
                data = {
                    'date': date_time,
                    'epoch': epoch,
                    'title': title,
                    'clips': []
                }

                contents['videos'].append(data)
                print("After: ", contents)

                with open(document, "w") as f:
                    yaml.safe_dump(contents, f)

                return date_time
                print("End of video function.")

def add_clip(document, latest_video, window, title):
    print("Clipping")
    with open(document, "r") as f:
        contents = yaml.safe_load(f)

    data = {
        'time': window,
        'title': title
    }

    for item in contents['videos']:
        if item['date'] == datetime_to_str(latest_video.date):
            print("Before: ", str(item))
            item['clips'].append(data)
            print("After: ", str(item))
        
    with open(document, "w") as f:
        yaml.safe_dump(contents, f)

def trigger_clip(config: Config, video_time, clip_before_length, clip_after_length, document, latest_video, title):
    time = current_time()
    relative_time = time - latest_video.date

    clip_before_length = timedelta(seconds=clip_before_length)
    clip_after_length = timedelta(seconds=clip_after_length)

    print("Current Time: {}".format(time))
    print("Latest Video Time: {}".format(latest_video.date))
    print("Relative Time: {}".format(relative_time))

    start_window = relative_time - clip_before_length
    start_window = timedelta_to_str(start_window)

    end_window = relative_time + clip_after_length
    end_window = timedelta_to_str(end_window)


    print("Start Window: {}".format(start_window))
    print("End Window: {}".format(end_window))

    # # Fix if less than 0
    # if start_window <= 0:
    #     start_window = 0

    window = str(start_window) + " - " + str(end_window)
    print("Window: {}".format(window))

    print(type(latest_video.date))
    
    add_clip(document, latest_video, window, title)
