import os
import re
import datetime
import psycopg2
import psycopg2.extras
import tabix
import urllib3
import certifi
import json
import yaml
import twobitreader
import tempfile
import subprocess
from flask import (
    url_for, request, render_template, current_app as app
)
from flask_mail import Message
from werkzeug.urls import url_parse
# from . import config
from MobiDetailsApp import mail

app_path = os.path.dirname(os.path.realpath(__file__))
# get config file with paths, etc
resources = yaml.safe_load(open('{}/sql/md_resources.yaml'.format(app_path)))

host = resources['host']
regexp = resources['regexp']

api_agent = resources['api_agent']

ext_exe = resources['ext_exe']
ext_exe['maxentscan5'] = '{0}{1}'.format(
    app_path, resources['ext_exe']['maxentscan5']
)
ext_exe['maxentscan3'] = '{0}{1}'.format(
    app_path, resources['ext_exe']['maxentscan3']
)


def get_resource_current_version(resource_dir, regexp):
    files = os.listdir(resource_dir)
    dates = []
    for current_file in files:
        # print(current_file)
        # match_obj = re.search(rf'clinvar_(\d+).vcf.gz$', current_file)
        match_obj = re.search(rf'{regexp}$', current_file)
        if match_obj:
            dates.append(match_obj.group(1))
    return max(dates)


one2three = resources['one2three']
three2one = resources['three2one']
urls = resources['urls']
local_files = resources['local_files']
local_files['cadd']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['cadd']['rel_path']
)
local_files['cadd_indels']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['cadd_indels']['rel_path']
)
local_files['clinpred']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['clinpred']['rel_path']
)
clingen_version = get_resource_current_version(
    '{0}{1}'.format(app_path, local_files['clingen_criteria_specification']['rel_path']),
    r'clingenCriteriaSpec_(\d+).json'
)
local_files['clingen_criteria_specification']['abs_path'] = '{0}{1}clingenCriteriaSpec_last.json'.format(
    app_path, local_files['clingen_criteria_specification']['rel_path']
)
local_files['clingen_criteria_specification_index'] = {}
local_files['clingen_criteria_specification_index']['abs_path'] = '{0}{1}clingenCriteriaSpec_last.txt'.format(
    app_path, local_files['clingen_criteria_specification']['rel_path']
)
clinvar_version = get_resource_current_version(
    '{0}{1}'.format(app_path, local_files['clinvar_hg38']['rel_path']),
    r'clinvar_(\d+).vcf.gz'
)
local_files['clinvar_hg38']['abs_path'] = '{0}{1}clinvar_{2}.vcf.gz'.format(
    app_path,
    local_files['clinvar_hg38']['rel_path'],
    clinvar_version
)

local_files['dbmts']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['dbmts']['rel_path']
)
local_files['dbnsfp']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['dbnsfp']['rel_path']
)
local_files['dbscsnv']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['dbscsnv']['rel_path']
)
local_files['dbsnp']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['dbsnp']['rel_path']
)
local_files['episignature']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['episignature']['rel_path']
)
local_files['gnomad_exome']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['gnomad_exome']['rel_path']
)
local_files['gnomad_genome']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['gnomad_genome']['rel_path']
)
local_files['gnomad_3']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['gnomad_3']['rel_path']
)
local_files['hgnc_full_set']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['hgnc_full_set']['rel_path']
)
local_files['human_genome_hg38']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['human_genome_hg38']['rel_path']
)
local_files['lovd_ref']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['lovd_ref']['rel_path']
)
local_files['lovd_api_json']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['lovd_api_json']['rel_path']
)
local_files['maxentscan']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['maxentscan']['rel_path']
)
local_files['metadome']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['metadome']['rel_path']
)
local_files['mistic']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['mistic']['rel_path']
)
local_files['spip']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['spip']['rel_path']
)
local_files['spliceai_folder']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['spliceai_folder']['rel_path']
)
local_files['spliceai_snvs']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['spliceai_snvs']['rel_path']
)
local_files['spliceai_indels']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['spliceai_indels']['rel_path']
)
local_files['uniprot']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['uniprot']['rel_path']
)
local_files['variant_validator']['abs_path'] = '{0}{1}'.format(
    app_path, local_files['variant_validator']['rel_path']
)

predictor_thresholds = resources['predictor_thresholds']
predictor_colors = resources['predictor_colors']
predictors_translations = resources['predictors_translations']
complement = resources['complement']
hidden_external_tools = resources['hidden_external_tools']
external_tools = resources['external_tools']
for tool in external_tools:
    if re.search(r'^\d+$', external_tools[tool]['paper']):
        external_tools[tool]['paper'] = '{0}{1}'.format(
            urls['ncbi_pubmed'], external_tools[tool]['paper']
        )
external_tools['ClinVar']['version'] = 'v{}'.format(
    clinvar_version
)
external_tools['ClinGenSpecificationRegistry']['version'] = 'v{}'.format(
    clingen_version
)
acmg_criteria = resources['acmg']
lovd_effect = resources['lovd_effect']
spip_headers = resources['spip_headers']
spip_annotations = resources['spip_annotations']
countries = resources['countries']

# create a poolmanager
http = urllib3.PoolManager(
    cert_reqs='CERT_REQUIRED',
    ca_certs=certifi.where(),
    timeout=urllib3.Timeout(connect=1.0, read=5.0)
)


def reverse_complement(seq):
    return "".join(complement[base] for base in reversed(seq.upper()))


def clean_var_name(variant):
    variant = re.sub(r'^[cpg]\.', '', variant)
    variant = re.sub(r'\(', '', variant)
    variant = re.sub(r'\)', '', variant)
    if re.search('>', variant):
        variant = variant.upper()
    elif re.search('d[eu][lp]', variant):
        match_obj = re.search(r'^(.+d[eu][lp])[ATCG]+$', variant)
        if match_obj:
            variant = match_obj.group(1)
        else:
            match_obj = re.search(r'^(.+del)[ATCG]+(ins[ACTG])$', variant)
            if match_obj:
                variant = match_obj.group(1) + match_obj.group(2)
    return variant


def three2one_fct(var):
    var = clean_var_name(var)
    match_object = re.search(r'^(\w{3})(\d+)(\w{3}|[X\*=])$', var)
    if match_object:
        if re.search('d[ue][pl]', match_object.group(3)):
            return three2one[match_object.group(1).capitalize()] + \
                match_object.group(2) + \
                match_object.group(3)
        else:
            return three2one[match_object.group(1).capitalize()] + \
                match_object.group(2) + \
                three2one[match_object.group(3).capitalize()]
    match_object = re.search(r'^(\w{3})(\d+_)(\w{3})(\d+.+)$', var)
    if match_object:
        return three2one[match_object.group(1)].capitalize() + \
            match_object.group(2) + \
            three2one[match_object.group(3)].capitalize() + \
            match_object.group(4)


def one2three_fct(var):
    var = clean_var_name(var)
    match_object = re.search(r'^(\w{1})(\d+)([\w\*=]{1})$', var)
    if match_object:
        return one2three[match_object.group(1).capitalize()] + \
            match_object.group(2) + \
            one2three[match_object.group(3).capitalize()]
    match_object = re.search(r'^(\w{1})(\d+)(d[ue][pl])$', var)
    if match_object:
        return one2three[match_object.group(1).capitalize()] + \
            match_object.group(2) + \
            match_object.group(3)
    match_object = re.search(r'^(\w{1})(\d+_)(\w{1})(\d+.+)$', var)
    if match_object:
        return one2three[match_object.group(1).capitalize()] + \
            match_object.group(2) + \
            one2three[match_object.group(3).capitalize()] + \
            match_object.group(4)


def get_ncbi_chr_name(db, chr_name, genome):
    # get NCBI chr names for common names
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if is_valid_full_chr(chr_name):
        short_chr = get_short_chr_name(chr_name)
        if short_chr is not None:
            curs.execute(
                """
                SELECT ncbi_name
                FROM chromosomes
                WHERE genome_version = %s
                    AND name = %s
                """,
                (genome, short_chr)
            )
            ncbi_name = curs.fetchone()
            # print(ncbi_name)
            if ncbi_name is not None:
                return ncbi_name


def get_common_chr_name(db, ncbi_name):
    # get common chr names for NCBI names
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if is_valid_ncbi_chr(ncbi_name):
        curs.execute(
            """
            SELECT name, genome_version
            FROM chromosomes
            WHERE ncbi_name = %s
            """,
            (ncbi_name,)
        )
        res = curs.fetchone()
        if res is not None:
            return res
        else:
            return None, None


def is_valid_full_chr(chr_name):  # chr name is valid?
    nochr_captured_regexp = regexp['nochr_captured']
    if re.search(rf'^[Cc][Hh][Rr]({nochr_captured_regexp})$', chr_name):
        return True
    return False


def get_short_chr_name(chr_name):  # get small chr name
    nochr_captured_regexp = regexp['nochr_captured']
    match_obj = re.search(
        rf'^[Cc][Hh][Rr]({nochr_captured_regexp})$', chr_name
    )
    if match_obj is not None:
        return match_obj.group(1)


def is_valid_chr(chr_name):  # chr name is valid?
    nochr_captured_regexp = regexp['nochr_captured']
    if re.search(rf'^({nochr_captured_regexp})$', chr_name):
        return True
    return False


def is_valid_ncbi_chr(chr_name):  # NCBI chr name is valid?
    if re.search(r'^[Nn][Cc]_0000\d{2}\.\d{1,2}$', chr_name):
        return True
    return False


def translate_genome_version(genome_version):
    if genome_version.upper() == 'GRCH38':
        return 'hg38'
    elif genome_version.upper() == 'GRCH37':
        return 'hg19'
    elif re.search(r'^[hH][gG][13][98]$', genome_version):
        return genome_version.lower()
    else:
        return 'wrong_genome_input'


def decompose_vcf_str(vcf_str):
    # chr_regexp = regexp['nochr_captured']
    vcf_str_regexp = regexp['vcf_str_captured']
    match_obj = re.search(rf'^{vcf_str_regexp}$', vcf_str)
    # match_obj = re.search(rf'[Cc]?[Hh]?[Rr]?({chr_regexp})[:-](\d+)[:-]([ACTGactg]+)[:-]([ACTGactg]+)', vcf_str)
    if match_obj:
        return match_obj.group(1), int(match_obj.group(2)), match_obj.group(3).upper(), match_obj.group(4).upper()
    else:
        return None, None, None, None


def get_var_genic_csq(var):
    # linked to function below => quick assessment of csq
    if re.search(r'^\d+[\+-]', var):
        return 'intron'
    elif re.search(r'^\*?\d+[^\+-]', var):
        return 'exon'
    elif re.search(r'^-', var):
        return '5UTR'


