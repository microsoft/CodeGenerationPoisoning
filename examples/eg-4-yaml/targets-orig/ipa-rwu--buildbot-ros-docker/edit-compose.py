#!/usr/bin/env python
import yaml, sys

# create docker container based on Dockerfile_unique(Dockerfile_test)
#from testbuild_docker import call

# create docker-compose file
def edit_docker_compose(composefile, SINGING_KEY):
    # 'docker-compose-deb.yaml'
    with open(composefile) as f:
        doc = yaml.safe_load(f)
    #doc['services']['scalable-test']['build']['dockerfile'] = 'Dockerfile_unique'
    doc['services']['scalable']['build']['args']['SINGING_KEY']= SINGING_KEY
    #doc['services']['scalable-debian']['build']['args']['LOCAL_RESPOSITORY']=LOCAL_RESPOSITORY
    with open(composefile, 'w+') as f:
        yaml.safe_dump(doc, f)



if __name__=="__main__":
    if len(sys.argv) < 2:
        print('')
        print('Usage: unique_docker_compose.py <composefile> <package>')
        print('')
        exit(-1)
    composefile = sys.argv[1]
    SINGING_KEY = sys.argv[2]
    edit_docker_compose(composefile, SINGING_KEY)