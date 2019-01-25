import enum

class Message_enum(enum.Enum):
    
    status = 1
    unknown_cmd = 2
    start_job = 3
    finish_job = 4
    start_server = 5
    

message_dict = {
                Message_enum.status: "Currently encoding {enc_jobs}, with {wait_jobs} item{pl} waiting.",
                Message_enum.unknown_cmd: "I don't know what you're asking.",
                Message_enum.start_job: "Starting job {id_}: {name}.",
                Message_enum.finish_job: "Finished job {id_}: {name}.",
                Message_enum.start_server: "Starting up Encodesrv."
                }
