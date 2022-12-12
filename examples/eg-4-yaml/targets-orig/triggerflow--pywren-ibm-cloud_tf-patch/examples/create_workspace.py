from triggerflow import Triggerflow
from triggerflow.eventsources import RedisEventSource
import yaml

if __name__ == "__main__":
    with open('lithops_config.yaml', 'r') as config_file:
        tf_config = yaml.safe_load(config_file)

    tf = Triggerflow(endpoint=tf_config['triggerflow']['endpoint'],
                     user=tf_config['triggerflow']['user'],
                     password=tf_config['triggerflow']['password'],
                     workspace=tf_config['triggerflow']['workspace'])

    try:
        tf.delete_workspace()
    except Exception as e:
        print(e)

    es = RedisEventSource(**tf_config['redis'])
    tf.create_workspace(workspace_name=tf_config['triggerflow']['workspace'], event_source=es)