def is_higher_genic_csq(new_csq, old_csq):
    # function to assess exon>intron>5UTR (designed originally for vcf_str api endpoint but not used)
    if new_csq == 'exon' or \
            new_csq == old_csq:
        return True
    elif new_csq != 'exon' and \
            old_csq == 'exon':
        return False
    elif new_csq == '5UTR' and \
            old_csq == 'intron':
        return False
    else:
        return True


def get_pos_splice_site(pos, positions):
    # compute position relative to nearest splice site
    if positions is not None:
        # print("{0}-{1}-{2}".format(positions['segment_start'],pos,positions['segment_end']))
        if abs(int(positions['segment_end'])-int(pos)+1) <=\
                abs(int(positions['segment_start'])-int(pos)+1):
            # near from segment_end
            # always exons!!!!
            return [
                'donor',
                abs(int(positions['segment_end'])-int(pos))+1
            ]
        else:
            # near from segment_start
            return [
                'acceptor',
                abs(int(positions['segment_start'])-int(pos))+1]


def get_pos_splice_site_intron(name):
    # get position of intronic variant to the nearest ss
    match_obj = re.search(r'^[\*-]?\d+([\+-])(\d+)[^\d_]', name)
    if match_obj:
        return [
            int(match_obj.group(2)),
            match_obj.group(1)
        ]
    match_obj = re.search(
        r'[\*-]?\d+([\+-])(\d+)_[\*-]?\d+[\+-](\d+)[^\d_]', name
    )
    if match_obj:
        return [
            min(
                int(match_obj.group(2)),
                int(match_obj.group(3))
            ),
            match_obj.group(1)
        ]
    if re.search(r'[\*-]?\d+[-]\d+_\d+[^\d_]', name):
        # overlapping variant
        return [1, '-']


def get_pos_exon_canvas(pos, positions):
    # compute relative position in exon for canvas drawing
    if positions is not None:
        pos_from_beginning = abs(int(positions['segment_start'])-int(pos))+1
        # rel_pos = pos_from_beginning / positions['segment_size']
        # rel_pos_canvas = rel_pos * 200
        return [
            200 + int(
                round(
                    (int(pos_from_beginning) / int(positions['segment_size']))*200
                )
            ),
            int(positions['segment_size'])
        ]


def get_exon_neighbours(db, positions):
    # get introns names, numbers surrounding an exon
    prec_type = prec_number = fol_type = fol_number = None
    # preceeding segment if 5UTR or an intron
    if positions['number'] == 1:
        prec_type = "5'"
        prec_number = "UTR"
    else:
        prec_type = "intron"
        prec_number = positions['number'] - 1
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # following segemnt is either an intron or 3UTR
    curs.execute(
        """
        SELECT number_of_exons
        FROM gene
        WHERE refseq = %s
        """,
        (positions['refseq'],)
    )
    res_nm = curs.fetchone()
    if res_nm['number_of_exons'] == positions['number']:
        fol_type = "3'"
        fol_number = "UTR"
    else:
        fol_type = "intron"
        fol_number = positions['number']
    return [prec_type, prec_number, fol_type, fol_number]


def get_exon_sequence(positions, chrom, strand):
    # get DNA sequence for a given exon
    if isinstance(positions['number'], int) and \
            re.search(r'^NM_\d+\.\d+$', positions['refseq']) and \
            re.search(r'^\d+$', chrom) and \
            re.search(r'^[\+-]+', strand):
        genome = twobitreader.TwoBitFile(
            '{}.2bit'.format(local_files['human_genome_hg38']['abs_path'])
        )
        current_chrom = genome['chr{}'.format(chrom)]
        exon_start = int(positions['segment_start'])
        exon_end = int(positions['segment_end'])
        if exon_start < exon_end:
            exon_seq = current_chrom[exon_start-1:exon_end].upper()
        else:
            exon_seq = current_chrom[exon_end-1:exon_start].upper()
        if strand == '-':
            exon_seq = reverse_complement(exon_seq).upper()
        return exon_seq
    else:
        return 'Wrong or lacking parameter'


def get_exonic_substitution_position(var_cdna):
    # from 158C>T get 158
    match_obj = re.search(r'^[\*-]?(\d+)[ATCG]', var_cdna)
    if match_obj:
        return match_obj.group(1)
    return None


def get_substitution_nature(var_cdna):
    # from 158C>T or 158-1C>T get C>T
    match_obj = re.search(r'([ATCG]>[ATGC])$', var_cdna)
    if match_obj:
        return match_obj.group(1)
    return None


def get_exon_first_nt_cdna_position(positions, var_gpos, var_c):
    # we have a variant b and an exon start genomic position a,
    # we want to get the c. of the exon start genomic
    # -------<a====b===>----
    dist_from_beg = abs(int(positions['segment_start'])-int(var_gpos)) + 1
    var_cpos = get_exonic_substitution_position(var_c)
    first_nt_cdna_position = (int(var_cpos) - dist_from_beg)
    if first_nt_cdna_position > 0:
        first_nt_cdna_position += 1
    return first_nt_cdna_position


def get_aa_position(hgvs_p):  # get aa position fomr hgvs p. (3 letter)
    match_object = re.search(r'^\w{3}(\d+)_\w{3}(\d+)[^\d]+$', hgvs_p)
    if match_object:
        # return "{0}_{1}".format(match_object.group(1), match_object.group(2))
        return match_object.group(1), match_object.group(2)
    match_object = re.search(r'^\w{3}(\d+)[^\d]+.*$', hgvs_p)
    if match_object:
        return match_object.group(1), match_object.group(1)


