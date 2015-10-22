# Imports
import threading
import psycopg2
import queue
import os.path
import shlex
import shutil
import logging
import time
import subprocess
import re
from datetime import datetime
from .config import Config

THREADPOOL = queue.Queue(0)

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
            logging.debug('Job {}: '.format(id_) + status)
            self.dbcur.execute("UPDATE encode_jobs SET status=\'{}\' WHERE id = {}".format(status, id_))
            self.dbconn.commit()
        except:
            logging.exception("Job {}: Failed to update status in DB".format(id_))

    def _copyfile(self, src, dst, desc):
        logging.debug('Job {}: (pv -ni 5 "{}" > "{}") 2>&1'.format(self.jobreq['id'], src, dst))
        p = subprocess.Popen('(pv -ni 5 "{}" > "{}") 2>&1'.format(src, dst), stdout=subprocess.PIPE, shell=True)

        while p.poll() != 0:
            line = p.stdout.readline().decode("utf-8")
            if line.strip() == '':
                continue
            if not line.rstrip().isdigit():
                raise Exception("Error during copy " + line)
            self._update_status("{} {}%".format(desc, line.rstrip()), self.jobreq['id'])
    
    def _nice_name(self):
        """
        Gets a nice to look at name and format for the job"""
        
        self.dbcur.execute("SELECT format_name FROM encode_formats WHERE id = {}".format(self.jobreq['format_id']) )
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
                    logging.exception("An unhandled exception occured. The thread has been 'reset'")
            else:
                time.sleep(3)

    def run_impl(self):

        # Create database connection
        try:
            self.dbconn = psycopg2.connect(**Config['database'])
            self.dbcur  = self.dbconn.cursor()
        except:
            logging.exception("Job {}: Could not connect to database".format(self.jobreq['id']))
            return
        
        logging.info('starting job {}, {}'.format(self.jobreq['id'], self._nice_name()))

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
            os.mkdir(dirname, 0o775)
        except:
            logging.exception("Job {} - Failed to create temporary directory".format(self.jobreq['id']))
            self._update_status("Error", self.jobreq['id'])
            return

        try:
            destleaf = self.jobreq['id']
            destleaf = os.path.splitext(os.path.basename(self.jobreq['source_file']))[1]
            srcleaf = "{}-source{}".format(self.jobreq['id'], destleaf)
            srcpath = os.path.join(dirname, srcleaf)
        except:
            logging.exception("Job {}: Debug 2 failed".format(self.jobreq['id']));
            self._update_status("Error", self.jobreq['id'])
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
            logging.exception("Job {}: Debug 3 failed".format(self.jobreq['id']));
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
                maxvolume = re.search(r"Integrated loudness:$\s* I:\s*(-?\d*.\d*) LUFS", analysis.decode("utf-8"),
                    flags=re.MULTILINE).group(1)

                # Calculate normalisation factor
                increase_factor = 10 ** ((level - float(maxvolume)) / 20)

                logging.debug('Job {}: Multiplying volume by {:.2f}'.format(self.jobreq['id'], increase_factor))
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

        for _pass in range(1, args['pass'] + 1):
            try:
                logging.debug("Job {}: Updating Status.".format(self.jobreq['id']))
                self._update_status("Encoding Pass {}".format(_pass), self.jobreq['id'])

                logging.debug("Job {}: Setting args.".format(self.jobreq['id']))
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

                logging.debug("Job {}: Opening subprocess: {}".format(self.jobreq['id'], FormatString))
                try:
                    cmd = subprocess.check_output(shlex.split(FormatString), cwd=dirname)

                    logging.debug("Job {}: Done Waiting.".format(self.jobreq['id']))

                except subprocess.CalledProcessError as e:
                    logging.exception("Job {}: Pass {} FAILED for {}".format(self.jobreq['id'],_pass,
                        os.path.basename(dirname)))
                    logging.error("{}:{}".format(e.returncode, e.output))
                    self._update_status("Error", self.jobreq['id'])
                    return
            except:
                logging.exception("Job {}: Debug 4 failed".format(self.jobreq['id']));
                self._update_status("Error", self.jobreq['id'])
                return

        # Apply MP4 Box if applicable
        try:
            if args['apply_mp4box']:
                logging.debug("Job {}: Applying MP4Box to {}".format(self.jobreq['id'], os.path.basename(dirname)))
                cmd = subprocess.Popen(shlex.split("MP4Box -inter 500 \"{}\"".format(args['_TempDest'])), cwd=dirname)

                cmd.wait()

                if cmd.returncode != 0:
                    logging.exception("Job {}: MP4Box-ing failed for \"{}\"".format(self.jobreq['id'],os.path.basename(dirname)))
                    self._update_status("Error", self.jobreq['id'])
                    return
        except:
            logging.exception("Job {}: Debug 5 failed".format(self.jobreq['id']));
            self._update_status("Error", self.jobreq['id'])
            return



        # Copy file to intended destination
        self._update_status("Moving File", self.jobreq['id'])
        try:
            logging.debug("Job {}: Moving to {}".format(self.jobreq['id'], self.jobreq['destination_file']))
            if not os.path.exists(os.path.dirname(self.jobreq['destination_file'])):
                logging.debug("Job {}: Directory does not exist: {}. Creating it now.".format(
                    self.jobreq['id'], os.path.dirname(self.jobreq['destination_file'])))
                try:
                    os.makedirs(os.path.dirname(self.jobreq['destination_file']))
                except OSError:
                    logging.exception("Job {}: Failed to create destination directory {}".format(self.jobreq['id'],
                        os.path.dirname(self.jobreq['destination_file'])))
                    self._update_status("Error", self.jobreq['id'])
                    return

            #shutil.copyfile(args['_TempDest'], self.jobreq['destination_file'])
            p = re.compile('%([0-9]+)d')
            if p.search(args['_TempDest']):
                dest = os.path.split(re.sub('%([0-9]+)d', '\d+', args['_TempDest']))
                files = [f for f in os.listdir(dest[0]) if re.match(dest[1], f)]
                i = 0
                for f in files:
                    self._update_status("Moving files {}%".format((i * 100) / len(files)), self.jobreq['id'])
                    i = i + 1
                    shutil.copyfile(os.path.join(dest[0], f), os.path.join(os.path.dirname(self.jobreq['destination_file']), f))
            else:
                self._copyfile(args['_TempDest'], self.jobreq['destination_file'], 'Copying Output')
            self._update_status("Done", self.jobreq['id'])

            if self.jobreq['video_id']:
                try:
                    # Enable the video for watch on-demand
                    self.dbcur.execute("UPDATE video_files SET is_enabled = True, size = {} WHERE id = {}".format(self._get_video_size(args), self.jobreq['video_id']))
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

        logging.info("Job {}: ({}) done!".format(self.jobreq['id'], self._nice_name()))
        
        del self.dbcur
        del self.dbconn
        
    def start(self):
        super(FFmpegJob, self).start()
        return self
