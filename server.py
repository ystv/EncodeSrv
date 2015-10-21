#!/usr/bin/python

# All the imports
import psycopg2
import time
import sys
import os.path

# self.logger
import log

# Other Encodesrv modules
from job import FFmpegJob, THREADPOOL
from daemon import Daemon

# And config stuff
from config import Config
    

class EncodeSrvDaemon(Daemon):
    
    """Actual encodesrv daemon. Jobs and things launched from here
    
    Methods:
        run: Thing that does the actual running.
    """
    
    def get_current_jobs(self):
        
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
        self.logger = log.setup_logging(self)
        
        self.logger.info("Starting Up")
    
        # Reset all crashed jobs
        try:
            self.logger.debug('Restarting crashed jobs')
            dbconn = psycopg2.connect(**Config["database"])
            cur = dbconn.cursor()
            cur.execute("UPDATE encode_jobs SET status='Not Encoding' WHERE status !='Done' AND status != 'Error'")
            dbconn.commit()
            cur.close()
            dbconn.close()
        except:
            self.logger.exception("Failed to connect to database on start, oops")
            raise
    
        self.thread_list = []
        # Spawn off threads to handle the jobs.
        self.logger.info("Spawning Threads")
        for x in range(Config['threads']):
            self.logger.debug("spawning thread {}".format(x))
            self.thread_list.append(FFmpegJob().start())
            
    
        columns = ["id", "source_file", "destination_file", "format_id", "status", "video_id"]
    
        # Now we need to get some data.
        while True:
            try:
                # Connect to the db
                conn = psycopg2.connect(**Config["database"])
                cur = conn.cursor()
                # Search the DB for jobs not being encoded
                query = "SELECT {} FROM encode_jobs WHERE status = 'Not Encoding' ORDER BY priority DESC LIMIT {}".format(", ".join(columns), 6-THREADPOOL.qsize())
                cur.execute(query)
                jobs = cur.fetchall()
                for job in jobs:
                    data = dict(zip(columns, job))
                    for key in data:
                        if key in ["source_file", "destination_file"]:
                            data[key] = os.path.join(Config["mntfolder"] + data[key].lstrip("/"))
                    THREADPOOL.put(data)
    
                    cur.execute("UPDATE encode_jobs SET status = 'Waiting' WHERE id = {}".format(data["id"]))
                    conn.commit()
                # Close communication with the database
                cur.close()
                conn.close()
            except:
                self.logger.exception("ERROR: An unhandled exception occured in the server whilst getting jobs.")
                raise
            time.sleep(60) #sleep after a run
            while THREADPOOL.qsize() > 6:
                self.logger.debug("Going to sleep for a while")
                time.sleep(60) #if the queue is still full, sleep a bit longer
        return


if __name__ == "__main__":
    daemon = EncodeSrvDaemon('/tmp/encodesrv.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print("Unknown command")
            sys.exit(2)
        sys.exit(0)
    else:
        print("usage: {} start|stop|restart".format(sys.argv[0]))
        sys.exit(2)
