#!/usr/bin/python

# All the imports
import psycopg2
import time
import sys
import os.path

# Logging
import logging.handlers
import slack

# Other Encodesrv modules
from job import FFmpegJob, THREADPOOL
from daemon import Daemon

# And config stuff
from config import Config


# Logging constants
LOG_FILENAME= "encodesrv.log"
LOG_FORMAT = '%(asctime)s:%(levelname)s:%(message)s'

def main():
    """Main server loop.

    Sets up logging and database connection, gets job list
    """
    # Setup a basic logging system to file
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)

    # Setup logging to email for critical failures
    mailhandler = logging.handlers.SMTPHandler(mailhost=Config["mail"]["host"],
                            fromaddr=Config["mail"]["from"],
                            toaddrs=Config["mail"]["to"],
                            subject='Encode Job Failure')
    mailhandler.setLevel(logging.ERROR)
    ##logging.getLogger('').addHandler(mailhandler)
    
    if Config['slack']['enabled']:
        slackhandler = slack.Encode_slack(**Config['slack'])
        slackhandler.setLevel(logging.INFO)
        logging.getLogger().addHandler(slackhandler)



    logging.info("Starting Up")

    # Reset all crashed jobs
    try:
        logging.debug('Restarting crashed jobs')
        dbconn = psycopg2.connect(**Config["database"])
        cur = dbconn.cursor()
        cur.execute("UPDATE encode_jobs SET status='Not Encoding' WHERE status !='Done' AND status != 'Error'")
        dbconn.commit()
        cur.close()
        dbconn.close()
    except:
        logging.exception("Failed to connect to database on start, oops")
        raise

    # Spawn off 3 threads to handle the jobs.
    logging.info("Spawning Threads")
    for x in range(3):
        logging.debug("spawning thread {}".format(x))
        FFmpegJob().start()

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
            logging.exception("ERROR: An unhandled exception occured in the server whilst getting jobs.")
            raise
        time.sleep(60) #sleep after a run
        while THREADPOOL.qsize() > 6:
            logging.debug("Going to sleep for a while")
            time.sleep(60) #if the queue is still full, sleep a bit longer
    return

class EncodeSrvDaemon(Daemon):
    def run(self):
        main()


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
