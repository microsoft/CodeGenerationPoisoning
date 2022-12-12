from queue import Queue
from Log.Logger import Logger
from Job.Job import JobFactory
import yaml

class Launcher:

    def __init__(self, path=None):
        if path is not None:
            self.meta_data = self.load_meta_data(path)
            self.job_que = self.make_job_queue()
        else:
            self.meta_data = None
        
        self.logger = Logger.get_instance().get_logger()
        self.logger.info('Launcher Created')

    def load_meta_data(self, PATH):
        with open(PATH) as yaml_file:
            return yaml.load(yaml_file)
            
    def make_job_queue(self):
        que = Queue()
        
        for meta_data in self.meta_data['job']:
            que.put(JobFactory.create_job(meta_data))

        return que

    def start(self):
        self.logger.info('Launcher Start')
        while True:
            if self.job_que.empty():
                self.logger.error('Job Que is empty')
                break

            job = self.job_que.get(False)

            try:
                job.do_job()
            except Exception:
                # TODO define do job exception for handling issue
                # TODO Logger may be used in this section
                # Send Mail to authorized users
                self.logger.critical("Job Fail")


if __name__ == "__main__":
    logger = Logger.get_instance().get_logger()
    
    logger.info("Create Logger")
    batch_launcher = Launcher("Batch/meta.yml")

    logger.info('Batch Start')
    batch_launcher.start()
