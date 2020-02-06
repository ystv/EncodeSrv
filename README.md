# EncodeSrv

EncodeSrv is a Python driven automatic video encoding tool, using ffmpeg and a database to configure and run batches of encode jobs. It is used by YSTV to prepare videos for the website by transcoding high-bitrate NLE-exported files to formats for viewing online, playout and download (with watermarks on downloads). In addition to video and audio transcoding EncodeSrv can also apply MP4Box (http://www.videohelp.com/tools/mp4box) to move metadata to the video start and normalise volume using EBU R128 loudness analysis.

## Downloading EncodeSrv
    git clone https://github.com/YSTV/encodesrv.git

## Prerequisites
In order to run, EncodeSrv requires Python, psycopg2, irc and python-dateutil, along with access to a few PostgreSQL database tables to store encode formats and jobs.

You'll also need a copy of ffmpeg with the codecs you plan to use compiled in, take a look at https://github.com/rrah/ffmpeg-linux-build for the script we use to build ours.

## Configuration
Rename the file config.py.sample to config.py and fill in the database and email configuration options, along with a working directory that source and pass log files can be stored in temporarily.

## Using EncodeSrv
EncodeSrv uses a Python daemon class to run in the background as a server, start it with:

    python3 server.py start

Then set up some encode formats in the encode_formats table and add jobs to the encode_jobs table to make it work some magic!

It can also be run as a foreground process, by running:

	python3 __main__.py

## Database tables
The file schema.sql contains the SQL statements to generate the two database tables needed, along with some comments explaining what each column does.

For the purposes of the source and destination file locations, we use NFS and CIFS mounts so these appear as local paths but are on a remote server, ie /data/videos/web/playout is actually the video drive on our CasparCG playout server.

## IRC/Slack bots
Encodesrv also supports the use of IRC and/or Slack bots. These can be configured (and turned on and off) in config.py.
