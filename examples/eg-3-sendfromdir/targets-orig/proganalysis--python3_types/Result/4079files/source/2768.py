import glob
import json
import os
import os.path as path

from flask import Flask, render_template, request, send_from_directory

from elvis.config import *
from elvis.utils import *

gold_info = get_mentions_info(gold_info_path)


def get_mention_by_startindex_for_document(mentions_df: pd.DataFrame, doc: str):
    mention_for_document_df = mentions_df[mentions_df['Doc_Id'] == doc[:doc.find('.')]]
    result = {}
    for ix, row in mention_for_document_df.iterrows():
        if not result.__contains__(int(row['Begin'])):
            result[int(row['Begin'])] = []
        result[int(row['Begin'])].append(row)
    return result


grouped_documents = []
id = 0
for lang in ['eng', 'spa',]:
    for domain in ['newswire', 'discussion_forum']:
        if path.isdir(documents_path + '/' + lang + '/' + domain):
            files = []
            for file in os.listdir(documents_path + '/' + lang + '/' + domain):
                if 'ltf' not in file:
                    id += 1
                    files.append({'id': lang + '/' + domain + '/' + file, 'tag': file})
            grouped_documents.append({'langDomain': str.capitalize(lang) + ' ' + str.capitalize(domain), 'files': files})
        else:
            raise FileNotFoundError(documents_path + '/' + lang + '/' + domain + ' does not exist!')

for lang in [ 'cmn']:
    for domain in ['nw', 'df']:
        if path.isdir(documents_path + '/' + lang + '/' + domain):
            files = []
            for file in os.listdir(documents_path + '/' + lang + '/' + domain):
                if 'ltf' not in file:
                    id += 1
                    files.append({'id': lang + '/' + domain + '/' + file, 'tag': file})
            grouped_documents.append({'langDomain': str.capitalize(lang) + ' ' + str.capitalize(domain), 'files': files})
        else:
            raise FileNotFoundError(documents_path + '/' + lang + '/' + domain + ' does not exist!')


if id == 0:
    raise FileNotFoundError(
        documents_path + '/' + lang + '/' + domain + ' does not contain any source documents! Did you run ltf2src.perl on the document directories?')

# ROUTING

app = Flask(__name__)


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('./templates/js', path)


@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('./templates/css', path)


@app.route('/get_documents')
def get_documents():
    return json.dumps(grouped_documents)


@app.route('/get_system_output')
def get_annotations():
    system_output = [{'id': file.split('/')[-2], 'tag': file.split('/')[-2]} for file in
                     sorted(glob.glob(system_output_path + '/*/' + system_output_file_name), reverse=True)]
    return json.dumps(system_output)