def get_user_id(username, db):
    if username:
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT id
            FROM mobiuser
            WHERE username = %s
            """,
            (username,)
        )
        res_user = curs.fetchone()
        if res_user:
            return res_user['id']
    return None


def define_lovd_class(acmg_classes, db):
    lovd_class = None
    if isinstance(acmg_classes, list):
        for acmg_class in acmg_classes:
            if (isinstance(acmg_class, list) or
                    isinstance(acmg_class, dict)) and \
                    'acmg_class' in acmg_class:
                # list => true DictRow from psycopg2
                # dict for pytest
                # print(acmg_classes)
                # print(acmg_class['acmg_class'])
                # 1st iteration
                if not lovd_class:
                    lovd_class = acmg2lovd(acmg_class['acmg_class'], db)
                # VUS => VUS
                if acmg_class['acmg_class'] == 3:
                    lovd_class = 'VUS'
                    break
                elif lovd_class != 'Conflicting':
                    # do sthg
                    if (acmg_class['acmg_class'] == 1 or
                            acmg_class['acmg_class'] == 2) and \
                            (lovd_class == 'Likely Pathogenic' or
                                lovd_class == 'Pathogenic'):
                        lovd_class = 'Conflicting'
                    elif (acmg_class['acmg_class'] == 4 or
                            acmg_class['acmg_class'] == 5) and \
                            (lovd_class == 'Likely benign' or
                                lovd_class == 'Benign'):
                        lovd_class = 'Conflicting'
                    elif (lovd_class == 'Benign' and
                            acmg_class['acmg_class'] == 2):
                        lovd_class = 'Likely benign'
                    elif (lovd_class == 'Likely benign' and
                            acmg_class['acmg_class'] == 1):
                        pass
                    elif (lovd_class == 'Pathogenic' and
                            acmg_class['acmg_class'] == 4):
                        lovd_class = 'Likely Pathogenic'
                    elif (lovd_class == 'Likely Pathogenic' and
                            acmg_class['acmg_class'] == 5):
                        pass
                    else:
                        lovd_class = acmg2lovd(acmg_class['acmg_class'], db)
                        # print('current acmg:{0} - current lovd: {1}'.format(
                        # acmg_class['acmg_class'], lovd_class))
    return lovd_class


def acmg2lovd(acmg_class, db):
    if isinstance(acmg_class, int):
        curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        curs.execute(
            """
            SELECT lovd_translation
            FROM valid_class
            WHERE acmg_class = %s
            """,
            (acmg_class,)
        )
        res_lovd_acmg = curs.fetchone()
        if res_lovd_acmg:
            return res_lovd_acmg[0]
    return None


def get_value_from_tabix_file(text, tabix_file, var, variant_features):
    # open a file with tabix and look for a record:
    tb = tabix.open(tabix_file)
    query = "{0}:{1}-{2}".format(var['chr'], var['pos'], var['pos'])
    # print(query)
    if text == 'gnomADv3' or \
            (re.search('MISTIC', tabix_file) and
                var['chr'] == 'X'):
        query = "chr{0}:{1}-{2}".format(var['chr'], var['pos'], var['pos'])
    try:
        records = tb.querys(query)
    except Exception as e:
        send_error_email(
            prepare_email_html(
                'MobiDetails error',
                """
                <p>A tabix failed</p><p>tabix {0} {1}<br />for variant:{2} with args: {3}</p>
                """.format(
                    tabix_file, query, var, e.args
                )
            ),
            '[MobiDetails - Tabix Error]'
        )
        return 'Match failed in {}'.format(text)

    i = 3
    if re.search(
            r'(dbNSFP|whole_genome_SNVs|dbscSNV|dbMTS|MISTIC|CADD/hg38/v1\.6/gnomad.genomes\.r3\.0\.indel)',
            tabix_file
            ):
        i -= 1
    for record in records:
        ref_list = re.split(',', record[i])
        alt_list = re.split(',', record[i+1])
        # print(record)
        # print('{}-{}-{}-{}'.format(var['pos_ref'], ref_list, var['pos_alt'], alt_list))
        if var['pos_ref'] in ref_list and \
                var['pos_alt'] in alt_list:
            return record
        elif re.search('dbNSFP', tabix_file) and \
                variant_features['dna_type'] == 'indel' and \
                variant_features['prot_type'] == 'missense':
            # particular case delins resulting in missense e.g.
            # FLNC c.3715_3716delinsTT p.Pro1239Phe
            aa1, ppos, aa2 = decompose_missense(variant_features['p_name'])
            i = 4
            ppos_list = re.split(';', record[i+7])
            if aa1 == record[i] and \
                    aa2 == record[i+1] and \
                    ppos in ppos_list:
                return record
    return 'No match in {}'.format(text)


def decompose_missense(p_name):
    match_obj = re.search(r'^([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})$', p_name)
    if match_obj:
        return three2one[match_obj.group(1)], match_obj.group(2), three2one[match_obj.group(3)]
    else:
        return None, None, None


def getdbNSFP_results(
        transcript_index, score_index, pred_index, sep,
        translation_mode, threshold_for_other,
        direction_for_other, dbnsfp_record):  # manage dbNSFP scores and values
    score = '.'
    pred = 'no prediction'
    star = ''
    try:
        score = re.split(
            '{}'.format(sep), dbnsfp_record[score_index]
        )[transcript_index]
        if pred_index != score_index:
            pred = predictors_translations[translation_mode][
                re.split(
                    '{}'.format(sep),
                    dbnsfp_record[pred_index]
                )[transcript_index]
            ]
            if score == '.':  # search most deleterious in other isoforms
                score, pred, star = get_most_other_deleterious_pred(
                    dbnsfp_record[score_index],
                    dbnsfp_record[pred_index],
                    threshold_for_other,
                    direction_for_other,
                    translation_mode
                )
    except Exception:
        try:
            score = dbnsfp_record[score_index]
            if pred_index != score_index:
                pred = predictors_translations[translation_mode][
                    dbnsfp_record[pred_index]
                ]
        except Exception:
            pass
    return score, pred, star


def get_spliceai_color(val):
    # returns an html color depending on spliceai score
    if val != '.':
        value = float(val)
        if value > predictor_thresholds['spliceai_max']:
            return predictor_colors['max']
        elif value > predictor_thresholds['spliceai_mid']:
            return predictor_colors['mid_effect']
        elif value > predictor_thresholds['spliceai_min']:
            return predictor_colors['small_effect']
        else:
            return predictor_colors['min']
    else:
        return predictor_colors['no_effect']


def get_most_other_deleterious_pred(
        score, pred, threshold, direction, pred_type):
    # returns most deleterious score of predictors
    # when not found in desired transcript
    j = 0
    k = 0
    best_score = threshold
    for score in re.split(';', score):
        if direction == 'lt':
            if score != '.' and \
                    float(score) < float(best_score):
                best_score = score
                k = j
        else:
            if score != '.' and \
                    float(score) > float(best_score):
                best_score = score
                k = j
        j += 1
    if best_score != threshold:
        return best_score, predictors_translations[pred_type][re.split(';', pred)[k]], '*'
    else:
        return '.', 'no prediction', ''


def get_preditor_single_threshold_color(val, predictor):
    # returns an html color depending on a single threshold
    # function to get green or red
    if val != '.':
        value = float(val)
        if predictor == 'sift':
            value = 1-(float(val))
        if value > predictor_thresholds[predictor]:
            return predictor_colors['max']
        return predictor_colors['min']
    else:
        return predictor_colors['no_effect']


def get_preditor_single_threshold_reverted_color(val, predictor):
    # returns an html color depending on a single threshold
    # (reverted, e.g. for fathmm)
    # function to get green or red
    if val != '.':
        if float(val) < predictor_thresholds[predictor]:
            return predictor_colors['max']
        return predictor_colors['min']
    else:
        return predictor_colors['no_effect']


def get_preditor_double_threshold_color(val, predictor_min, predictor_max):
    # returns an html color depending on a double threshold
    # function to get green or red
    if val != '.':
        value = float(val)
        if value > predictor_thresholds[predictor_max]:
            return predictor_colors['max']
        elif value > predictor_thresholds[predictor_min]:
            return predictor_colors['mid_effect']
        return predictor_colors['min']
    else:
        return predictor_colors['no_effect']


def get_metadome_colors(val):
    # returns a list of effect and color for metadome
    value = float(val)
    if value < predictor_thresholds['metadome_hintolerant']:
        return ['highly intolerant', predictor_colors['highly_intolerant']]
    if value < predictor_thresholds['metadome_intolerant']:
        return ['intolerant', predictor_colors['max']]
    elif value < predictor_thresholds['metadome_sintolerant']:
        return ['slightly intolerant', predictor_colors['mid_effect']]
    elif value < predictor_thresholds['metadome_neutral']:
        return ['neutral', predictor_colors['neutral']]
    elif value < predictor_thresholds['metadome_stolerant']:
        return ['slightly tolerant', predictor_colors['slightly_tolerant']]
    elif value < predictor_thresholds['metadome_tolerant']:
        return ['tolerant', predictor_colors['tolerant']]
    else:
        return ['highly tolerant', predictor_colors['highly_tolerant']]


def compute_pos_end(g_name):
    # in ajax.py return end pos of a specific variant
    # receives g_name as 216420460C>A or 76885812_76885817del
    match_object = re.search(r'^(\d+)[ATGC]>', g_name)
    if match_object is not None:
        return match_object.group(1)
    else:
        match_object = re.search(r'_(\d+)[di]', g_name)
        if match_object is not None:
            return match_object.group(1)
        else:
            # case of single nt dels ins dup
            match_object = re.search(r'^(\d+)[d]', g_name)
            if match_object is not None:
                return match_object.group(1)


def compute_start_end_pos(name):
    # slightly diffenent as above as start can differ
    # from VCF and HGVS - for variants > 1bp
    match_object = re.search(r'(\d+)_(\d+)[di]', name)
    if match_object is not None:
        return match_object.group(1), match_object.group(2)
    else:
        match_object = re.search(r'^(\d+)[ATGC]>', name)
        if match_object is not None:
            return match_object.group(1), match_object.group(1)
        else:
            # single nt del or delins
            match_object = re.search(r'^(\d+)[d]', name)
            if match_object is not None:
                return match_object.group(1), match_object.group(1)
            else:
                # case where NM wt disagree with genomic wt
                if re.search(r'^\d+=', name):
                    return '-1', '-1'


def danger_panel(var, warning):  # to be used in create_var_vv
    begin_txt = 'VariantValidator error: '
    if var == '':
        begin_txt = ''
    return """
    <div class="w3-margin w3-panel w3-pale-red w3-leftbar w3-display-container">
        <span class="w3-button w3-ripple w3-display-topright w3-large" onclick="this.parentElement.style.display=\'none\'">X</span>
        <p><span><strong>{0}{1}<br/>{2}</strong></span><br /></p>
    </div>
    """.format(begin_txt, var, warning)


def info_panel(text, var='', id_var='', color_class='w3-sand'):
    # to print general info do not send var neither id_var
    # Newly created variant:
    c = 'c.'
    if re.search(r'N[MR]_', var):
        c = ''
    link = ''
    if var != '':
        link = """
        <a href="{0}" target="_blank" title="Go to the variant page">{1}{2}</a>
        """.format(
                    url_for('api.variant', variant_id=id_var, caller='browser'), c, var
                )
    return """
    <div class="w3-margin w3-panel {0} w3-leftbar w3-display-container">\
        <span class="w3-button w3-ripple w3-display-topright w3-large" onclick="this.parentElement.style.display=\'none\'">X</span>
        <p><span><strong>{1}{2}<br/></strong></span><br /></p>
    </div>
    """.format(color_class, text, link)


def get_vv_api_url():
    # try remote VV rest api and if not functional, switch on local
    try:
        hello = json.loads(http.request(
            'GET',
            urls['variant_validator_api_hello']).data.decode('utf-8')
        )
        if hello['status'] == "hello_world":
            return urls['variant_validator_api']
        else:
            raise Exception
    except Exception:
        try:
            print(
                'VV looks down - trying to switch on rescue docker {}'
                .format(urls['variant_validator_api_hello_backup'])
            )
            hello = json.loads(http.request(
                'GET',
                urls['variant_validator_api_hello_backup'])
                    .data.decode('utf-8')
            )
            if hello['status'] == "hello_world":
                return urls['variant_validator_api_backup']
            else:
                raise Exception
            # return urls['variant_validator_api_backup']
        except Exception:
            send_error_email(
                prepare_email_html(
                    'MobiDetails VariantValidator error',
                    '<p>VariantValidator looks down!!<br /> - from {0}</p>'
                    .format(
                        os.path.basename(__file__)
                    )
                ),
                '[MobiDetails - VariantValidator Error]'
            )
    return None


def vv_internal_server_error(caller, vv_data, vv_key_var):
    if 'message' in vv_data and vv_data['message'] == 'Internal Server Error':
        if caller == 'browser':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    """
                    <p>VariantValidator returned an Internal Server Error for {0} no Flag in json response</p>
                    """.format(vv_key_var)
                ),
                '[MobiDetails - VariantValidator Error]'
            )
            return danger_panel(
                vv_key_var,
                """
                VariantValidator returned an Internal Server Error. Sorry for the inconvenience. Please retry later.
                """
            )
        elif caller == 'cli':
            return {'mobidetails_error': 'VariantValidator returned an Internal Server Error for {0}'.format(vv_key_var)}
    return 'vv_ok'


def create_var_vv(
        vv_key_var, gene, acc_no, new_variant,
        original_variant, vv_data, caller, db, g):
    vf_d = {}
    # deal with various warnings
    # docker up?
    if caller == 'browser':
        print('Creating variant: {0} - {1}'.format(gene, original_variant))
    vv_error = vv_internal_server_error(caller, vv_data, vv_key_var)
    if vv_error != 'vv_ok':
        return vv_error
    if 'flag' not in vv_data:
        if caller == 'browser':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    """
                    <p>VariantValidator looks down!! no Flag in json response</p>
                    """
                ),
                '[MobiDetails - VariantValidator Error]'
            )
            return danger_panel(
                vv_key_var,
                """
                VariantValidator looks down!! Sorry for the inconvenience. Please retry later.
                """
            )
        elif caller == 'cli':
            return {'mobidetails_error': 'VariantValidator looks down'}
    elif vv_data['flag'] is None:
        if caller == 'browser':
            return danger_panel(
                vv_key_var,
                """
                VariantValidator could not process your variant, please check carefully your nomenclature!
                Of course this may also come from the gene and not from you!
                """
            )
        elif caller == 'cli':
            return {
                'mobidetails_error':
                """
                No flag in VariantValidator answer. Please check your variant.
                """
            }
    elif re.search('Major error', vv_data['flag']):
        if caller == 'browser':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    """
                    <p>A major validation error has occurred in VariantValidator.</p>
                    """
                ),
                '[MobiDetails - VariantValidator Error]'
            )
            return danger_panel(
                vv_key_var,
                """
                A major validation error has occurred in VariantValidator. VV Admin have been made aware of the issue.
                Sorry for the inconvenience. Please retry later.
                """
            )
        elif caller == 'cli':
            return {
                'mobidetails_error':
                'A major validation error has occurred in VariantValidator'
            }
    # print(vv_data['flag'])
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if 'validation_warning_1' in vv_data:
        first_level_key = 'validation_warning_1'
    if vv_key_var in vv_data:
        first_level_key = vv_key_var

    if vv_data['flag'] == 'intergenic':
        first_level_key = 'intergenic_variant_1'
    else:
        for key in vv_data:
            # if vv modified the nomenclature
            if re.search('{}'.format(acc_no), key) and \
                    vv_data[key]['submitted_variant'] == vv_key_var:
                vv_key_var = key
                var_obj = re.search(r':c\.(.+)$', key)
                vf_d['c_name'] = var_obj.group(1)
                first_level_key = key
                break
    try:
        print('First level key: {}'.format(first_level_key))
    except UnboundLocalError as e:
        if caller == 'browser':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    """
                    <p>Insertion failed for variant hg38 for {0} with args: {1}.
                    <br />The unknown error arised again.</p><p>{2}</p>
                    """.format(
                        vv_key_var,
                        e.args,
                        vv_data
                    )
                ),
                '[MobiDetails - MD variant creation Error]'
            )
            return danger_panel(
                vv_key_var,
                """
                An unknown error has been caught during variant creation with VariantValidator.<br />
                It may work if you try again.<br />I am aware of this bug and actively tracking it.
                """
            )
        elif caller == 'cli':
            return {
                'mobidetails_error':
                """
                An unknown error has been caught during variant creation with VariantValidator.
                It is possible that it works if you try again: {0}-{1}
                """.format(acc_no, gene)}

    if 'validation_warnings' in vv_data[first_level_key]:
        for warning in vv_data[first_level_key]['validation_warnings']:
            # print(vv_data[first_level_key])
            # print(warning)
            variant_regexp = regexp['variant']
            if re.search(r'RefSeqGene record not available', warning):
                vf_d['ng_name'] = 'NULL'
            elif re.search(r'automapped to NC_0000', warning):
                continue
            elif re.search(
                    rf'automapped to {acc_no}:c\.{variant_regexp}',
                    warning):
                match_obj = re.search(
                    rf'automapped to {acc_no}:(c\.{variant_regexp})',
                    warning
                )
                if match_obj:
                    return_text = "VariantValidator reports that your variant should be {0} instead of {1}".format(
                        match_obj.group(1), original_variant
                    )
                    if caller == 'browser':
                        return danger_panel(vv_key_var, return_text)
                    elif caller == 'cli':
                        return {'mobidetails_error': '{}'.format(return_text)}
                else:
                    danger_panel(vv_key_var, warning)
            elif re.search('normalized', warning):
                match_obj = re.search(
                    rf'normalized to ({acc_no}:c\..+)',
                    warning
                )
                if match_obj and \
                        match_obj.group(1) == vv_key_var:
                    next
                elif caller == 'browser':
                    return danger_panel(vv_key_var, warning)
                elif caller == 'cli':
                    return {'mobidetails_error': '{}'.format(warning)}
            elif re.search('A more recent version of', warning) or \
                    re.search('LRG_', warning) or \
                    re.search('Whitespace', warning):
                next
            elif re.search(r'is not HGVS-compliant: Instead', warning):
                match_obj = re.search(r'^(.+is not HGVS-compliant)', warning)
                message = warning
                if match_obj:
                    message = "{0}. Your variant is not located inside the gene genomic boundaries, therefore MD cannot treat it.".format(match_obj.group(1))
                if caller == 'browser':
                    return danger_panel(vv_key_var, message)
                elif caller == 'cli':
                    return {'mobidetails_error': '{}'.format(message)}
            else:
                if 'Removing redundant reference bases from variant description' in warning:
                    continue
                if 'cannot be mapped directly to genome build' in warning:
                    # test whether we still have mapping onto
                    # both genome versions
                    ncbi_chrom_regexp = regexp['ncbi_chrom']
                    # print(vv_data[vv_key_var]['primary_assembly_loci']['hg19']['hgvs_genomic_description'])
                    # print(vv_data[vv_key_var]['primary_assembly_loci']['hg38']['hgvs_genomic_description'])
                    if 'primary_assembly_loci' in vv_data[vv_key_var]\
                        and \
                        'hg19' in \
                        vv_data[vv_key_var]['primary_assembly_loci']\
                        and \
                        'hgvs_genomic_description' in \
                        vv_data[vv_key_var]['primary_assembly_loci']['hg19'] \
                        and \
                        re.search(
                            rf'{ncbi_chrom_regexp}:g\.(.+)$',
                            vv_data[vv_key_var]['primary_assembly_loci']['hg19']['hgvs_genomic_description']
                        ) and \
                        'hg38' in \
                        vv_data[vv_key_var]['primary_assembly_loci'] \
                        and \
                        'hgvs_genomic_description' in \
                        vv_data[vv_key_var]['primary_assembly_loci']['hg38'] \
                        and \
                        re.search(
                            rf'{ncbi_chrom_regexp}:g\.(.+)$',
                            vv_data[vv_key_var]['primary_assembly_loci']['hg38']['hgvs_genomic_description']
                            ):
                        # we have a correct mapping
                        # print('going out')
                        break
                if caller == 'browser':
                    if len(
                        vv_data[first_level_key]['validation_warnings']
                    ) > 1:
                        return danger_panel(
                            vv_key_var,
                            '<br />'.join(
                                vv_data[first_level_key]['validation_warnings']
                            )
                        )
                    else:
                        return danger_panel(vv_key_var, warning)
                elif caller == 'cli':
                    if len(
                        vv_data[first_level_key]['validation_warnings']
                    ) > 1:
                        return {
                            'mobidetails_error':
                            ' '.join(
                                vv_data[first_level_key]['validation_warnings']
                            )
                        }
                    else:
                        return {'mobidetails_error':  '{}'.format(warning)}
    vv_variant_data_check = check_vv_variant_data(vv_key_var, vv_data)
    # if check_vv_variant_data(vv_key_var, vv_data) is not True:
    if vv_variant_data_check is not True:
        if caller == 'browser':
            vv_warning = return_vv_validation_warnings(vv_data)
            if vv_warning == '':
                send_error_email(
                    prepare_email_html(
                        'MobiDetails error',
                        """
                        <p>VV check failed for variant {0} with args: {1} {2}.
                        """.format(
                            vv_key_var,
                            vv_data,
                            vv_variant_data_check
                        )
                    ),
                    '[MobiDetails - MD variant creation Error: VV check]'
                )
                return danger_panel(
                    vv_key_var,
                    """
                    VariantValidator did not return a valid value for this variant. An admin has been warned. {0}
                    """.format(vv_variant_data_check)
                )
            else:
                return danger_panel(
                    vv_key_var,
                    """
                    VariantValidator did not return a valid value for this variant: {0} {1}
                    """.format(vv_warning, vv_variant_data_check)
                )
        elif caller == 'cli':
            return {
                'mobidetails_error': "VariantValidator did not return a valid value for the variant {0} {1}".format(vv_key_var, vv_variant_data_check)}
    genome = 'hg38'
    # hg38
    try:
        hg38_d = get_genomic_values('hg38', vv_data, vv_key_var)
        if 'mobidetails_error' in hg38_d:
            if caller == 'browser':
                return danger_panel(
                    'MobiDetails error',
                    hg38_d['mobidetails_error']
                )
            elif caller == 'cli':
                return hg38_d
    except Exception:
        # print(vv_data)
        error_text = "Transcript {0} for gene {1} does not seem to map correctly to hg38. Currently, MobiDetails requires proper mapping on hg38 and hg19. It is therefore impossible to create a variant.".format(acc_no, gene)
        if caller == 'browser':
            return danger_panel(
                vv_key_var,
                error_text
            )
        elif caller == 'cli':
            return {'mobidetails_error':  error_text}
    # check again if variant exist for this transcript
    curs.execute(
        """
        SELECT id, c_name AS nm
        FROM variant_feature
        WHERE c_name = %s
            AND refseq = %s
        """,
        (new_variant.replace("c.", ""), acc_no)
    )
    res = curs.fetchone()
    if res is not None:
        # now returns only id
        return res['id']
    try:
        hg19_d = get_genomic_values('hg19', vv_data, vv_key_var)
        if 'mobidetails_error' in hg19_d:
            if caller == 'browser':
                return danger_panel(
                    'MobiDetails error',
                    hg19_d['mobidetails_error']
                )
            elif caller == 'cli':
                return hg19_d
    except Exception:
        error_text = """
        Transcript {0} for gene {1} does not seem to map correctly to hg19.
        Currently, MobiDetails requires proper mapping on hg38 and hg19.
        It is therefore impossible to create a variant.
        """.format(acc_no, gene)
        if caller == 'browser':
            return danger_panel(
                vv_key_var,
                error_text
            )
        elif caller == 'cli':
            return {'mobidetails_error': error_text}
    positions = compute_start_end_pos(hg38_d['g_name'])
    if positions[0] == '-1':
        error_text = """
        The wild-type nucleotide is discordant between the RefSeq transcript and the human genome.
        It may occur with frequent variants.
        As the genome reference would be equal to the variant nucleotide ({0}), it is therefore impossible to generate correct annotations.
        """.format(hg38_d['g_name'])
        if caller == 'browser':
            return danger_panel(
                vv_key_var,
                error_text
            )
        elif caller == 'cli':
            return {'mobidetails_error': error_text}
    if 'c_name' not in vf_d:
        var_obj = re.search(r'^c?\.?(.+)$', new_variant)
        vf_d['c_name'] = var_obj.group(1)
    if 'ng_name' not in vf_d:
        ng_name_obj = re.search(
            r':g\.(.+)$',
            vv_data[vv_key_var]['hgvs_refseqgene_variant']
        )
        if ng_name_obj:
            vf_d['ng_name'] = ng_name_obj.group(1)
        else:
            vf_d['ng_name'] = 'NULL'
    # dna_type
    if re.search('>', vf_d['c_name']):
        vf_d['dna_type'] = 'substitution'
        vf_d['variant_size'] = 1
    elif re.search(r'del.*ins', vf_d['c_name']):
        vf_d['dna_type'] = 'indel'
    elif re.search('dup', vf_d['c_name']):
        vf_d['dna_type'] = 'duplication'
    elif re.search('ins', vf_d['c_name']):
        vf_d['dna_type'] = 'insertion'
    elif re.search('del', vf_d['c_name']):
        vf_d['dna_type'] = 'deletion'
    elif re.search('inv', vf_d['c_name']):
        vf_d['dna_type'] = 'inversion'
    elif re.search('=', vf_d['c_name']):
        error_text = """
        Reference should not be equal to alternative to define a variant.
        """
        if caller == 'browser':
            return danger_panel(
                vv_key_var,
                error_text
            )
        elif caller == 'cli':
            return {'mobidetails_error': error_text}
    else:
        error_text = 'No proper DNA type found for the variant.'
        if caller == 'browser':
            return danger_panel(
                vv_key_var,
                error_text
            )
        elif caller == 'cli':
            return {'mobidetails_error':error_text}
    if 'variant_size' not in vf_d:
        if not re.search('_', vf_d['c_name']):
            # one bp del or dup
            vf_d['variant_size'] = 1
        else:
            vf_d['variant_size'] = int(positions[1]) - int(positions[0]) + 1

    # we need strand later
    curs.execute(
        """
        SELECT strand
        FROM gene
        WHERE gene_symbol = %s
            AND refseq = %s
        """,
        (gene, acc_no)
    )
    res_strand = curs.fetchone()
    if res_strand is None:
        error_text = """
        No strand for gene {}, impossible to create a variant, please contact us
        """.format(gene)
        if caller == 'browser':
            return danger_panel(
                vv_key_var,
                error_text
            )
        elif caller == 'cli':
            return {'mobidetails_error': error_text}

    # p_name
    p_obj = re.search(
        r':p\.\((.+)\)$',
        vv_data[vv_key_var]['hgvs_predicted_protein_consequence']['tlr']
    )
    if p_obj:
        vf_d['p_name'] = p_obj.group(1)
        if re.search(r'Ter$', vf_d['p_name']):
            vf_d['prot_type'] = 'nonsense'
        elif re.search(r'fsTer\d+', vf_d['p_name']):
            vf_d['prot_type'] = 'frameshift'
        elif re.search(r'\w{3}\d+=', vf_d['p_name']):
            vf_d['prot_type'] = 'silent'
        elif re.search(r'^\?$', vf_d['p_name']):
            vf_d['prot_type'] = 'unknown'
        elif re.search(r'^Met1\?$', vf_d['p_name']):
            vf_d['prot_type'] = 'start codon'
        elif re.search(r'ext', vf_d['p_name']):
            vf_d['prot_type'] = 'stop codon'
        elif re.search(r'_\w{3}\d+del', vf_d['p_name']) or \
                re.search(r'^\w{3}\d+del', vf_d['p_name']):
            vf_d['prot_type'] = 'inframe deletion'
        elif re.search(r'_\w{3}\d+dup', vf_d['p_name']) or \
                re.search(r'^\w{3}\d+dup', vf_d['p_name']):
            vf_d['prot_type'] = 'inframe duplication'
        elif re.search(r'_\w{3}\d+ins', vf_d['p_name']):
            vf_d['prot_type'] = 'inframe insertion'
        else:
            var_obj = re.search(r'^(\w{3})\d+(\w{3})$', vf_d['p_name'])
            if var_obj.group(1) != var_obj.group(2):
                vf_d['prot_type'] = 'missense'
            else:
                vf_d['prot_type'] = 'unknown'
    else:
        vf_d['p_name'] = '?'
        vf_d['prot_type'] = 'unknown'

    # deal with +1,+2 etc
    vf_d['rna_type'] = 'neutral inferred'
    if re.search(r'\d+[\+-][12][^\d]', vf_d['c_name']):
        vf_d['rna_type'] = 'altered inferred'
    # exons pos, etc - based on hg38
    # VV2 here we basically get "variant_exonic_positions"
    # we need the NCBI hg38 chrom
    # "NC_000004.12": {
    #     "end_exon": "21",
    #     "start_exon": "20i"
    # },
    ncbi_chr = get_ncbi_chr_name(db, 'chr{}'.format(hg38_d['chr']), genome)
    if ncbi_chr[0] not in vv_data[vv_key_var]['variant_exonic_positions']:
        # error
        if caller == 'browser':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    """
                    <p>Insertion failed for variant features for {0} with args no chr:
                    {1}</p>
                    """.format(
                        vv_key_var,
                        ncbi_chr[0]
                    )
                ),
                '[MobiDetails - MD variant creation Error]'
            )
            return danger_panel(
                'MobiDetails error {}'.format(vv_key_var),
                """
                Sorry, an issue occured with the variant mapping. An admin has been warned.
                """
            )
        elif caller == 'cli':
            return {
                'mobidetails_error':
                """
                Sorry, an issue occured with the variant mapping for {}.
                """.format(vv_key_var)
            }

    vf_d['start_segment_type'] = get_segment_type_from_vv(vv_data[vv_key_var]['variant_exonic_positions'][ncbi_chr[0]]['start_exon'])
    vf_d['start_segment_number'] = get_segment_number_from_vv(vv_data[vv_key_var]['variant_exonic_positions'][ncbi_chr[0]]['start_exon'])
    vf_d['end_segment_type'] = get_segment_type_from_vv(vv_data[vv_key_var]['variant_exonic_positions'][ncbi_chr[0]]['end_exon'])
    vf_d['end_segment_number'] = get_segment_number_from_vv(vv_data[vv_key_var]['variant_exonic_positions'][ncbi_chr[0]]['end_exon'])
    if vf_d['start_segment_type'] == 'segment_type_error' or \
            vf_d['end_segment_type'] == 'segment_type_error' or \
            vf_d['start_segment_number'] == 'segment_number_error' or \
            vf_d['end_segment_number'] == 'segment_number_error':
        if caller == 'browser':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    """
                    <p>Insertion failed for variant features for {0} with args start_segment_type:
                    {1}-end_segment_type:{2}-start_segment_number:{3}-end_segment_number:{4}</p>
                    """.format(
                        vv_key_var,
                        vf_d['start_segment_type'],
                        vf_d['end_segment_type'],
                        vf_d['start_segment_number'],
                        vf_d['end_segment_number']
                    )
                ),
                '[MobiDetails - MD variant creation Error]'
            )
            return danger_panel(
                'MobiDetails error {}'.format(vv_key_var),
                """
                Sorry, an issue occured with the variant position and intron/exon definition. An admin has been warned
                """
            )
        elif caller == 'cli':
            return {
                'mobidetails_error':
                """
                Sorry, an issue occured with the variant position and intron/exon definition for {}
                """.format(vv_key_var)
            }
    if positions[0] != positions[1]:
        # get IVS name
        if vf_d['start_segment_type'] == 'intron':
            ivs_obj = re.search(
                r'^\d+([\+-]\d+)_\d+([\+-]\d+)(.+)$',
                vf_d['c_name']
            )
            if ivs_obj:
                vf_d['ivs_name'] = 'IVS{0}{1}_IVS{2}{3}{4}'.format(
                    vf_d['start_segment_number'],
                    ivs_obj.group(1),
                    vf_d['end_segment_number'],
                    ivs_obj.group(2),
                    ivs_obj.group(3)
                )
            else:
                ivs_obj = re.search(
                    r'^\d+([\+-]\d+)_(\d+)([^\+-].+)$',
                    vf_d['c_name']
                )
                if ivs_obj:
                    vf_d['ivs_name'] = 'IVS{0}{1}_{2}{3}'.format(
                        vf_d['start_segment_number'],
                        ivs_obj.group(1),
                        ivs_obj.group(2),
                        ivs_obj.group(3)
                    )
                else:
                    ivs_obj = re.search(
                        r'^(\d+)_\d+([\+-]\d+)(.+)$',
                        vf_d['c_name']
                    )
                    if ivs_obj:
                        vf_d['ivs_name'] = '{0}_IVS{1}{2}{3}'.format(
                            ivs_obj.group(1), vf_d['end_segment_number'],
                            ivs_obj.group(2), ivs_obj.group(3)
                        )
    else:
        # substitutions
        if vf_d['start_segment_type'] == 'intron':
            ivs_obj = re.search(r'^[\*-]?\d+([\+-]\d+)(.+)$', vf_d['c_name'])
            if ivs_obj:
                vf_d['ivs_name'] = 'IVS{0}{1}{2}'.format(
                    vf_d['start_segment_number'],
                    ivs_obj.group(1),
                    ivs_obj.group(2)
                )
            else:
                send_error_email(
                    prepare_email_html(
                        'MobiDetails error',
                        """
                        <p>Issue with gene segments definition {0} in md_utilities create_var_vv</p>
                        """.format(vv_key_var)
                    ),
                    '[MobiDetails - MD variant creation Error]'
                )
    if 'ivs_name' not in vf_d:
        vf_d['ivs_name'] = 'NULL'
    # ncbi_chr = get_ncbi_chr_name(db, 'chr{}'.format(hg38_d['chr']), genome)
    hg38_d['chr'] = ncbi_chr[0]
    record = get_value_from_tabix_file(
        'dbsnp', local_files['dbsnp']['abs_path'], hg38_d, vf_d
    )
    reg_chr = get_common_chr_name(db, ncbi_chr[0])
    hg38_d['chr'] = reg_chr[0]
    if isinstance(record, str):
        vf_d['dbsnp_id'] = 'NULL'
    else:
        match_object = re.search(r'RS=(\d+);', record[7])
        if match_object:
            pos_ref_list = re.split(',', record[3])
            pos_alt_list = re.split(',', record[4])
            if hg38_d['pos_ref'] in pos_ref_list and \
                    hg38_d['pos_alt'] in pos_alt_list:
                vf_d['dbsnp_id'] = match_object.group(1)
        # print(record[7])
    # get wt sequence using twobitreader module
    # 0-based
    if vf_d['variant_size'] < 50:
        x = int(positions[0])-26
        y = int(positions[1])+25
        # startbugfix david 20210216
        # del/dups on strand - could get bad sequences
        if res_strand['strand'] == '-' and \
            (vf_d['dna_type'] == 'indel' or
                vf_d['dna_type'] == 'deletion' or
                vf_d['dna_type'] == 'duplication'):
            pos_vcf = int(
                vv_data[vv_key_var]['primary_assembly_loci']
                [genome]['vcf']['pos']
            )
            if vf_d['dna_type'] == 'indel':
                pos_vcf -= 1
            x = pos_vcf - 25
            y = pos_vcf + int(vf_d['variant_size']) + 25
        # endbugfix
        genome = twobitreader.TwoBitFile(
            '{}.2bit'.format(
                local_files['human_genome_{}'.format(genome)]['abs_path']
            )
        )
        current_chrom = genome['chr{}'.format(hg38_d['chr'])]
        seq_slice = current_chrom[x:y].upper()
        # seq2 = current_chrom[int(positions[0])+1:int(positions[0])+2]
        # return seq2
        if res_strand['strand'] == '-':
            seq_slice = reverse_complement(seq_slice).upper()
        marker = 25 if vf_d['dna_type'] != 'insertion' else 26
        begin = seq_slice[:marker]
        middle = seq_slice[marker:len(seq_slice)-marker]
        end = seq_slice[-marker:]
        # substitutions
        if vf_d['dna_type'] == 'substitution':
            vf_d['wt_seq'] = "{0} {1} {2}".format(begin, middle, end)
            mt_obj = re.search(r'>([ATGC])$', vf_d['c_name'])
            vf_d['mt_seq'] = "{0} {1} {2}".format(begin, mt_obj.group(1), end)
        elif vf_d['dna_type'] == 'inversion':
            vf_d['wt_seq'] = "{0} {1} {2}".format(begin, middle, end)
            vf_d['mt_seq'] = "{0} {1} {2}".format(
                begin, reverse_complement(middle), end
            )
        elif vf_d['dna_type'] == 'indel':
            ins_obj = re.search(r'delins([ATGC]+)', vf_d['c_name'])
            exp_size = abs(len(middle)-len(ins_obj.group(1)))
            exp = ''
            for i in range(0, exp_size):
                exp += '-'
            if len(middle) > len(ins_obj.group(1)):
                vf_d['wt_seq'] = "{0} {1} {2}".format(begin, middle, end)
                vf_d['mt_seq'] = "{0} {1}{2} {3}".format(
                    begin, ins_obj.group(1), exp, end
                )
            else:
                vf_d['wt_seq'] = "{0} {1}{2} {3}".format(
                    begin, middle, exp, end
                )
                vf_d['mt_seq'] = "{0} {1} {2}".format(
                    begin, ins_obj.group(1), end
                )
        elif vf_d['dna_type'] == 'insertion':
            ins_obj = re.search(r'ins([ATGC]+)', vf_d['c_name'])
            exp = ''
            for i in range(0, len(ins_obj.group(1))):
                exp += '-'
            vf_d['wt_seq'] = "{0} {1} {2}".format(begin, exp, end)
            vf_d['mt_seq'] = "{0} {1} {2}".format(begin, ins_obj.group(1), end)
        elif vf_d['dna_type'] == 'deletion':
            vf_d['wt_seq'] = "{0} {1} {2}".format(begin, middle, end)
            exp = ''
            for i in range(0, vf_d['variant_size']):
                exp += '-'
            vf_d['mt_seq'] = "{0} {1} {2}".format(begin, exp, end)
        elif vf_d['dna_type'] == 'duplication':
            exp = ''
            for i in range(0, vf_d['variant_size']):
                exp += '-'
            vf_d['wt_seq'] = "{0} {1}{2} {3}".format(begin, middle, exp, end)
            vf_d['mt_seq'] = "{0} {1}{1} {2}".format(begin, middle, end)
    mobiuser = 'mobidetails'
    if caller == 'browser':
        if g.user is not None:
            mobiuser = g.user['username']
        vf_d['creation_user'] = get_user_id(mobiuser, db)
    elif caller == 'cli':
        vf_d['creation_user'] = g.user['id']

    today = datetime.datetime.now()
    vf_d['creation_date'] = '{0}-{1}-{2}'.format(
        today.strftime("%Y"), today.strftime("%m"), today.strftime("%d")
    )

    s = ", "
    # attributes =
    t = "', '"
    vf_d['gene_symbol'] = gene
    vf_d['refseq'] = acc_no
    insert_variant_feature = """
        INSERT INTO variant_feature ({0})
        VALUES ('{1}')
        RETURNING id
    """.format(
        s.join(vf_d.keys()),
        t.join(map(str, vf_d.values()))
    ).replace("'NULL'", "NULL")
    # insert_variant_feature = """
    # INSERT INTO variant_feature (gene_symbol, refseq, {0})
    # VALUES ('{1}', '{2}', '{3}')
    # RETURNING id
    # """.format(
    #     s.join(vf_d.keys()),
    #     gene,
    #     acc_no,
    #     t.join(map(str, vf_d.values()))
    # ).replace("'NULL'", "NULL")
    # print(insert_variant_feature)
    vf_id = ''
    try:
        curs.execute(insert_variant_feature)
        vf_id = curs.fetchone()[0]
    except Exception as e:
        if caller == 'browser':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    """
                    <p>Insertion failed for variant features for {0} with args {1}, {2}</p>
                    """.format(vv_key_var, e.args, insert_variant_feature)
                ),
                '[MobiDetails - MD variant creation Error]'
            )
            return danger_panel(
                'MobiDetails error {}'.format(vv_key_var),
                """
                Sorry, an issue occured with variant features. An admin has been warned
                """
            )
        elif caller == 'cli':
            return {
                'mobidetails_error':
                """
                Impossible to insert variant_features for {}
                """.format(vv_key_var)
            }
    insert_variant_38 = """
        INSERT INTO variant (feature_id, {0})
        VALUES ('{1}', '{2}')
    """.format(
        s.join(hg38_d.keys()),
        vf_id,
        t.join(map(str, hg38_d.values()))
    )
    try:
        curs.execute(insert_variant_38)
    except Exception as e:
        if caller == 'browser':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    """
                    <p>Insertion failed for variant hg38 for {0} with args: {1}, {2}</p>
                    """.format(vv_key_var, e.args, insert_variant_38)
                ),
                '[MobiDetails - MD variant creation Error]'
            )
            return danger_panel(
                'MobiDetails error {}'.format(vv_key_var),
                """
                Sorry, an issue occured with variant mapping in hg38. An admin has been warned
                """
            )
        elif caller == 'cli':
            return {
                'mobidetails_error':
                """
                Impossible to insert variant (hg38) for {}
                """.format(vv_key_var)
            }
    insert_variant_19 = """
        INSERT INTO variant (feature_id, {0})
        VALUES ('{1}', '{2}')
    """.format(
        s.join(hg19_d.keys()),
        vf_id,
        t.join(map(str, hg19_d.values()))
    )
    try:
        curs.execute(insert_variant_19)
    except Exception as e:
        if caller == 'browser':
            send_error_email(
                prepare_email_html(
                    'MobiDetails error',
                    """
                    <p>Insertion failed for variant hg19 for {0} with args {1}, {2}</p>
                    """.format(vv_key_var, e.args, insert_variant_19)
                ),
                '[MobiDetails - MD variant creation Error]'
            )
            return danger_panel(
                'MobiDetails error {}'.format(vv_key_var),
                """Sorry, an issue occured with variant mapping in hg19. An admin has been warned"""
            )
        elif caller == 'cli':
            return {
                'mobidetails_error':
                """Impossible to insert variant (hg19) for {}""".format(vv_key_var)}
    db.commit()
    return vf_id


