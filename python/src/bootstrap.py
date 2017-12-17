print 'loading protobuf'
import protobuf
import androidbridge

androidbridge.log('running bootstrap')

def run():
    while 1:
        job = androidbridge.get_job()
        if job:
            response = protobuf.handle_request_blob(job)
            androidbridge.process_result(response)

run()