@app.route('/get_document')
def get_document():
    request_document = request.args.get('document').split('/')
    request_system_output = request.args.get('systemOutput')

    if len(request_document) == 3:
        lang, domain, doc_id = request_document
        if lang in ['eng', 'spa', 'cmn'] and domain in ['newswire', 'discussion_forum']:
            with open(documents_path + '/' + request.args.get('document'), 'r') as doc:
                mention_by_startindex_gold = get_mention_by_startindex_for_document(gold_info, doc_id)
                system_info = get_mentions_info(system_output_path + '/' + request_system_output + '/' + system_output_file_name)
                mention_by_startindex_system = get_mention_by_startindex_for_document(system_info, doc_id)
                result = []
                end = []

                for _ix, char in enumerate(''.join(doc.readlines())):
                    ix = _ix - 39
                    mention_labels = {}
                    mention_infos = {}
                    mention_ends = {}

                    if ix in mention_by_startindex_system.keys():
                        gold_mention = None
                        system_mention = None
                        for a_system_mention_at_ix in mention_by_startindex_system[ix]:
                            if a_system_mention_at_ix['Mention'] not in mention_labels:
                                mention_labels[a_system_mention_at_ix['Mention']] = []
                                mention_infos[a_system_mention_at_ix['Mention']] = []
                                mention_ends[a_system_mention_at_ix['Mention']] = []
                            if ix in mention_by_startindex_gold.keys():
                                for a_gold_mention_at_ix in mention_by_startindex_gold[ix]:
                                    if int(a_gold_mention_at_ix['End']) == int(a_system_mention_at_ix['End']):
                                        gold_mention = a_gold_mention_at_ix
                                        system_mention = a_system_mention_at_ix

                                        mention_labels[system_mention['Mention']].append([])
                                        mention_labels[system_mention['Mention']][-1].append('is_tp')

                                        mention_infos[system_mention['Mention']].append([])
                                        mention_infos[a_system_mention_at_ix['Mention']][-1].append('<table>')
                                        mention_infos[a_system_mention_at_ix['Mention']][-1].append('<tr><td>Mention String</td><td>[' + a_system_mention_at_ix['Mention_String'].replace("\"", "''") + ']</td></tr>')
                                        mention_infos[a_system_mention_at_ix['Mention']][-1].append('<tr><td></td><td></td></tr>')
                                        mention_infos[a_system_mention_at_ix['Mention']][-1].append('<tr><td>System Mention Type</td><td>' + a_system_mention_at_ix['Mention_Type'] + '</td></tr>')

                                        mention_infos[a_system_mention_at_ix['Mention']][-1].append('<tr><td>System Entity Type</td><td>' + a_system_mention_at_ix['Entity_Type'] + '</td></tr>')
                                        if not system_mention['Entity_Type'] == gold_mention['Entity_Type']:
                                            mention_labels[system_mention['Mention']][-1].append('is_fp_nerc')
                                            mention_infos[a_system_mention_at_ix['Mention']][-1].append(
                                                '<tr><td>Gold Entity Type</td><td>' + gold_mention[
                                                    'Entity_Type'] + '</td></tr>')

                                        mention_infos[a_system_mention_at_ix['Mention']][-1].append('<tr><td>System KBID</td><td>' + get_entity_name_from_id(a_system_mention_at_ix['KBID']) + '</td></tr>')
                                        if not (system_mention['KBID'].startswith("NIL") and gold_mention['KBID'].startswith("NIL")) and not system_mention['KBID'] == gold_mention['KBID']:
                                            mention_labels[system_mention['Mention']][-1].append('is_fp_nerl')
                                            mention_infos[a_system_mention_at_ix['Mention']][-1].append(
                                                '<tr><td>Gold KBID</td><td>' + get_entity_name_from_id(
                                                    gold_mention['KBID']) + '</td></tr>')

                                        mention_infos[a_system_mention_at_ix['Mention']][-1].append('</table>')

                                        mention_ends[system_mention['Mention']].append(
                                            int(a_system_mention_at_ix['End']))

                                        end.append(int(a_system_mention_at_ix['End']))
                            if len(mention_labels[a_system_mention_at_ix['Mention']]) == 0:
                                mention_labels[a_system_mention_at_ix['Mention']].append([])
                                mention_labels[a_system_mention_at_ix['Mention']][-1].append('is_fp_ner')
                                mention_infos[a_system_mention_at_ix['Mention']].append([])
                                mention_infos[a_system_mention_at_ix['Mention']][-1].append('<table>')
                                mention_infos[a_system_mention_at_ix['Mention']][-1].append(
                                    '<tr><td>Mention String</td><td>[' + a_system_mention_at_ix['Mention_String'].replace("\"", "''") + ']</td></tr>')
                                mention_infos[a_system_mention_at_ix['Mention']][-1].append('<tr><td></td><td></td></tr>')
                                mention_infos[a_system_mention_at_ix['Mention']][-1].append('<tr><td>System Mention Type</td><td>' + a_system_mention_at_ix['Mention_Type'] + '</td></tr>')
                                mention_infos[a_system_mention_at_ix['Mention']][-1].append('<tr><td>System Entity Type</td><td>' + a_system_mention_at_ix['Entity_Type'] + '</td></tr>')
                                mention_infos[a_system_mention_at_ix['Mention']][-1].append('<tr><td>System KBID</td><td>' + get_entity_name_from_id(a_system_mention_at_ix['KBID']) + '</td></tr>')
                                mention_infos[a_system_mention_at_ix['Mention']][-1].append('</table>')
                                mention_ends[a_system_mention_at_ix['Mention']].append(
                                    int(a_system_mention_at_ix['End']))
                                end.append(int(a_system_mention_at_ix['End']))

                    if ix in mention_by_startindex_gold.keys():
                        gold_mention = None
                        system_mention = None
                        for a_gold_mention_at_ix in mention_by_startindex_gold[ix]:
                            tp = 0
                            if a_gold_mention_at_ix['Mention'] not in mention_labels.keys():
                                mention_labels[a_gold_mention_at_ix['Mention']] = []
                                mention_infos[a_gold_mention_at_ix['Mention']] = []
                                mention_ends[a_gold_mention_at_ix['Mention']] = []
                            if ix in mention_by_startindex_system.keys():
                                for a_system_mention_at_ix in mention_by_startindex_system[ix]:
                                    if int(a_gold_mention_at_ix['End']) == int(a_system_mention_at_ix['End']):
                                        tp += 1
                            if tp == 0:
                                mention_labels[a_gold_mention_at_ix['Mention']].append([])
                                mention_labels[a_gold_mention_at_ix['Mention']][-1].append('is_fn_ner')
                                mention_infos[a_gold_mention_at_ix['Mention']].append([])
                                mention_infos[a_gold_mention_at_ix['Mention']][-1].append('<table>')
                                mention_infos[a_gold_mention_at_ix['Mention']][-1].append(
                                    '<tr><td>Mention String</td><td>[' + a_gold_mention_at_ix['Mention_String'].replace("\"", "''") + ']</td></tr>')
                                mention_infos[a_gold_mention_at_ix['Mention']][-1].append('<tr><td></td><td></td></tr>')
                                mention_infos[a_gold_mention_at_ix['Mention']][-1].append('<tr><td>Gold Mention Type</td><td>' + a_gold_mention_at_ix['Mention_Type'] + '</td></tr>')
                                mention_infos[a_gold_mention_at_ix['Mention']][-1].append('<tr><td>Gold Entity Type</td><td>' + a_gold_mention_at_ix['Entity_Type'] + '</td></tr>')
                                mention_infos[a_gold_mention_at_ix['Mention']][-1].append('<tr><td>Gold KBID</td><td>' + get_entity_name_from_id(a_gold_mention_at_ix['KBID']) + '</td></tr>')
                                mention_infos[a_gold_mention_at_ix['Mention']][-1].append('</table>')
                                mention_ends[a_gold_mention_at_ix['Mention']].append(int(a_gold_mention_at_ix['End']))
                                end.append(int(a_gold_mention_at_ix['End']))

                    for mention_key in sorted(mention_labels.keys(), key=lambda x: mention_ends[x], reverse=True):
                        for m_labels, m_infos in zip(mention_labels[mention_key], mention_infos[mention_key]):
                            result.append('<span class=" is_mention ' + ' '.join(
                                m_labels) + '" role="button" data-trigger="click" title="' + mention_key + '" data-container="body" data-toggle="popover" data-placement="bottom" data-content="' + ''.join(
                                m_infos) + '">')
                    result.append(char)

                    if len(end) > 0 and ix in end:
                        for _ in range(end.count(ix)):
                            result.append('</span>')
                        end.remove(ix)

                return json.dumps(transform_tac_to_html(''.join(result)))


@app.route('/')
def index():
    return render_template('index.html')