def get_segment_type_from_vv(vv_expr):
    if re.match(r'^\d+i$', vv_expr):
        return 'intron'
    elif re.match(r'^\d+$', vv_expr):
        return 'exon'
    else:
        return 'segment_type_error'


def get_segment_size_from_vv_cigar(cigar):
    match_obj = re.search(r'^(\d+)=', cigar)
    if match_obj:
        return str(match_obj.group(1))
    else:
        return 'cigar_error'


def get_positions_dict_from_vv_json(gene_symbol, transcript, ncbi_chr, exon_number):
    # we will find the exon start and end in the VV json file
    # print(ncbi_chr)
    # print(exon_number)
    try:
        json_file = open('{0}{1}.json'.format(
            local_files['variant_validator']['abs_path'],
            gene_symbol
        ))
    except IOError:
        # print('file_not_found_error')
        return 'file_not_found_error'
    vv_json = json.load(json_file)
    positions = {
        'number': int(exon_number),
        'gene_symbol': gene_symbol,
        'refseq': transcript
    }
    for vv_transcript in vv_json['transcripts']:
        if vv_transcript['reference'] == transcript:
            if ncbi_chr in vv_transcript['genomic_spans']:
                # get strand
                strand = vv_transcript['genomic_spans'][ncbi_chr]['orientation']
                # we loop on exons
                for exon in vv_transcript['genomic_spans'][ncbi_chr]['exon_structure']:
                    if str(exon['exon_number']) == str(exon_number):
                        # print('exon')
                        if strand == 1:
                            positions['segment_start'] = str(exon['genomic_start'])
                            positions['segment_end'] = str(exon['genomic_end'])
                        else:
                            positions['segment_start'] = str(exon['genomic_end'])
                            positions['segment_end'] = str(exon['genomic_start'])
                        positions['segment_size'] = get_segment_size_from_vv_cigar(exon['cigar'])
                        if positions['segment_size'] != 'cigar_error' and \
                                re.search(r'^\d+$', positions['segment_start']) and \
                                re.search(r'^\d+$', positions['segment_start']):
                            json_file.close()
                            return positions
                        else:
                            json_file.close()
                            return 'positions_error'
    json_file.close()
    return 'transcript_error'


