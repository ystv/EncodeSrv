"""Define the main EncodeSrv class, cause that's the whole purpose of this package."""


import psycopg2
import time
import os.path
import datetime
from dateutil import relativedelta


# Logging
from encodesrv import logs
from encodesrv.logs import log
from encodesrv.logs.messages import Message_enum

# Other Encodesrv modules
from encodesrv.job import FFmpegJob, THREADPOOL
from encodesrv.daemon import Daemon

# And config stuff
from encodesrv.config import Config


class EncodeSrv(object):
    
    """Actual encodesrv daemon. Jobs and things launched from here
    
    Methods:
        get_current_jobs: Return the names for all the jobs running.
        run: Thing that does the actual running.
    """
    
    def __init__(self):
        self.run()
    
    def get_current_jobs(self):
        
        """Get a list of nice names for all the jobs currently running.
        
        Arguments:
            None.
            
        Returns:
            Running jobs (list of strings).
        """
        
        encoding = []
        for thread in self.thread_list:
            if thread.get_job_name() is not None:
                encoding.append(thread.get_job_name())
        
        return encoding
    
    def run(self):

        """Thing that does the actual running.
        
        Arguments:
            None.
            
        Returns:
            None.
        """
        
        # Set up logging
        log.setup_logging(self)
        self.logger = logs.get_logger(__name__)

        self.thread_list = []
        
        self.logger.info(Message_enum.start_server)
    
        # Reset all crashed jobs
        try:
            self.logger.debug('Restarting crashed jobs')
            dbconn = psycopg2.connect(**Config["database"])
            cur = dbconn.cursor()
            cur.execute("UPDATE encode_jobs SET status='Not Encoding' WHERE status LIKE '%{}%' AND status NOT LIKE '%Error%'".format(Config["servername"]))
            dbconn.commit()
            cur.close()
            dbconn.close()
        except:
            self.logger.exception("Failed to connect to database on start, oops")
            raise

        # Spawn off threads to handle the jobs.
        self.logger.info("Spawning Threads", bot = False)
        for x in range(Config['threads']):
            self.logger.debug("spawning thread {}".format(x))
            self.thread_list.append(FFmpegJob().start())

        columns = ["id", "source_file", "destination_file", "format_id", "status", "video_id"]

        last_success = datetime.datetime.now()

        # Now we need to get some data.
        while True:
            try:
                # Connect to the db
                conn = psycopg2.connect(**Config["database"])
                cur = conn.cursor()
                # Search the DB for jobs not being encoded
                query = "SELECT {} FROM encode_jobs WHERE status = 'Not Encoding' ORDER BY priority DESC LIMIT {}".format(", ".join(columns), 1-THREADPOOL.qsize())
                cur.execute(query)
                jobs = cur.fetchall()
                for j in jobs:
                    data = dict(zip(columns, j))
                    for key in data:
                        if key in ["source_file", "destination_file"]:
                            data[key] = os.path.join(Config["mntfolder"] + data[key].lstrip("/"))
                    THREADPOOL.put(data)
                    cur.execute("UPDATE encode_jobs SET status = '{} - Waiting' WHERE id = {}".format(Config["servername"], data["id"]))
                    conn.commit()
                # Close communication with the database
                cur.close()
                conn.close()
                last_success = datetime.datetime.now()
                failure = False
            except:
                failure = True
                current_time = datetime.datetime.now()
                delta = relativedelta.relativedelta(current_time, last_success)
                if delta.days > 1:
                    self.logger.critical("CRITICAL: Failed to get jobs for more than 1 day, exiting with exception :(")
                    raise

                error_message = "ERROR: An unhandled exception occurred in the server whilst getting jobs."
                time_message = "Last success: {}, Now: {}, {}".format(last_success.isoformat(),
                                                                      current_time.isoformat(),
                                                                      delta)
                self.logger.exception("{} {}".format(error_message, time_message))
                self.logger.info("INFO: Sleeping for 5 minutes after failing")
                time.sleep(5 * 60)

            if not failure:
                # sleep after a run, only if the run was successful
                time.sleep(60)
                while THREADPOOL.qsize() > 0:
                    self.logger.debug("Going to sleep for a while")
                    # if the queue is still full, sleep a bit longer
                    time.sleep(60)
