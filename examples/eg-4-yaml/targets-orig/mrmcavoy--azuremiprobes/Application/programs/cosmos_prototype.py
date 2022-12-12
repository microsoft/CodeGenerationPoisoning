
# install via ~/Library/miniconda3/envs/mirage/bin/pip install azure-cosmos
from azure.cosmos import CosmosClient, PartitionKey, exceptions

import os
import yaml # conda install pyyaml
import json
import pandas as pd


class CosmosDB(object):

    def __init__(self, path=''):

        # get yaml credentials
        with open("Application/programs/user.yaml", 'r') as stream:
            credentials = yaml.safe_load(stream)
        
        # connect to client, db, and container
        self.client = CosmosClient(credentials['cosmos']['endpoint'], credentials['cosmos']['key'])
        self.dbname, self.crname = 'cosmosDB', 'machineCR'
        self.partition_key = PartitionKey(path=credentials['cosmos']['partition_key']),
        self.db = self.client.create_database_if_not_exists(id=self.dbname)
        self.cr = self.db.create_container_if_not_exists(id=self.crname,
                                                         partition_key=self.partition_key,
                                                         offer_throughput=400
        )
        self.fname = os.path.basename(path)
        self.machineid = 'machineA'
        self.query = ''

    def update_query(self, query):
        # add exception cases and tests here for proper querys
        self.query = query
        
    def query_func(self):
        
        print("Cosmos DB query: {}".format(self.query))
        items = list(self.cr.query_items(
            query=self.query,
            enable_cross_partition_query=True
        ))
        items = [ pd.DataFrame(item) for item in items ]
        df = pd.concat(items)

        df = df.reset_index()
        df = df.rename(columns={ 'index': 'wells', 'wells': 'values' })

        # hack to get leading zero in wells
        df['wells'] = df['wells'].apply(lambda x: x[0] + '0' + x[1] if len(x) == 2 else x)

        
        print(df.head(), "\n", df.tail())

        return df
    

    def upsert(self, doc):
        # read in data, add an id field [cosmos requirement]
        #self.fname = os.path.basename(path)
        print("upserting doc:", doc)
        fname = doc['id']
        
        # upsert into cosmos db
        response = self.cr.upsert_item(body=doc)
        '''
        # re-query db for upserted items based on fname in path
        self.query = "SELECT * FROM c WHERE c.machineid IN ('{}')".format(doc['machineid'])
        df = self.query_func()
        return df
        '''
        return response

    def delete(self, doc_id):
        response = self.cr.delete_item(item=doc_id,
                                       enable_cross_partition_query=True,
                                       partition_key=self.machineid)
        return response

    def read(self, doc_id):
        response = self.cr.read_item(item=doc_id,
                                       enable_cross_partition_query=True,
                                       partition_key=self.machineid)
        return response
        
    
if __name__ == '__main__':

    cosmos_conn = CosmosDB()
    cosmos_conn.machineid = 'machineA'
    path = 'Application/programs/sample_data/Magellan Sheet 5.csv'
    doc_id = 'barcode ' + os.path.basename(path)
    
    print("item: {}  partition key: {}".format(doc_id, cosmos_conn.machineid))
    print(" ******************************************************** ")
    
    #response = cosmos_conn.upsert(path)
    #response = cosmos_conn.delete(doc_id)
    cosmos_conn.query = "SELECT * FROM c"
    response = cosmos_conn.query_func()
    print("response from operation: {}".format(response))

    





