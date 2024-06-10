import os
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"
import moviepy.video.io.ImageSequenceClip

image_folder='/Users/mscottod/Documents/HEAT/data/sparc_000000_test_rotation2Hz/Images/Temperature/'
fps=1

image_files = [os.path.join(image_folder,img)
               for img in os.listdir(image_folder)
               if img.endswith(".png")]
clip = moviepy.video.io.ImageSequenceClip.ImageSequenceClip(image_files, fps=fps)
clip.write_videofile('T_2Hz.mp4')