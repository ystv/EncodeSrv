#!/usr/bin/python
import psycopg2, threading, Queue, time, sys, logging, logging.handlers
import os.path.join
from job import FFmpegJob

from config import Config
from daemon import Daemon

LOG_FILENAME= "/var/log/encodesrv"
LOG_FORMAT = '%(asctime)s:%(levelname)s:%(message)s'

def main():
	"""Main server loop.

	Sets up logging and database connection, gets job list
	"""
	# Setup a basic logging system to file	
	logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG, format=LOG_FORMAT)

	# Setup logging to email for critical failures
	mailhandler = logging.handlers.SMTPHandler(mailhost=Config["mail"]["host"],
							fromaddr=Config["mail"]["from"],
							toaddrs=Config["mail"]["to"],
							subject='Encode Job Failure')
	mailhandler.setLevel(logging.ERROR)
	logging.getLogger('').addHandler(mailhandler)

	logging.debug("Starting Up")

	# Setup a pool of threads to handle encode jobs.
	FFmpegJob.THREADPOOL = Queue.Queue(0)
	
	# Reset all crashed jobs
	try:
		dbconn = psycopg2.connect(**Config["database"])
		cur = dbconn.cursor()
		cur.execute("UPDATE encode_jobs SET status='Not Encoding' WHERE status !='Done' AND status != 'Error'")
		dbconn.commit()
		cur.close()
	 	dbconn.close()	
        except:
            	logging.exception("Failed to connect to database on start, oops")

		
	# Spawn off 2 threads to handle the jobs.	
	print "Spawning Threads"
	logging.debug("Spawning Threads")
	for x in xrange(2):
		print x
		logging.debug("spawning thread %s" % x)
		FFmpegJob().start()
		
	columns = ["id", "source_file", "destination_file", "format_id", "status", "video_id"]
	
	# Now we need to get some data.
	while True:
		try:
			# Connect to the db
			conn = psycopg2.connect(**Config["database"])
			cur = conn.cursor()
			# Search the DB for jobs not being encoded
			query = "SELECT %s FROM encode_jobs WHERE status = 'Not Encoding' ORDER BY priority DESC LIMIT "+str(6-FFmpegJob.THREADPOOL.qsize())
			cur.execute(query  % ", ".join(columns))
			jobs = cur.fetchall()
			for job in jobs:
				data = dict(zip(columns, job))
				for key in data:
					if key in ["sourcefile", "destination_file"}:
						data[key] = os.path.join(Config["mntfolder"] + data[key].lstrip("/"))
				FFmpegJob.THREADPOOL.put(data)

				cur.execute("UPDATE encode_jobs SET status = 'Waiting' WHERE id = %s", (data["id"],))
				conn.commit()
			# Close communication with the database
			cur.close()
			conn.close()
			#print "sleeping"
		except:
			logging.exception("ERROR: An unhandled exception occured in the server whilst getting jobs.")
		time.sleep(60) #sleep after a run
		while FFmpegJob.THREADPOOL.qsize() > 6:
    		    logging.debug("Going to sleep for a while")
		    time.sleep(60) #if the queue is still full, sleep a bit longer
		
	return

class EncodeSrvDaemon(Daemon):
	def run(self):
		main()

	
if __name__ == "__main__":
#	main()
	daemon = EncodeSrvDaemon('/tmp/encodesrv.pid')
	if len(sys.argv) == 2:
		if 'start' == sys.argv[1]:
			daemon.start()
		elif 'stop' == sys.argv[1]:
			daemon.stop()
		elif 'restart' == sys.argv[1]:
			daemon.restart()
		else:
			print "Unknown command"
			sys.exit(2)
		sys.exit(0)
	else:
		print "usage: %s start|stop|restart" % sys.argv[0]
		sys.exit(2)