def get_segment_number_from_vv(vv_expr):
    match_obj = re.search(r'^(\d+)i?$', vv_expr)
    if match_obj:
        return match_obj.group(1)
    else:
        return 'segment_number_error'


def get_genomic_transcript_positions_from_vv_json(gene_symbol, transcript, ncbi_chr, strand):
    try:
        json_file = open('{0}{1}.json'.format(
            local_files['variant_validator']['abs_path'],
            gene_symbol
        ))
    except IOError:
        # print('file_not_found_error')
        return 'file_not_found_error'
    vv_json = json.load(json_file)
    start = end = vv_strand = None
    for vv_transcript in vv_json['transcripts']:
        if vv_transcript['reference'] == transcript:
            if 'genomic_spans' in vv_transcript and \
                    ncbi_chr in vv_transcript['genomic_spans']:
                if 'start_position' in vv_transcript['genomic_spans'][ncbi_chr] and \
                        'end_position' in vv_transcript['genomic_spans'][ncbi_chr] and \
                        'orientation' in vv_transcript['genomic_spans'][ncbi_chr]:
                    start = vv_transcript['genomic_spans'][ncbi_chr]['start_position']
                    end = vv_transcript['genomic_spans'][ncbi_chr]['end_position']
                    vv_strand = '+' if vv_transcript['genomic_spans'][ncbi_chr]['orientation'] == 1 else '-'
                    if vv_strand == strand:
                        return start, end
                    else:
                        send_error_email(
                            prepare_email_html(
                                'MobiDetails error',
                                """
                                <p>Strand does not match between VV and MD for {0}({1})</p>
                                """.format(
                                    transcript,
                                    gene_symbol
                                )
                            ),
                            '[MobiDetails - Strand Error]'
                        )
                        return -2, -2
    return -1, -1


