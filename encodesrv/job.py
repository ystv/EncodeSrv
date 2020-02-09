# Imports
import threading
import psycopg2
import queue
import os.path
import shlex
import shutil
import time
import subprocess
import re
from datetime import datetime
from .config import Config
from . import logs
from . import Message_enum

THREADPOOL = queue.Queue(0)

logger = logs.get_logger(__name__)

class FFmpegJob (threading.Thread):
    """Encode job handler

    Run an individual encode job - assemble an ffmpeg command from the
    database and run it

    """

    THREADPOOL = None

    ffmpegargs = [
	{"arg": "ffmpeg"},
        {"arg": "-i \"{_SourceFile}\"", "parm": "_SourceFile"},
        {"arg": "-passlogfile \"{_PassLogFile}\"", "parm": "_PassLogFile"},
        {"arg": "{args_beginning}", "parm": "args_beginning"},
        {"arg": "-vcodec {video_codec}", "parm": "video_codec"},
        {"arg": "-b:v {video_bitrate}", "parm": "video_bitrate"},
        {"arg": "{_VPre}", "parm": "_VPre"},
        {"arg": "-pass {_Pass}", "parm": "_Pass"},
        {"arg": "-s {video_resolution}", "parm": "video_resolution"},
        {"arg": "-aspect {aspect_ratio}", "parm": "aspect_ratio"},
        {"arg": "{args_video}", "parm": "args_video"},
        {"arg": "-acodec {audio_codec}", "parm": "audio_codec"},
        {"arg": "-ar {audio_samplerate}", "parm": "audio_samplerate"},
        {"arg": "-ab {audio_bitrate}", "parm": "audio_bitrate"},
        {"arg": "{args_audio}", "parm": "args_audio"},
        {"arg": "-threads 0"},
        {"arg": "{args_end}", "parm": "args_end"},
        {"arg": "-f {container}", "parm": "container"},
        {"arg": "-y"},
        {"arg": "\"{_TempDest}\"", "parm": "_TempDest"},
    ]

    def _get_video_size(self, args):
        if 'thumbs/' in self.jobreq['destination_file']:
            return sum([os.path.getsize(f) for f in os.listdir(args['_TempDest'].replace("/%05d.jpg","")) if os.path.isfile(f)])
        else:
            return os.path.getsize(args['_TempDest'])

    def _update_status(self, status, id_):
        """Wrapper to change the DB status of a job """
        try:
            logger.debug(f'Job {id_}: ' + status)
            self.dbcur.execute("UPDATE encode_jobs SET status=\'{}\' WHERE id = {}".format(status, id_))
            self.dbconn.commit()
        except:
            logger.exception(f"Job {id_}: Failed to update status in DB")

    def _copyfile(self, src, dst, desc):
        logger.debug(f'Job {self.jobreq["id"]}: (pv -ni 5 {src} > {dst}) 2>&1')
        p = subprocess.Popen(f'(pv -ni 5 {src} > {dst}) 2>&1', stdout=subprocess.PIPE, shell=True)

        while p.poll() != 0:
            line = p.stdout.readline().decode("utf-8")
            if line.strip() == '':
                continue
            if not line.rstrip().isdigit():
                raise Exception("Error during copy " + line)
            self._update_status(f"{Config['servername']} - {desc} {line.rstrip()}%", self.jobreq['id'])
    
    def _nice_name(self):
        """
        Gets a nice to look at name and format for the job"""
        
        self.dbcur.execute(f"SELECT format_name FROM encode_formats WHERE id = {self.jobreq['format_id']}")
        fetched = [x if x is not None else '' for x in self.dbcur.fetchone()]
        return os.path.basename(self.jobreq['source_file']) + ' (' + fetched[0] + ')'
    
    def get_job_name(self):
        
        """Get a nice name for current job.
        
        Arguments:
            None.
        
        Returns:
            Job name (string) or None.
        """
        
        try: 
            if self.dbcur:
                pass
        except AttributeError:
            return None
        return self._nice_name()

    def run(self):
        while True:
            self.jobreq = THREADPOOL.get()
            if self.jobreq != None:
                try:
                    self.run_impl()
                except:
                    logger.exception("An unhandled exception occured. The thread has been 'reset'")
            else:
                time.sleep(3)

    def run_impl(self):

        # Create database connection
        try:
            self.dbconn = psycopg2.connect(**Config['database'])
            self.dbcur  = self.dbconn.cursor()
        except:
            logger.exception(f"Job {self.jobreq['id']}: Could not connect to database")
            return
        
        logger.info(Message_enum.start_job, data = {"id_": self.jobreq['id'], 
                                                    "name": self._nice_name()
                                                    })

        # Check whether source file exists
        try:
            with open(self.jobreq['source_file']): pass
        except IOError:
            logger.exception(f"Job {self.jobreq['id']}: Unable to open source file")
            self._update_status(f"{Config['servername']} - Error", self.jobreq['id'])
            return

        # Create temp dir for this job
        try:
            dirname = os.path.join(Config['tmpfolder'], f"{os.path.basename(self.jobreq['source_file'])}--encode--{str(datetime.now()).replace(' ', '-')}")
            os.mkdir(dirname, 0o775)
        except:
            logger.exception(f"Job {self.jobreq['id']} - Failed to create temporary directory")
            self._update_status(f"{Config['servername']} - Error", self.jobreq['id'])
            return

        try:
            destleaf = self.jobreq['id']
            destleaf = os.path.splitext(os.path.basename(self.jobreq['source_file']))[1]
            srcleaf = f"{self.jobreq['id']}-source{destleaf}"
            srcpath = os.path.join(dirname, srcleaf)
        except:
            logger.exception(f"Job {self.jobreq['id']}: Debug 2 failed");
            self._update_status(f"{Config('servername')} - Error", self.jobreq['id'])
            return



        # Get job settings from database
        try:
            cols = ('container', 'video_bitrate', 'video_bitrate_tolerance','video_codec',
                    'video_resolution', 'audio_bitrate', 'audio_samplerate','audio_codec',
                    'vpre_string', 'preset_string', 'aspect_ratio', 'args_beginning', 'args_video',
                    'args_audio', 'args_end', 'apply_mp4box', 'normalise_level', 'pass')
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
            logger.exception(f"Job {self.jobreq['id']}: Debug 3 failed");
            self._update_status(f"{Config['servername']} - Error", self.jobreq['id'])
            return

        # Copy to local folder, rename source
        try:
            self._copyfile(self.jobreq['source_file'], srcpath, 'Copying Source')
        except:
            logger.exception(f"Job {self.jobreq['id']}: couldn't copy from {self.jobreq['source_file']} to {dirname}")
            self._update_status(f"{Config['servername']} - Error", self.jobreq['id'])
            return

        # Analyse video for normalisation if requested
        if args['normalise_level'] is not '':
            try:
                self._update_status(f"{Config['servername']} - Analysing audio", self.jobreq['id'])

                level = float(args['normalise_level'])
                analysis = subprocess.check_output(["ffmpeg", "-i", srcpath, "-af",
                    "ebur128", "-f", "null", "-y", "/dev/null"], stderr=subprocess.STDOUT)
                maxvolume = re.search(r"Integrated loudness:$\s* I:\s*(-?\d*.\d*) LUFS", analysis.decode("utf-8"),
                    flags=re.MULTILINE).group(1)

                # Calculate normalisation factor
                increase_factor = 10 ** ((level - float(maxvolume)) / 20)

                logger.debug('Job {}: Multiplying volume by {:.2f}'.format(self.jobreq['id'], increase_factor))
                args['args_audio'] += '-af volume={0}'.format(increase_factor)
            except:
                logger.exception(f"Job {self.jobreq['id']}: Failed normalising volume")
                self._update_status(f"{Config['servername']} - Error", self.jobreq['id'])
                return

        # Run encode job
        try:
            self.dbcur.execute("UPDATE encode_jobs SET working_directory=%s WHERE id=%s",(dirname, self.jobreq['id']))
            self.dbconn.commit()
        except:
            logger.exception(f"Job {self.jobreq['id']}: Failed to update database")
            self._update_status(f"{Config['servername']} - Error", self.jobreq['id'])
            return

        for _pass in range(1, args['pass'] + 1):
            try:
                logger.debug(f"Job {self.jobreq['id']}: Updating Status.")
                self._update_status(f"{Config['servername']} - Encoding Pass {_pass}", self.jobreq['id'])

                logger.debug(f"Job {self.jobreq['id']}: Setting args.")
                args['_Pass'] = _pass

                finalargs = []
                for arg in FFmpegJob.ffmpegargs:
                    if 'parm' in arg:
                        if arg['parm'] in args and args[arg['parm']]:
                            format_ = arg['arg'].translate(''.maketrans("\n\t\r", "\x20"*3))
                            finalargs.append(format_.format(**args))
                    else:
                        finalargs.append(arg['arg'])
                        
                FormatString = ' '.join(finalargs)

                logger.debug(f"Job {self.jobreq['id']}: Opening subprocess: {FormatString}")
                try:
                    cmd = subprocess.check_output(shlex.split(FormatString), cwd=dirname)

                    logger.debug(f"Job {self.jobreq['id']}: Done Waiting.")

                except subprocess.CalledProcessError as e:
                    logger.exception(f"Job {self.jobreq['id']}: Pass {_pass} FAILED for {os.path.basename(dirname)}")
                    logger.error(f"{e.returncode}:{e.output}")
                    self._update_status(f"{Config['servername']} - Error", self.jobreq['id'])
                    return
            except:
                logger.exception(f"Job {self.jobreq['id']}: Debug 4 failed")
                self._update_status(f"{Config['servername']} - Error", self.jobreq['id'])
                return

        # Apply MP4 Box if applicable
        try:
            if args['apply_mp4box']:
                logger.debug(f"Job {self.jobreq['id']}: Applying MP4Box to {os.path.basename(dirname)}")
                cmd = subprocess.Popen(shlex.split(f"MP4Box -inter 500 \"{args['_TempDest']}\""), cwd=dirname)

                cmd.wait()

                if cmd.returncode != 0:
                    logger.exception(f"Job {self.jobreq['id']}: MP4Box-ing failed for \"{s.path.basename(dirname)}\"")
                    self._update_status(f"{Config'servername']} - Error", self.jobreq['id'])
                    return
        except:
            logger.exception(f"Job {self.jobreq['id']}: Debug 5 failed")
            self._update_status(f"{Config['servername']} - Error", self.jobreq['id'])
            return



        # Copy file to intended destination
        self._update_status(f"{Config['servername']} - Moving File", self.jobreq['id'])
        try:
            logger.debug(f"Job {self.jobreq['id']}: Moving to {self.jobreq['destination_file']}")
            if not os.path.exists(os.path.dirname(self.jobreq['destination_file'])):
                logger.debug(f"Job {self.jobreq['id']}: Directory does not exist: {os.path.dirname(self.jobreq['destination_file'])}. Creating it now.")
                try:
                    os.makedirs(os.path.dirname(self.jobreq['destination_file']))
                except OSError:
                    logger.exception(f"Job {self.jobreq['id']}: Failed to create destination directory {os.path.dirname(self.jobreq['destination_file'])}")
                    self._update_status(f"{Config['servername']} - Error", self.jobreq['id'])
                    return

            p = re.compile('%([0-9]+)d')
            if p.search(args['_TempDest']):
                dest = os.path.split(re.sub('%([0-9]+)d', '\d+', args['_TempDest']))
                files = [f for f in os.listdir(dest[0]) if re.match(dest[1], f)]
                i = 0
                for f in files:
                    self._update_status(f"{Config['servername']} - Moving files {(i * 100) / len(files)}%", self.jobreq['id'])
                    i += 1
                    shutil.copyfile(os.path.join(dest[0], f), os.path.join(os.path.dirname(self.jobreq['destination_file']), f))
            else:
                self._copyfile(args['_TempDest'], self.jobreq['destination_file'], 'Copying Output')
            self._update_status("Done", self.jobreq['id'])

            if self.jobreq['video_id']:
                try:
                    # Enable the video for watch on-demand
                    self.dbcur.execute(f"UPDATE video_files SET is_enabled = True, size = {self._get_video_size(args)} WHERE id = {self.jobreq['video_id']}")
                    self.dbconn.commit()
                except:
                    logger.exception(f"Job {self.jobreq['id']}: Unable to update video file status")

        except:
            logger.exception(f"Job {self.jobreq['id']}: Failed to copy {os.path.basename(self.jobreq['source_file'])} to {self.jobreq['destination_file']}")
            self._update_status(f"{Config['servername']} - Error", self.jobreq['id'])
            return

        # Remove the working directory
        try:
            shutil.rmtree(os.path.dirname(args['_TempDest']))
        except OSError:
            self._update_status("Encoded", self.jobreq['id'])
            logger.exception(f"Job {self.jobreq['id']}: Failed to remove directory: {os.path.dirname(args['_TempDest'])}")

        logger.info(Message_enum.finish_job, data = {"id_": self.jobreq['id'], 
                                                    "name": self._nice_name()
                                                    })
        
        del self.dbcur
        del self.dbconn
        
    def start(self):
        super(FFmpegJob, self).start()
        return self
