import os
import yaml
from datetime import datetime, timedelta
import pytz
from pprint import pprint
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.python_operator import BranchPythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from airflow.hooks.http_hook import HttpHook
from airflow.configuration import conf
from airflow.models import Variable
from airflow.utils.dates import days_ago

# Following are defaults which can be overridden later on
default_args = {
    'owner': 'hubmap',
    'depends_on_past': False,
    'start_date': datetime(2019, 1, 1),
    'email': ['joel.welling@gmail.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'provide_context': True,
    'xcom_push': True,
    'params': {
            'auth_tok': 'AgJEbW7KYQVDvpdWJ9vJWGDrYa0W0zp5vJ3e1vP3mz8ydzOjO6T0CBxzxEnKmJeOedyx58j44EDDM7U395N0Yf7KVD',
            'dag_id': 'test_scan_and_begin_processing_dag_id',
            'process': 'scan.and.begin.processing',
            'provider': 'IEC Testing Group',
            'execution_date': datetime.now(tz = pytz.timezone('America/New_York')).isoformat(),
            'lz_path': "/usr/local/airflow/lz/IEC Testing Group/80cd0a1fadbb654f023daf197d8a0bfe",
            'src_path': "/usr/src/app/src",
            #'submission_id': '43c6ad5c6b2471ca812ac8fa4029d63a', # original
            #'submission_id': '404cf7a1c0149e3cccbd7b50b09d28d3', # good Vanderbilt copy
            #'submission_id': '4f80da2501a9547fbbb6f2a1b9458633', # bad Vanderbilt copy
            'submission_id': '80cd0a1fadbb654f023daf197d8a0bfe',  # good Florida copy
        }
}

with DAG('test_scan_and_begin_processing', 
         schedule_interval=None, 
         is_paused_upon_creation=False, 
         default_args=default_args) as dag:


    def set_params(*argv, **kwargs):
        # In the real version these will be set from kwargs['dag_run'].conf dict
        run_id = kwargs['run_id']
        ingest_id = run_id
        dag_params = Variable.get("dag_params", deserialize_json=True)
        new_dag_params = kwargs['params'].copy()
        new_dag_params['run_id'] = run_id
        new_dag_params['ingest_id'] = ingest_id
        Variable.set("dag_params", new_dag_params, serialize_json=True)
        return 'Whatever you return gets printed in the logs'

 
    def test_params(*argv, **kwargs):
        run_id = kwargs['run_id']
        dag_params = Variable.get("dag_params", deserialize_json=True)
        print('dag_params:')
        pprint(dag_params)
        print('kwargs:')
        pprint(kwargs)
        return 'maybe this will make it run only once'

         
    def send_status_msg(**kwargs):
        md_extract_retcode = int(kwargs['ti'].xcom_pull(task_ids="run_md_extract"))
        print('md_extract_retcode: ', md_extract_retcode)
        http_conn_id='ingest_api_connection'
        endpoint='/datasets/status'
        method='PUT'
        headers={
            #'authorization' : 'Bearer ' + kwargs['params']['auth_tok'],
                 'content-type' : 'application/json'}
        extra_options=[]
         
        http = HttpHook(method,
                        http_conn_id=http_conn_id)
 
        if md_extract_retcode == 0:
            md_fname = os.path.join(os.environ['AIRFLOW_HOME'],
                                    'data/temp', kwargs['run_id'],
                                    'rslt.yml')
            with open(md_fname, 'r') as f:
                md = yaml.safe_load(f)
            data = {'dataset_id' : kwargs['dag_run'].conf['submission_id'],
                    'status' : 'QA',
                    'message' : 'the process ran',
                    'metadata': md}
            kwargs['ti'].xcom_push(key='collectiontype',
                                   value=(md['collectiontype'] if 'collectiontype' in md
                                          else None))
        else:
            log_fname = os.path.join(os.environ['AIRFLOW_HOME'],
                                     'data/temp', kwargs['run_id'],
                                     'session.log')
            with open(log_fname, 'r') as f:
                err_txt = '\n'.join(f.readlines())
            data = {'dataset_id' : kwargs['dag_run'].conf['submission_id'],
                    'status' : 'Invalid',
                    'message' : err_txt}
            kwargs['ti'].xcom_push(key='collectiontype', value=None)
        print('data: ', data)
         
        response = http.run(endpoint,
                            json.dumps(data),
                            headers,
                            extra_options)
        print('response: ', response.text)

    def maybe_spawn_dag(context, dag_run_obj):
        """
        This needs to be table-driven.  Its purpose is to suppress
        triggering the dependent DAG if the collectiontype doesn't
        have a dependent DAG.
        """
        print('context:')
        pprint(context)
        md_extract_retcode = int(context['ti'].xcom_pull(task_ids="run_md_extract"))
        collectiontype = context['ti'].xcom_pull(key='collectiontype',
                                                 task_ids='send_status_msg')
        if md_extract_retcode == 0 and collectiontype is not None:
            md_fname = os.path.join(os.environ['AIRFLOW_HOME'],
                                    'data/temp', context['run_id'],
                                    'rslt.yml')
            with open(md_fname, 'r') as f:
                md = yaml.safe_load(f)
            if collectiontype in ['rnaseq_10x']:
                payload = {'ingest_id' : context['run_id'],
                           #'ingest_id' : context['dag_run'].conf['ingest_id'],
                           'auth_tok' : context['params']['auth_tok'],
                           'parent_lz_path' : context['params']['lz_path'],
                           'parent_submission_id' : context['params']['submission_id'],
                           'metadata': md}
                dag_run_obj.payload = payload
                return dag_run_obj
            else:
                print('Extracted metadata has no "collectiontype" element')
                return None
        else:
            # The extraction of metadata failed or collectiontype is unknown,
            # so spawn no child runs
            return None


    def trigger_or_skip(**kwargs):
        collectiontype = kwargs['ti'].xcom_pull(key='collectiontype',
                                                task_ids="send_status_msg")
        if collectiontype is None:
            return 'no_spawn'
        else:
            return 'maybe_spawn_dag'
        


    t0 = PythonOperator(
        task_id='set_params',
        python_callable=set_params,
        provide_context=True
        )

 
    t1 = PythonOperator(
        task_id='test_params',
        python_callable=test_params,
        provide_context=True
        )


    t_create_tmpdir = BashOperator(
        task_id='create_temp_dir',
        bash_command='mkdir ${AIRFLOW_HOME}/data/temp/{{run_id}}',
        provide_context=True
        )

 
        #lz_dir="{{dag_run.conf.lz_path}}" ; \
        #src_dir="{{dag_run.conf.src_path}}/md" ; \         
    t_run_md_extract = BashOperator(
        task_id='run_md_extract',
        bash_command=""" \
        lz_dir="{{var.json.dag_params.lz_path}}" ; \
        src_dir="{{var.json.dag_params.src_path}}/md" ; \
        work_dir="${AIRFLOW_HOME}/data/temp/{{run_id}}" ; \
        cd $work_dir ; \
        python $src_dir/metadata_extract.py --out ./rslt.yml --yaml "$lz_dir" \
          > ./session.log 2>&1 ; \
        echo $?
        """,
        provide_context = True
        )

 
    t_send_status = PythonOperator(
        task_id='send_status_msg',
        python_callable=send_status_msg,
        provide_context=True
    )


    t_maybe_trigger = BranchPythonOperator(
        task_id='maybe_trigger',
        python_callable=trigger_or_skip,
        provide_context=True
        )

    t_join = DummyOperator(
        task_id='join',
        trigger_rule='one_success')

    t_no_spawn = DummyOperator(
        task_id='no_spawn')

    t_spawn_dag = TriggerDagRunOperator(
        task_id="maybe_spawn_dag",
        trigger_dag_id="trig_{{ti.xcom_pull(key='collectiontype', task_ids='send_status_msg')}}",
        python_callable = maybe_spawn_dag,
        #conf={"message": "Hello World"},
        #provide_context = True
        )
 

    t_cleanup_tmpdir = BashOperator(
        task_id='cleanup_temp_dir',
        bash_command='echo rm -r ${AIRFLOW_HOME}/data/temp/{{run_id}}',
        )
 
 
    (dag >> t0 >> t1 >> t_create_tmpdir >> t_run_md_extract >> t_send_status
     >> t_maybe_trigger)
    t_maybe_trigger >> t_spawn_dag >> t_join
    t_maybe_trigger >> t_no_spawn >> t_join
    t_join >> t_cleanup_tmpdir