def get_genomic_values(genome, vv_data, vv_key_var):
    if vv_data[vv_key_var]['primary_assembly_loci'][genome]:
        g_name_obj = re.search(
            r':g\.(.+)$',
            vv_data[vv_key_var]['primary_assembly_loci'][genome]['hgvs_genomic_description']
        )
        chr_obj = re.search(
            r'chr([\dXYM]{1,2})$',
            vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['chr']
        )
        if len(
            vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['ref']
        ) > 49 or \
            len(
            vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['alt']
        ) > 49:
            # flash('MobiDetails currently only accepts variants of length
            #  < 50 bp (SNVs ans small insertions/deletions', 'w3-pale-red')
            # flash is only useful if we return a new page
            # which is not the case here
            return {
                'mobidetails_error':
                """
                MobiDetails currently only accepts variants of length < 50 bp (SNVs ans small insertions/deletions)
                """
            }
        return {
            'genome_version': genome,
            'g_name': g_name_obj.group(1),
            'chr': chr_obj.group(1),
            'pos': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['pos'],
            'pos_ref': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['ref'],
            'pos_alt': vv_data[vv_key_var]['primary_assembly_loci'][genome]['vcf']['alt']
        }


def check_vv_variant_data(vv_key_var, vv_data):
    # checks whether a variant VV json contains all the required fields
    # but if VV automapped, vv_key_var won't be found anymore
    # need to get at least the right transcript
    if vv_key_var not in vv_data:
        variant_regexp = regexp['variant']
        ncbi_transcript_regexp = regexp['ncbi_transcript']
        nm_match = re.search(rf'({ncbi_transcript_regexp}):c\.{variant_regexp}', vv_key_var)
        if nm_match:
            current_nm = nm_match.group(1)
            for vv_key in vv_data:
                vv_nm_match = re.search(rf'{current_nm}:c\.{variant_regexp}', vv_key)
                if vv_nm_match:
                    vv_key_var = vv_key
    if vv_key_var in vv_data:
        if 'primary_assembly_loci' not in vv_data[vv_key_var] or \
                'hg38' not in vv_data[vv_key_var]['primary_assembly_loci']:
            return 'The variant does not seem to map properly on hg38, which is mandatory for MD to treat it.'
        if 'hg19' not in vv_data[vv_key_var]['primary_assembly_loci']:
            return 'The variant does not seem to map properly on hg19, which is mandatory for MD to treat it.'
        if 'hgvs_genomic_description' not in vv_data[vv_key_var]['primary_assembly_loci']['hg38'] or \
                'hgvs_genomic_description' not in vv_data[vv_key_var]['primary_assembly_loci']['hg19']:
            return 'The variant is lacking proper genomic description in the variant validation.'
        if 'vcf' not in vv_data[vv_key_var]['primary_assembly_loci']['hg38'] or \
                'vcf' not in vv_data[vv_key_var]['primary_assembly_loci']['hg19']:
            return 'The variant is lacking VCF description in the variant validation.'
        if 'chr' not in vv_data[vv_key_var]['primary_assembly_loci']['hg38']['vcf'] or \
                'chr' not in vv_data[vv_key_var]['primary_assembly_loci']['hg19']['vcf']:
            return 'The variant is lacking chr description in the variant validation.'
        if 'pos' not in vv_data[vv_key_var]['primary_assembly_loci']['hg38']['vcf'] or \
                'pos' not in vv_data[vv_key_var]['primary_assembly_loci']['hg19']['vcf']:
            return 'The variant is lacking position description in the variant validation.'
        if 'ref' not in vv_data[vv_key_var]['primary_assembly_loci']['hg38']['vcf'] or \
                'ref' not in vv_data[vv_key_var]['primary_assembly_loci']['hg19']['vcf']:
            return 'The variant is lacking reference description in the variant validation.'
        if 'alt' not in vv_data[vv_key_var]['primary_assembly_loci']['hg38']['vcf'] or \
                'alt' not in vv_data[vv_key_var]['primary_assembly_loci']['hg19']['vcf']:
            return 'The variant is lacking alternative description in the variant validation.'
        if 'hgvs_refseqgene_variant' not in vv_data[vv_key_var]:
            return 'The variant is lacking RefSeqGene description in the variant validation.'
        if 'hgvs_predicted_protein_consequence' not in vv_data[vv_key_var]:
            return 'The variant is lacking protein description in the variant validation.'
        if 'tlr' not in vv_data[vv_key_var]['hgvs_predicted_protein_consequence']:
            return 'The variant is lacking protein description in the variant validation.'
        if 'variant_exonic_positions' not in vv_data[vv_key_var]:
            return 'The variant is lacking exonic description in the variant validation.'
        else:
            ncbi_chrom_regexp = regexp['ncbi_chrom']
            variant_regexp = regexp['variant']
            match_obj = re.search(
                rf'^({ncbi_chrom_regexp}):g\.{variant_regexp}$',
                vv_data[vv_key_var]['primary_assembly_loci']['hg38']['hgvs_genomic_description']
            )
            if match_obj:
                ncbi_chr = match_obj.group(1)
                if ncbi_chr not in vv_data[vv_key_var]['variant_exonic_positions']:
                    return 'The variant is lacking chromosomic description in the variant validation.'
                if 'start_exon' not in vv_data[vv_key_var]['variant_exonic_positions'][ncbi_chr] or \
                        'end_exon' not in vv_data[vv_key_var]['variant_exonic_positions'][ncbi_chr]:
                    return 'The variant is lacking exonic description in the variant validation.'
        return True
    return False


