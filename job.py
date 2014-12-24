# Imports
import threading
import psycopg2
import Queue
import os.path
import shlex
import shutil
import logging
import time
import subprocess
import pexpect
import re
from datetime import datetime
from string import maketrans
from config import Config

THREADPOOL = Queue.Queue(0)

class FFmpegJob (threading.Thread):
    """Encode job handler

    Run an individual encode job - assemble an ffmpeg command from the
    database and run it

    """

    THREADPOOL = None

    FormatString = """
    ffmpeg -i \"{_SourceFile}\" -passlogfile \"{_PassLogFile}\"
    {args_beginning} -vcodec {video_codec} -b:v {video_bitrate}
    {_VPre} -pass {_Pass} -s {video_resolution} -aspect {aspect_ratio}
    {args_video} -acodec {audio_codec} -ar {audio_samplerate}
    -ab {audio_bitrate} {args_audio} -threads 0 {args_end} -f {container}
    -y \"{_TempDest}\"
    """.translate(maketrans("\n\t\r", "\x20"*3))


    def _update_status(self, status, id):
        """Wrapper to change the DB status of a job """
        try:
            logging.debug('Job {}: '.format(id) + status)
            self.dbcur.execute("UPDATE encode_jobs SET status=\'{}\' WHERE id = {}".format(status,id))
            self.dbconn.commit()
        except:
            logging.exception("Job {}: Failed to update status in DB".format(id))

    def intify(self, T):
        return tuple([int(e) for e in T])

    def _copyfile(self, src, dst, desc):
        logging.debug('(pv -ni 5 "{}" > "{}") 2>&1'.format(src, dst))
        p = subprocess.Popen('(pv -ni 5 "{}" > "{}") 2>&1'.format(src, dst), stdout=subprocess.PIPE, shell=True)

        while p.poll() != 0:
            line = p.stdout.readline()
            if not line.rstrip().isdigit():
                raise Exception("Error during copy " + line)
            self._update_status("{} {}%".format(desc, line.rstrip()), self.jobreq['id'])

    def run(self):
        while True:
            self.jobreq = THREADPOOL.get()
            if self.jobreq != None:
                try:
                    self.run_impl()
                except:
                    logging.exception("An unhandled exception occured. The thread has been 'reset'")
            else:
                time.sleep(3)

    def run_impl(self):

        logging.info('starting job {}'.format(self.jobreq['id']))

        # Create database connection
        try:
            self.dbconn = psycopg2.connect(**Config['database'])
            self.dbcur  = self.dbconn.cursor()
        except:
            logging.exception("Job {}: Could not connect to database".format(self.jobreq['id']))
            return

        # Check whether source file exists
        try:
            with open(self.jobreq['source_file']): pass
        except IOError:
            logging.exception("Job {}: Unable to open source file".format(self.jobreq['id']))
            self._update_status("Error", self.jobreq['id'])
            return

        # Create temp dir for this job
        try:
            dirname = os.path.join(Config['tmpfolder'], "{}--encode--{}".format(
                os.path.basename(self.jobreq['source_file']), str(datetime.now()).replace(' ', '-')
            ))
            os.mkdir(dirname, 0775)
        except:
            logging.exception("Job {} - Failed to create temporary directory".format(self.jobreq['id']))
            self._update_status("Error", self.jobreq['id'])
            return

        try:
            destleaf = os.path.basename(self.jobreq['destination_file'])
            srcleaf = "{}-source{}".format(*os.path.splitext(destleaf))
            srcpath = os.path.join(dirname, srcleaf)
        except:
            logging.exception("Job {} - Debug 2 failed".format(self.jobreq['id']));
            self._update_status("Error", self.jobreq['id'])
            return



        # Get job settings from database
        try:
            cols = ('container', 'video_bitrate', 'video_bitrate_tolerance','video_codec',
                    'video_resolution', 'audio_bitrate', 'audio_samplerate','audio_codec',
                    'vpre_string', 'preset_string', 'aspect_ratio', 'args_beginning', 'args_video',
                    'args_audio', 'args_end', 'apply_mp4box', 'normalise_level')
            self.dbcur.execute("SELECT {} FROM encode_formats WHERE id = {}".format(
                ", ".join(cols), self.jobreq['format_id']) )

            fetched = [x if x is not None else '' for x in self.dbcur.fetchone()]
            args = dict(zip(cols, fetched))

            # Process the special ones (the /^_[A-Z]/ ones)
            args['_SourceFile'] = srcpath
            args['_PassLogFile'] = os.path.join(dirname, "pass.log")

            args['_VPre'] = args['preset_string']
            args['_TempDest'] = os.path.join(dirname, os.path.basename(self.jobreq['destination_file']))
        except:
            logging.exception("Job {} - Debug 3 failed".format(self.jobreq['id']));
            self._update_status("Error", self.jobreq['id'])
            return

        # Copy to local folder, rename source
        try:
            self._copyfile(self.jobreq['source_file'], srcpath, 'Copying Source')
            #shutil.copyfile(self.jobreq['source_file'], srcpath)
        except:
            logging.exception("Job {}: couldn't copy from {} to {}".format(
                self.jobreq['id'],self.jobreq['source_file'], dirname
            ))
            self._update_status("Error", self.jobreq['id'])
            return

        # Analyse video for normalisation if requested
        if args['normalise_level'] is not '':
            try:
                self._update_status("Analysing audio", self.jobreq['id'])

                level = float(args['normalise_level'])
                analysis = subprocess.check_output(["ffmpeg", "-i", srcpath, "-af",
                    "ebur128", "-f", "null", "-y", "/dev/null"], stderr=subprocess.STDOUT)
                maxvolume = re.search(r"Integrated loudness:$\s* I:\s*(-?\d*.\d*) LUFS", analysis,
                    flags=re.MULTILINE).group(1)

                # Calculate normalisation factor
                change = level - float(maxvolume)
                increase_factor = 10 ** ((level - float(maxvolume)) / 20)

                logging.debug('Multiplying volume by {:.2f}'.format(increase_factor))
                args['args_audio'] += '-af volume={0}'.format(increase_factor)
            except:
                logging.exception("Job {}: Failed normalising volume".format(self.jobreq['id']))
                self._update_status("Error", self.jobreq['id'])
                return

        # Run encode job
        try:
            self.dbcur.execute("UPDATE encode_jobs SET working_directory=%s WHERE id=%s",
                (dirname, self.jobreq['id'])
            ) ; self.dbconn.commit()
        except:
            logging.exception("Job {}: Failed to update database".format(self.jobreq['id']))
            self._update_status("Error", self.jobreq['id'])
            return

        for _pass in (1, 2):
            try:
                logging.debug("Updating Status.")
                self._update_status("Encoding Pass {}".format(_pass), self.jobreq['id'])

                logging.debug("Setting args.")
                args['_Pass'] = _pass
                FormatString = FFmpegJob.FormatString.format(**args)

                logging.debug("Opening subprocess: {}".format(FormatString))
                try:
                    ffmpeg_process = pexpect.spawn(FormatString.strip())

                    cpl = ffmpeg_process.compile_pattern_list([
                        pexpect.EOF,
                        ".*Duration: ([0-9]{2}):([0-9]{2}):([0-9]{2}).([0-9]{2}).*",
                        ".*time=([0-9]{2}):([0-9]{2}):([0-9]{2}).([0-9]{2}).*",
                        '(.+)'
                    ])

                    while True:
                        time.sleep(20)
                        i = ffmpeg_process.expect_list(cpl, timeout=10)
                        if (i == 0):
                            break
                        elif (i == 1):
                            (hours, mins, secs, frames) = self.intify(ffmpeg_process.match.group(1, 2, 3, 4))
                            totalTime = (((((hours * 60) + mins) * 60) + secs) * 100) + frames
                            ffmpeg_process.close
                        elif (i == 2):
                            (hours, mins, secs, frames) = self.intify(ffmpeg_process.match.group(1, 2, 3, 4))
                            currentTime = (((((hours * 60) + mins) * 60) + secs) * 100) + frames
                            progress = (currentTime * 100) / totalTime

                            self._update_status("Encoding Pass {} {}%".format(_pass, progress), self.jobreq['id'])

                            ffmpeg_process.close
                        elif (i == 3):
                            pass

                    logging.debug("Done Waiting.")

                except subprocess.CalledProcessError as e:
                    logging.exception("Job {}: Pass {} FAILED for {}".format(self.jobreq['id'],_pass,
                        os.path.basename(dirname)))
                    logging.error("{}:{}".format(e.returncode, e.output))
                    self._update_status("Error", self.jobreq['id'])
                    return
            except:
                logging.exception("Job {} - Debug 4 failed".format(self.jobreq['id']));
                self._update_status("Error", self.jobreq['id'])
                return

        # Apply MP4 Box if applicable
        try:
            if args['apply_mp4box']:
                logging.debug("Applying MP4Box to {}".format(os.path.basename(dirname)))
                cmd = subprocess.Popen(shlex.split("MP4Box -inter 500 \"{}\"".format(args['_TempDest'])), cwd=dirname)

                cmd.wait()

                if cmd.returncode != 0:
                    logging.exception("Job {}: MP4Box-ing failed for \"{}\"".format(self.jobreq['id'],os.path.basename(dirname)))
                    self._update_status("Error", self.jobreq['id'])
                    return
        except:
            logging.exception("Job {} - Debug 5 failed".format(self.jobreq['id']));
            self._update_status("Error", self.jobreq['id'])
            return



        # Copy file to intended destination
        self._update_status("Moving File", self.jobreq['id'])
        try:
            logging.debug("Moving to: {}".format(self.jobreq['destination_file']))
            if not os.path.exists(os.path.dirname(self.jobreq['destination_file'])):
                logging.debug("Directory does not exist: {}. Creating it now.".format(
                    os.path.dirname(self.jobreq['destination_file'])))
                try:
                    os.makedirs(os.path.dirname(self.jobreq['destination_file']))
                except OSError:
                    logging.exception("Job {}: Failed to create destination directory {}".format(self.jobreq['id'],
                        os.path.dirname(self.jobreq['destination_file'])))
                    self._update_status("Error", self.jobreq['id'])
                    return

            #shutil.copyfile(args['_TempDest'], self.jobreq['destination_file'])
            self._copyfile(args['_TempDest'], self.jobreq['destination_file'], 'Copying Output')
            self._update_status("Done", self.jobreq['id'])

            try:
                # Enable the video for watch on-demand
                self.dbcur.execute("UPDATE video_files SET is_enabled = True, size = {} WHERE id = {}".format(
                    os.path.getsize(args['_TempDest']), self.jobreq['video_id']))
                self.dbconn.commit()
            except:
                logging.exception("Job {}: Unable to update video file status".format(self.jobreq['id']))

        except:
            logging.exception("Job {}: Failed to copy {} to {}".format(
                self.jobreq['id'],os.path.basename(self.jobreq['source_file']), self.jobreq['destination_file']
                ))
            self._update_status("Error", self.jobreq['id'])
            return

        # Remove the working directory
        try:
            shutil.rmtree(os.path.dirname(args['_TempDest']))
        except OSError:
            self._update_status("Encoded", self.jobreq['id'])
            logging.exception("Job {}: Failed to remove directory: {}".format(self.jobreq['id'],os.path.dirname(args['_TempDest'])));

        del self.dbcur
        del self.dbconn

        logging.debug("Job {} ({}) done!".format(self.jobreq['id'],os.path.basename(args['_TempDest'])))
