import protobuf
import androidbridge

def run():
    while androidbridge.is_running():
        job = androidbridge.get_job()
        if job:
            response = protobuf.handle_request_blob(job)
            androidbridge.process_result(response)