def return_vv_validation_warnings(vv_data):
    # when check_vv_variant_data is False, check if errors need to be returned
    # we need to deal with most errors here, e.g.:
    # - Variant reference (G) does not agree with reference sequence (C)
    # - Using a transcript reference sequence to specify a variant position that
    # lies outside of the reference sequence is not HGVS-compliant
    # - base start position must be <= end position
    # - lacking characters
    for key in vv_data:
        if key == 'validation_warning_1':
            for field in vv_data[key]:
                if field == 'validation_warnings':
                    for warning in vv_data[key][field]:
                        if re.search('does not agree with reference sequence', warning):
                            return warning
                        if re.search('base start position must be <= end position:', warning):
                            return warning
                        if re.search('Removing redundant reference bases from variant description', warning):
                            return warning
                        if re.search('expected one of', warning):
                            return warning
                        if re.search('end of input', warning):
                            return warning
                        if re.search('is not formatted following the HGVS guidelines', warning):
                            return warning
                        if re.search('Variant coordinate is out of the bound of CDS region', warning):
                            return warning
                        if re.search('insertion length must be', warning):
                            return warning
                        if re.search('start or end or both are beyond the bounds of transcript record', warning):
                            return warning
                        if re.search('base start position must be <= end position', warning):
                            return warning
                        if re.search('The given coordinate is outside the bounds of the reference sequence.', warning):
                            return warning
                        if re.search('Interval end position', warning):
                            return warning
                        match_obj = re.search('(Using a transcript reference sequence to specify a variant position that lies outside of the reference sequence is not HGVS-compliant):.*', warning)
                        if match_obj:
                            return match_obj.group(1)
    return ''


def prepare_email_html(title, message, send_url=True):
    if send_url is False:
        return render_template(
            'md/email.html',
            title=title,
            message=message,
            url=''
        )
    else:
        return render_template(
            'md/email.html',
            title=title,
            message=message,
            url=request.base_url
        )


def send_email(message, mail_object, receiver, bcc_receiver=None):
    if "MAIL_USERNAME" in app.config:
        msg = Message(
            mail_object,
            sender=app.config["MAIL_USERNAME"],
            recipients=receiver,
            bcc=bcc_receiver
        )
        msg.html = message
        mail.send(msg)


def send_error_email(message, mail_object):
    if "MAIL_USERNAME" in app.config:
        msg = Message(
            mail_object,
            # sender=params['mail_username'],
            sender=app.config["MAIL_USERNAME"],
            # recipients=[params['mail_error_recipient']]
            recipients=[app.config["MAIL_ERROR_RECIPIENT"]]
        )
        msg.html = message
        mail.send(msg)


def maxentscan(w, y, seq, scantype, a=0, x=26):
    # takes a sequence and positions as input
    # returns a list of sequences
    # a = window slider
    # x = pos 1st nt / mutation (26)
    # y = len(var)
    # z = len(resulting seq) must be = 9|23
    # w = len(seq required) = 9|23
    z = w
    seq = seq.replace(' ', '').replace('-', '')
    pos1 = pos2 = 0
    seqs = []
    seqs_html = []
    while z == w and \
            pos2 < len(seq):
        pos1 = x - w + a
        pos2 = pos1 + w - 1
        z = (pos2 - pos1 + 1)
        # get substring
        interest_seq = '{}\n'.format(seq[pos1-1:pos2])
        seqs.append(interest_seq)
        # we need to html highlight the mutant sequence so to retrieve it here
        # r is the beginning of the subseq and defined as
        # ((len(seq required 4 maxent; 9 or 23) - window position - 1) -
        # (len(var) -2)))
        # s is the end of the substring being r + len(var)
        # limitation for delins => the size is the size of the deleted sequence
        r = (w - a - 1) - (y - 2)
        s = r + y
        # we need to remap r and s if < 0
        if (r < 0):
            r = 0
            s = s + abs(r)
            if s < 0:
                s = 0
        # print('r: {0};s: {1}'.format(r, s))
        seqs_html.append(
            '{0}<span class="w3-text-red"><strong>{1}</strong></span>{2}'
            .format(interest_seq[:r], interest_seq[r:s], interest_seq[s:])
        )
        a += 1
    # create temp file and launch maxentscan
    tf = tempfile.NamedTemporaryFile()
    # print(tf.name)
    tf.write(bytes(''.join(seqs), encoding='utf-8'))
    tf.seek(0)
    # cannot figure out why the above line is mandatory
    # but without it the file is empty
    # print(tf.read())
    result = subprocess.run(
        [
            ext_exe['perl'],
            '{}'.format(
                ext_exe[
                    'maxentscan{}'.format(scantype)
                ]
            ),
            '{}'.format(tf.name)
        ],
        stdout=subprocess.PIPE
    )
    if result.returncode == 0:
        return [str(result.stdout, 'utf-8'), seqs_html]
    else:
        return ['There has been an error while processing MaxEntScan', '']


def select_mes_scores(scoreswt, html_wt, scoresmt, html_mt, cutoff, threshold):
    # get 2 lists of wt and mt scores, returns only those
    # which have a 15% variation
    signif_scores = {}
    for i in range(len(scoreswt)):
        # a score is
        # CAAATTCTG\t-17.88
        if i < len(scoresmt):
            wt = scoreswt[i].split()
            mt = scoresmt[i].split()
            if len(wt) == 2 and \
                    len(mt) == 2 and \
                    wt[1] != '' and \
                    mt[1] != '':
                if float(wt[1]) != 0:
                    variation = (
                        float(mt[1]) - float(wt[1])
                    ) / abs(float(wt[1]))
                else:
                    variation = float(wt[1])
                if abs(variation) >= float(cutoff) and \
                        (float(mt[1]) > threshold or
                            float(wt[1]) > threshold):
                    # get span with exon/intron depending on score5 or score 3
                    html_seqwt = html_seqmt = ''
                    if len(wt[0]) == 9:
                        # score 5
                        html_seqwt = '<strong>{0}</strong>{1}'.format(
                            wt[0][:3], wt[0][3:].lower()
                        )
                        html_seqmt = '<strong>{0}</strong>{1}'.format(
                            mt[0][:3], mt[0][3:].lower()
                        )
                    else:
                        html_seqwt = '{0}<strong>{1}</strong>'.format(
                            wt[0][:20].lower(), wt[0][20:]
                        )
                        html_seqmt = '{0}<strong>{1}</strong>'.format(
                            mt[0][:20].lower(), mt[0][20:]
                        )
                    signif_scores[i] = [
                        wt[0], wt[1], mt[0], mt[1], round(variation*100, 2),
                        html_wt[i], html_seqwt, html_mt[i], html_seqmt
                    ]
    return signif_scores


