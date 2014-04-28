import threading, psycopg2, Queue
import os.path, shlex, shutil, logging, time, subprocess, re
from datetime import datetime
from string import maketrans
from config import Config

class FFmpegJob (threading.Thread):
	"""Encode job handler

	Run an individual encode job - assemble an ffmpeg command from the 
	database and run it

	"""

	THREADPOOL = None

	FormatString = """
	ffmpeg -i \"%(_SourceFile)s\" -passlogfile \"%(_PassLogFile)s\"
	%(args_beginning)s -vcodec %(video_codec)s -b:v %(video_bitrate)s
	%(_VPre)s -pass %(_Pass)s -s %(video_resolution)s -aspect %(aspect_ratio)s
	%(args_video)s -acodec %(audio_codec)s -ar %(audio_samplerate)s
	-ab %(audio_bitrate)s %(args_audio)s -threads 0 %(args_end)s -f %(container)s
	-y \"%(_TempDest)s\"
	""".translate(maketrans("\n\t\r", "\x20"*3))
	
	
	def _update_status(self, status, id):
		"""Wrapper to change the DB status of a job """
		try:
			self.dbcur.execute("UPDATE encode_jobs SET status=%s WHERE id = %s", (status,id))
			self.dbconn.commit()
		except:
			logging.exception("Job %s: Failed to update status in DB", (id))
		
	def run(self):
		while True:
			self.jobreq = FFmpegJob.THREADPOOL.get()

			if self.jobreq != None: 
				try:
					self.run_impl()
				except:
					logging.exception("An unhandled exception occured. The thread has been 'reset'")
			else: time.sleep(3)

	def run_impl(self):
	
		print "run_impl"
			
		# Check whether source file exists
		try:
			with open(self.jobreq['source_file']): pass
		except IOError:
			logging.exception("Job %s: Unable to open source file", (self.jobreq['id']))
			
		# Create temp dir for this job
		try:
			dirname = os.path.join(Config['tmpfolder'], "%s--encode--%s" % (
				os.path.basename(self.jobreq['source_file']), str(datetime.now()).replace(' ', '-')
			))
		except:
			logging.debug("Job %s - Debug 1 failed", (self.jobreq['id']));
		
		try:
			os.mkdir(dirname, 0775)
		except:
			logging.debug("Job %s - Failed to create temporary directory", (self.jobreq['id']))
		
		try:
			destleaf = os.path.basename(self.jobreq['destination_file'])
			srcleaf = "%s-source%s" % os.path.splitext(destleaf)
			srcpath = os.path.join(dirname, srcleaf)
		except:
			logging.exception("Job %s - Debug 2 failed", (self.jobreq['id']));
		
		# Create database connection
		try:
			self.dbconn = psycopg2.connect(**Config['database'])
			self.dbcur  = self.dbconn.cursor()
		except:
			logging.exception("Job %s: Could not connect to database",(self.jobreq['id']))
		
		# Get job settings from database
		try:
			cols = ('container', 'video_bitrate', 'video_bitrate_tolerance','video_codec',
			        'video_resolution', 'audio_bitrate', 'audio_samplerate','audio_codec',
			        'vpre_string', 'preset_string', 'aspect_ratio', 'args_beginning', 'args_video',
			        'args_audio', 'args_end', 'apply_mp4box', 'normalise_level')
			self.dbcur.execute("SELECT %s FROM encode_formats WHERE id = %s" % 
				(", ".join(cols), self.jobreq['format_id']) )
		
			fetched = [x if x is not None else '' for x in self.dbcur.fetchone()]
			args = dict(zip(cols, fetched))
			
			# Process the special ones (the /^_[A-Z]/ ones)
			args['_SourceFile'] = srcpath
			args['_PassLogFile'] = os.path.join(dirname, "pass.log")
	
			args['_VPre'] = args['preset_string']
			args['_TempDest'] = os.path.join(dirname, os.path.basename(self.jobreq['destination_file']))
		except:
			logging.exception("Job %s - Debug 3 failed", (self.jobreq['id']));
		
		# Copy to local folder, rename source
		try:
			shutil.copyfile(self.jobreq['source_file'], srcpath)
		except:
			logging.exception("Job %s: couldn't copy from %s to %s" % (
				self.jobreq['id'],self.jobreq['source_file'], dirname
			))
			self._update_status("Error", self.jobreq['id'])
			return
		
		# Analyse video for normalisation if requested
		if args['normalise_level'] is not '':
			try:
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
				logging.exception("Job %s: Failed normalising volume" % (self.jobreq['id']))
				self._update_status("Error", self.jobreq['id'])
				return

		# Run encode job		
		try:
			self.dbcur.execute("UPDATE encode_jobs SET working_directory=%s WHERE id=%s", 
				(dirname, self.jobreq['id'])
			) ; self.dbconn.commit()
		except:
			logging.exception("Job %s: Failed to update database", (self.jobreq['id']))

		for _pass in (1, 2):
			try:
				logging.debug("Updating Status.")
				self._update_status("Encoding Pass %d" % _pass, self.jobreq['id'])
				
				logging.debug("Setting args.")
				args['_Pass'] = _pass
				
				print "ARGS: %s" % args
				
				print FFmpegJob.FormatString % args 
				
				
				logging.debug("Opening subprocess: %s" % (FFmpegJob.FormatString % args))
				cmd = subprocess.Popen(shlex.split(FFmpegJob.FormatString % args), cwd=dirname)
				
				logging.debug("Waiting...")
				cmd.wait() # Magic!
				logging.debug("Done Waiting.")
				
				if cmd.returncode != 0:
					logging.exception("Job %s: Pass %d FAILED for %s" % (self.jobreq['id'],_pass, 
						os.path.basename(dirname)))
					self._update_status("Error", self.jobreq['id'])
					return
			except:
				logging.exception("Job %s - Debug 4 failed", (self.jobreq['id']));
				
		# Apply MP4 Box if applicable	
		try:
			if args['apply_mp4box']:
				logging.debug("Applying MP4Box to %s" % (os.path.basename(dirname)))
				cmd = subprocess.Popen(shlex.split("MP4Box -inter 500 \"%s\"" % args['_TempDest']), cwd=dirname)
				
				cmd.wait()
				
				if cmd.returncode != 0:
					logging.exception("Job %s: MP4Box-ing failed for \"%s\"" % (self.jobreq['id'],os.path.basename(dirname)))
					self._update_status("Error", self.jobreq['id'])
					return	
		except:
			logging.exception("Job %s - Debug 5 failed", (self.jobreq['id']));
				
				
			
		# Copy file to intended destination
		self._update_status("Moving File", self.jobreq['id'])
		try:
			logging.debug("Moving to: %s", (self.jobreq['destination_file']))
			if not os.path.exists(os.path.dirname(self.jobreq['destination_file'])):
				logging.debug("Directory does not exist: %s. Creating it now.", 
					os.path.dirname(self.jobreq['destination_file']))
				try:
					os.makedirs(os.path.dirname(self.jobreq['destination_file']))
				except OSError:
					logging.exception("Job %s: Failed to create destination directory %s" % (self.jobreq['id'],
						os.path.dirname(self.jobreq['destination_file'])))
					self._update_status("Error", self.jobreq['id'])
					return

			shutil.copyfile(args['_TempDest'], self.jobreq['destination_file'])
			self._update_status("Done", self.jobreq['id'])
			
			try:
				# Enable the video for watch on-demand
				self.dbcur.execute("UPDATE video_files SET is_enabled = True, size = %s WHERE id = %s", 
					(os.path.getsize(args['_TempDest']), self.jobreq['video_id']))
				print self.dbcur.query
				self.dbconn.commit()
			except:
				logging.debug("Job %s: Unable to update video file status",(self.jobreq['id']))

		except IOError:
			logging.exception("Job %s: Failed to copy %s to %s" % (
				self.jobreq['id'],os.path.basename(self.jobreq['source_file']), destleaf
			))
			self._update_status("Error", self.jobreq['id'])
		
		# Remove the working directory
		try:
			shutil.rmtree(os.path.dirname(args['_TempDest']))
		except OSError:
			self._update_status("Encoded", self.jobreq['id'])
			logging.exception("Job %s: Failed to remove directory: %s" %  (self.jobreq['id'],os.path.dirname(args['_TempDest'])));

		del self.dbcur
		del self.dbconn
		
		logging.debug("Job %s (%s) done!" % (self.jobreq['id'],os.path.basename(args['_TempDest'])))
