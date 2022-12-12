import re
import urllib3
import certifi
import urllib.parse
import psycopg2
import psycopg2.extras
import json
from flask import (
    Blueprint, request, current_app, render_template, flash, g, url_for
)
# from werkzeug.utils import secure_filename
from MobiDetailsApp.db import get_db, close_db
from . import (
    md_utilities
)

bp = Blueprint('upload', __name__)

# adapted from
# https://pythonise.com/series/learning-flask/flask-uploading-files


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
    # if not "." in filename:
    #     return False
    # ext = filename.rsplit(".", 1)[1]
    # if ext.lower() in current_app.config['ALLOWED_EXTENSIONS']:
    #     return True
    # else:
    #     return False


# def allowed_filesize(filesize):
#     if int(filesize) <= current_app.config["MAX_CONTENT_LENGTH"]:
#         return True
#     else:
#         return False


@bp.route('/file_upload', methods=['GET', 'POST'])
def file_upload():
    if request.method == 'POST':
        if request.files:
            uploaded_file = request.files['file']
            if uploaded_file.filename == "":
                flash('No filename.', 'w3-pale-red')
                return render_template('upload/upload_form.html')
                # return redirect(request.url)
            if allowed_file(uploaded_file.filename):
                # filename = secure_filename(uploaded_file.filename)
                lines = uploaded_file.read().decode().replace('\r\n', '\n').replace('\r', '\n').split('\n')
                # print(lines)
                # ok we've got the file
                # get user API key or use MD
                db = get_db()
                curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
                http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
                # headers
                header = md_utilities.api_agent
                result = []
                api_key = md_utilities.get_api_key(g, curs)
                if api_key is None:
                    flash('There is an issue in obtaining an API key')
                    close_db()
                    return render_template('upload/upload_form.html')
                    # return redirect(request.url)
                # we need to check the format and send a proper query to the API
                for line in lines:
                    # print('-{}-'.format(line))
                    # cDNA format
                    md_response = []
                    if re.search(r'^#', line) or \
                            line == '':
                        continue
                    line = line.replace(' ', '')
                    variant_regexp = md_utilities.regexp['variant']
                    ncbi_transcript_regexp = md_utilities.regexp['ncbi_transcript']
                    match_obj_c = re.search(rf'^({ncbi_transcript_regexp})\(*[\w-]*\)*:(c\.{variant_regexp})$', line)
                    if match_obj_c:
                        # check NM number and version
                        curs.execute(
                            """
                            SELECT gene_symbol
                            FROM gene
                            WHERE refseq = %s
                            """,
                            (match_obj_c.group(1),)
                        )
                        res_gene = curs.fetchone()
                        if res_gene:
                            # send var to api
                            md_api_url = '{0}{1}'.format(request.host_url[:-1], url_for('api.api_variant_create'))
                            # md_api_url = '{0}/api/variant/create'.format(md_api_base_url)
                            # print(md_api_url)
                            data = {
                                'variant_chgvs': urllib.parse.quote(
                                    '{0}:{1}'.format(
                                        match_obj_c.group(1),
                                        match_obj_c.group(2)
                                    )
                                ),
                                'caller': 'cli',
                                'api_key': api_key
                            }
                            try:
                                md_response = json.loads(
                                    http.request(
                                        'POST',
                                        md_api_url,
                                        headers=header,
                                        fields=data
                                    ).data.decode('utf-8')
                                )
                                result.append(
                                    {'variant': line,
                                        'id': md_response['mobidetails_id'],
                                        'url': md_response['url']}
                                )
                            except Exception:
                                if 'mobidetails_error' in md_response:
                                    result.append({'variant': line, 'error': md_response['mobidetails_error']})
                                else:
                                    result.append({'variant': line, 'error': 'MDAPI call failed'})
                        else:
                            result.append({'variant': line, 'error': 'Unknown NCBI NM accession number'})
                        continue
                    # genomic format
                    ncbi_chrom_regexp = md_utilities.regexp['ncbi_chrom']
                    match_obj_g = re.search(rf'^({ncbi_chrom_regexp}:g\.{variant_regexp});([\w-]+)$', line)
                    if match_obj_g:
                        # check gene is available
                        curs.execute(
                            """
                            SELECT gene_symbol
                            FROM gene
                            WHERE refseq = %s
                            """,
                            (match_obj_g.group(2),)
                        )
                        res_gene = curs.fetchone()
                        if res_gene:
                            # send var to api
                            md_api_url = '{0}{1}'.format(request.host_url[:-1], url_for('api.api_variant_g_create'))
                            # print(md_api_url)
                            data = {
                                'variant_ghgvs': urllib.parse.quote(match_obj_g.group(1)),
                                'gene_hgnc': match_obj_g.group(2),
                                'caller': 'cli',
                                'api_key': api_key
                            }
                            try:
                                md_response = json.loads(
                                    http.request(
                                        'POST',
                                        md_api_url,
                                        headers=header,
                                        fields=data
                                    ).data.decode('utf-8')
                                )
                                # print(md_response)
                                result.append({'variant': line, 'id': md_response['mobidetails_id']})
                            except Exception:
                                if 'variant_validator_output' in md_response and \
                                        'validation_warning_1' in md_response['variant_validator_output'] and \
                                        'validation_warnings' in md_response['variant_validator_output']['validation_warning_1']:
                                    result.append(
                                        {'variant': line,
                                            'error': md_response['variant_validator_output']['validation_warning_1']['validation_warnings'][0]}
                                    )
                                elif 'mobidetails_error' in md_response:
                                    result.append({'variant': line, 'error': md_response['mobidetails_error']})
                                else:
                                    result.append({'variant': line, 'error': 'MDAPI call failed'})
                        else:
                            result.append({'variant': line, 'error': 'Unknown gene'})
                        continue
                    if re.search(r'^rs\d+$', line):
                        md_api_url = '{0}{1}'.format(request.host_url[:-1], url_for('api.api_variant_create_rs'))
                        # md_api_url = '{0}/api/variant/create'.format(md_api_base_url)
                        # print(md_api_url)
                        data = {
                            'rs_id': line,
                            'caller': 'cli',
                            'api_key': api_key
                        }
                        try:
                            md_response = json.loads(
                                http.request(
                                    'POST',
                                    md_api_url,
                                    headers=header,
                                    fields=data
                                ).data.decode('utf-8')
                            )
                            for var in md_response:
                                # print(md_response[var])
                                if 'mobidetails_error' in md_response[var]:
                                    result.append(
                                        {'variant': '{0} - {1}'.format(line, var),
                                            'error': md_response[var]['mobidetails_error']}
                                    )
                                elif var == 'mobidetails_error':
                                    result.append({'variant': line, 'error': md_response[var]})
                                else:
                                    result.append(
                                        {'variant': '{0} - {1}'.format(line, var),
                                            'id': md_response[var]['mobidetails_id'],
                                            'url': md_response[var]['url']}
                                    )

                        except Exception:
                            result.append({'variant': line, 'error': 'MDAPI call failed'})
                        continue
                    result.append({'variant': line, 'error': 'Bad format'})
                close_db()
                flash('File correctly uploaded', 'w3-pale-green')
                if g.user:
                    # send an email
                    # print(g.user)
                    result_list = ''
                    for resul in result:
                        result_list = '{0}<li>{1}'.format(result_list, resul['variant'])
                        if 'error' in resul:
                            result_list = '{0} - {1}</li>'.format(result_list, resul['error'])
                        else:
                            result_list = '{0} - <a href="{1}{2}">success</a></li>'.format(
                                result_list,
                                request.host_url[:-1],
                                url_for(
                                    'api.variant',
                                    variant_id=resul['id'],
                                    caller='browser'
                                )
                            )

                    message = """
                    Dear {0},<br /><p>Your batch job returned the following results:
                    </p><ul>{1}</ul><p>You can have a direct acces to the successfully annotated variants at your
                    <a href="{2}{3}">profile page</a>.
                    """.format(
                        g.user['username'],
                        result_list,
                        request.host_url[:-1],
                        url_for(
                            'auth.profile',
                            mobiuser_id=0
                        )
                    )
                    md_utilities.send_email(
                        md_utilities.prepare_email_html(
                            'MobiDetails - Batch job',
                            message,
                            False
                        ),
                        '[MobiDetails - Batch job]',
                        [g.user['email']]
                    )
                return render_template('md/variant_multiple.html', upload=result)
            else:
                flash('That file extension is not allowed', 'w3-pale-red')
                return render_template('upload/upload_form.html')
                # return redirect(request.url)

    return render_template("upload/upload_form.html", run_mode=md_utilities.get_running_mode())