def get_maxent_natural_sites_scores(chrom, strand, scantype, positions):
    # 1st we need the sequences and therefore determine
    # start and end of interest
    segment_start = int(positions['segment_start'])
    segment_end = int(positions['segment_end'])
    x = y = None
    if scantype == 3:
        if strand == '+':
            x = segment_start-21
            y = segment_start+2
        else:
            x = segment_start-3
            y = segment_start+20

    else:
        if strand == '+':
            x = segment_end-3
            y = segment_end+6
        else:
            x = segment_end-7
            y = segment_end+2

    genome = twobitreader.TwoBitFile('{}.2bit'.format(
        local_files['human_genome_hg38']['abs_path'])
    )
    current_chrom = genome['chr{}'.format(chrom)]
    seq_slice = current_chrom[x:y].upper()
    if strand == '-':
        seq_slice = reverse_complement(seq_slice).upper()
    # create temp file and launch maxentscan
    tf = tempfile.NamedTemporaryFile()
    # print(tf.name)
    tf.write(bytes(seq_slice, encoding='utf-8'))
    tf.seek(0)
    if scantype == 3:
        formatted_seq = '{0}{1}'.format(seq_slice[:20].lower(), seq_slice[20:])
    else:
        formatted_seq = '{0}{1}'.format(seq_slice[:3], seq_slice[3:].lower())
    # cannot figure out why the above line is mandatory but
    # without it the file is empty
    # print(tf.read())
    result = subprocess.run(
        [
            '/usr/bin/perl',
            '{}'.format(ext_exe['maxentscan{}'.format(scantype)]),
            '{}'.format(tf.name)
        ],
        stdout=subprocess.PIPE
    )
    if result.returncode == 0:
        return [
            float(
                re.split(
                    '\n',
                    re.split(
                        '\t', str(result.stdout, 'utf-8')
                    )[1]
                )[0]
            ),
            formatted_seq
        ]
    else:
        return ['There has been an error while processing MaxEntScan', '']


def lovd_error_html(text):
    return """
    <tr>
        <td class="w3-left-align" id="lovd_feature" style="vertical-align:middle;">LOVD Matches:</td>
        <td class="w3-left-align" style="vertical-align:middle;">{}</td>
        <td class="w3-left-align" id="lovd_description" style="vertical-align:middle;">
            <em class="w3-small">LOVD match in public instances</em>
        </td>
    </tr>
    """.format(text)


def format_mirs(record):
    mir_html = ''
    mir_list = []  # to remove multiple occurences
    for mir in re.split(';', record):
        if mir != '.':
            mir_small = mir
            if mir not in mir_list:
                mir_list.append(mir)
                match_obj = re.search('^hsa-(.+)$', mir)
                if match_obj:
                    mir_small = match_obj.group(1)
                mir_html = "{0}<a href='{1}{2}' target='_blank' title='Link to miRBase'>{3}</a><br />".format(
                    mir_html, urls['mirbase'], mir, mir_small
                )
        else:
            mir_html = mir
    return mir_html


def check_api_key(db, api_key):  # in api
    curs = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if len(api_key) != 43:
        return {'mobidetails_error': 'Invalid API key'}
    else:
        curs.execute(
            """
            SELECT *
            FROM mobiuser
            WHERE api_key = %s
                AND activated = 't'
            """,
            (api_key,)
        )
        res = curs.fetchone()
        if res is None:
            return {'mobidetails_error': 'Unknown API key or unactivated account'}
        else:
            return {'mobiuser': res}


def check_caller(caller):  # in api
    if caller != 'browser' and \
            caller != 'cli':
        return 'Invalid caller submitted'
    return 'Valid caller'


def get_api_key(g, curs):
    # when we need an API key just to trigger an API action e.g. in upload.py
    api_key = None
    if g.user:
        api_key = g.user['api_key']
    else:
        curs.execute(
            """
            SELECT api_key
            FROM mobiuser
            WHERE username = 'mobidetails'
            """
        )
        res_key = curs.fetchone()
        if res_key:
            api_key = res_key['api_key']
    return api_key


def get_post_param(request, param):
    # swagger/curl sends request.args e.g.
    # curl -X POST "http://10.34.20.79:5001/api/variant/create?variant_chgvs=
    # NM_005422.2%3Ac.5040G%3ET&api_key=XXX" -H  "accept: application/json"
    # while
    # urllib3 request from create_vars_batch.py sends request.form
    if param:
        if request.args.get('{}'.format(param)):
            return request.args.get('{}'.format(param))
        elif '{}'.format(param) in request.form:
            return request.form['{}'.format(param)]
    return None


def get_acmg_criterion_color(criterion):
    criterion = str(criterion)
    if re.search(r'^PS', criterion) or \
            re.search(r'^PVS', criterion):
        return 'w3-red'
    elif re.search(r'^PM', criterion):
        return 'w3-deep-orange'
    elif re.search(r'^PP', criterion):
        return 'w3-orange'
    elif re.search(r'^BP', criterion):
        return 'w3-teal'
    elif re.search(r'^B[SA]', criterion):
        return 'w3-green'
    else:
        return None


def run_spip(gene_symbol, nm_acc, c_name, variant_id):
    tf = tempfile.NamedTemporaryFile(suffix='.txt')
    # temp file replaced w/ real file to perform caching
    tf.write(
        bytes('gene\tvarID\n{0}\t{1}:c.{2}'.format(
            gene_symbol, nm_acc, c_name
        ), encoding='utf-8')
    )
    tf.seek(0)
    # SPiP v1:
    # '-f',
    # '{}.fa'.format(local_files['human_genome_hg38']['abs_path']),
    # '-s',
    # '{}'.format(ext_exe['samtools']),
    result = subprocess.run(
        [
            ext_exe['Rscript'],
            '{}'.format(ext_exe['spip']),
            '-I',
            '{}'.format(tf.name),
            '-O',
            '{0}{1}.txt'.format(local_files['spip']['abs_path'], variant_id),
            '-g',
            'hg38'
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )
    if result.returncode == 0:
        # print('SPiP: {}'.format(result_file))
        spip_out = open('{0}{1}.txt'.format(local_files['spip']['abs_path'], variant_id), "r")
        result_file = spip_out.read()
        return result_file
    else:
        return 'There has been an error while processing SPiP'


def format_spip_result(result_spip, caller):
    spip_list = re.split('\n', result_spip)
    # print(result_spip[0])
    headers_spip = re.split('\t', spip_list[0])
    scores_spip = re.split('\t', spip_list[1])
    i = 0
    dict_spip = {}
    for header in headers_spip:
        if re.search(
            r'(gene|varID|chr|strand|gNomen|varType|ntChange|ExonInfo|transcript|seqPhysio|seqMutated)',
            header
                ):
            i += 1
            continue
        if header == 'Interpretation':
            if re.search(r'\+', scores_spip[i]):
                # we split intepretations with ' + ', then translate it
                # and rejoin with the same separator
                splitted_int = re.split(r' \+ ', scores_spip[i])
                formatted_list = ''
                for interpretation in splitted_int:
                    formatted_list += ' + {}'.format(
                        spip_annotations[interpretation]
                    )
                if caller == 'browser':
                    dict_spip[header] = [
                        formatted_list,
                        spip_headers[header]
                    ]
                else:
                    dict_spip[header] = formatted_list
                i += 1
                continue
            if caller == 'browser':
                dict_spip[header] = [
                    spip_annotations[scores_spip[i]],
                    spip_headers[header]
                ]
            else:
                dict_spip[header] = spip_annotations[scores_spip[i]]
            i += 1
            continue
        if caller == 'browser':
            if header == 'InterConfident':
                header = 'Risk'
            if header == 'mutInPBarea':
                header = 'mutInBParea'
            if scores_spip[i] == 'No available':
                scores_spip[i] = 'Not available'
            if scores_spip[i] == 'Outside SPiCE Interpretation':
                scores_spip[i] = 'Out of SPiCE interpretation region'
            dict_spip[header] = [
                scores_spip[i],
                spip_headers[header]
            ]
        else:
            dict_spip[header] = scores_spip[i]
        i += 1
    return dict_spip


def get_running_mode():
    return app.config['RUN_MODE']


def get_tinyurl_api_key():
    return app.config['TINY_URL_API_KEY']


def build_redirect_url(incoming_url=None):
    # method to rebuild URL and avoid Untrusted URL redirection
    # if re.search(r'https?:\/\/', incoming_url):
    if incoming_url is None:
        return None
    elif url_parse(incoming_url).scheme:
        return '{0}://{1}{2}{3}#{4}'.format(
            url_parse(incoming_url).scheme,
            url_parse(incoming_url).netloc,
            url_parse(incoming_url).path,
            url_parse(incoming_url).query,
            url_parse(incoming_url).fragment
        )
    elif re.search(r'^\/', incoming_url):
        if url_parse(incoming_url).fragment:
            return '{0}{1}#{2}'.format(
                url_parse(incoming_url).path,
                url_parse(incoming_url).query,
                url_parse(incoming_url).fragment
            )
        else:
            return '{0}{1}'.format(
                url_parse(incoming_url).path,
                url_parse(incoming_url).query,
            )
        # return incoming_url


def get_clingen_criteria_specification_id(current_gene_symbol):
    clingen_index = open(local_files['clingen_criteria_specification_index']['abs_path'], 'r')
    # if the list becomes too long, store id directly in DB
    for gene_symbol in clingen_index:
        if re.search(f'^{current_gene_symbol}$', gene_symbol):
            # get clingen spec page id in json
            with open(local_files['clingen_criteria_specification']['abs_path'], 'r', encoding='utf-8') as clingen_file:
                clingen_json = json.load(clingen_file)
            clingen_file.close()
            if 'data' in clingen_json:
                for rule in clingen_json['data']:
                    if 'genes' in rule:
                        for gene in rule['genes']:
                            if 'label' in gene and \
                                    gene['label'] == current_gene_symbol:
                                # we're in
                                return rule['svi']['id']
    return None


def spliceai_internal_api_hello():
    try:
        hello = json.loads(http.request(
            'GET',
            '{0}/hello'.format(urls['spliceai_internal_server'])).data.decode('utf-8')
        )
        if hello['spliceai_mtp_status'] == "running":
            return True
        else:
            raise Exception
    except Exception:
        return False
