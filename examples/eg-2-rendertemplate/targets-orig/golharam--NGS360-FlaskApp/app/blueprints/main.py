'''
Main application endpoints
'''
from flask import Blueprint, render_template, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from app import project_registry, BASESPACE as base_space, DB as db
from app.models import Project, RunToSamples, SequencingRun, BatchJob

BP = Blueprint('main', __name__)

@BP.route('/')
@login_required
def index():
    '''
    Home Page URL: /
    '''
    return render_template('main/index.html')

@BP.route("/basespace")
@login_required
def show_basespace():
    ''' Show Basespace page '''
    return render_template('main/basespace.html')

@BP.route('/browseFiles')
@login_required
def browseFiles():
    return render_template("main/browseFiles.html", bucket=request.args.get('bucket'),
                                                    prefix=request.args.get('prefix'))

@BP.route("/jobs")
@login_required
def show_batch_jobs():
    ''' Show user jobs '''
    if 'username' in request.args:
        username = request.args.get('username')
    else:
        username = current_user.username
    return render_template('main/jobs.html', username=username)

@BP.route("/jobs/<jobid>/log")
@login_required
def show_job_log(jobid):
    job = BatchJob.query.filter_by(id=jobid).first()
    if current_user.username == job.user and job.viewed == False:
        job.viewed = True
        db.session.add(job)
        db.session.commit()
    return render_template('main/job_log.html', jobId=job.id, jobName=job.name, submittedOn=job.submitted_on,
                           logStreamName=job.log_stream_name, status=job.status)

@BP.route("/illumina_qc")
@login_required
def show_illumina_qc():
    return render_template('main/illumina_qc.html')

@BP.route("/illumina_runs")
@login_required
def show_illumina_runs():
    ''' Show Illumina Runs page '''
    return render_template('main/illumina_runs.html')

def find_bucket_key(s3path):
    """
    This is a helper function that given an s3 path such that the path is of
    the form: bucket/key
    It will return the bucket and the key represented by the s3 path, eg
    if s3path == s3://bmsrd-ngs-data/P-234
    """
    if s3path.startswith('s3://'):
        s3path = s3path[5:]
    s3components = s3path.split('/')
    bucket = s3components[0]
    s3key = ""
    if len(s3components) > 1:
        s3key = '/'.join(s3components[1:])
    return bucket, s3key

@BP.route("/illumina_run")
@login_required
def show_illumina_run():
    ''' Show an Illumina run '''
    runid = request.args.get('runid')
    if not runid:
        return "Run ID not specified", 404

    run = SequencingRun.query.get(runid)
    if run:
        bucket, key = find_bucket_key(run.s3_run_folder_path)
        run_barcode = run.s3_run_folder_path.split('/')[-1]
        return render_template('main/illumina_run.html', runid=runid, run_barcode=run_barcode,
                               experiment_name=run.experiment_name, flowcell=run.flowcell_id,
                               bucket=bucket, prefix=key)
    return abort(404)

@BP.route("/projects")
@login_required
def show_projects():
    ''' Show Projects page '''
    return render_template('main/projects.html')

@BP.route("/projects/<projectid>")
@login_required
def show_project(projectid):
    ''' Show Project page '''
    basespace_project = base_space.get_project_id(projectid)
    project = Project.query.get(projectid)

    if project:
        xpress_project_id = project.xpress_project_id
    else:
        xpress_project_id = 0

    runs = db.session.query(SequencingRun).join(RunToSamples).filter(
        RunToSamples.project_id == projectid).distinct(RunToSamples.sequencing_run_id)
    associated_runs = []
    for run in runs:
        if run.experiment_name:
            barcode = run.experiment_name
        else:
            barcode = "%s_%s_%s_%s" % (run.run_date.strftime("%y%m%d"), run.machine_id,
                                       run.run_number.zfill(4), run.flowcell_id)
        associated_runs.append({'id': run.id, 'barcode': barcode})
    return render_template('main/project.html', projectid=projectid,
                           basespace_project=basespace_project,
                           xpress_project_id=xpress_project_id,
                           runs=associated_runs,
                           data_bucket=current_app.config['DATA_BUCKET'],
                           results_bucket=current_app.config["RESULTS_BUCKET"])
