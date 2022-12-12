#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, sys
sys.path.append("../scm")
sys.path.append("../tools_dep/")
import scm
import re
import subprocess
import codecc_web
import json
import util
import time
import platform
import shutil
import xml.etree.ElementTree as ET
import file
import yaml
import uuid
import network
import getpass

properties_info={}
params_root = {}
properties_path=''

def     get_stream_name_and_tool(message):
    try:
        global properties_info
        support_tools = properties_info["SUPPORT_TOOLS"].split(";")
        tool_type = ""
        stream_name = ""
        os.environ["LANG"] = "zh_CN.utf-8"
        for tool in support_tools:
            if re.search("_"+tool+'$', message):
                tool_type = tool
                replace_reg = re.compile("_"+tool+'$')
                stream_name = replace_reg.sub("", message).strip()
                properties_info['STREAM_NAME'] = stream_name
                properties_info['TOOL_TYPE'] = tool_type

    except Exception as e:
        raise Exception(e)
        
def load_properties():
    try:
        global properties_info
        global properties_path
        current_path=sys.path[0]
        properties_path=current_path+'/../config/config.properties'
        cov_properties = open(properties_path, encoding='utf-8')   #open the properties
        for line in cov_properties:
            if "=" in line:
                tmp = line.split("=",1)
                properties_info[tmp[0]] = tmp[1].replace("\n", "")  
        cov_properties.close()
    except Exception as e:
        raise Exception(e)
        
def verify_info():
    try:
        if not "DATA_ROOT_PATH" in properties_info or properties_info['DATA_ROOT_PATH'] == "":
            print("please define the option DATA_ROOT_PATH")
            exit(1)
        else:
            if not os.path.exists(properties_info['DATA_ROOT_PATH']): os.makedirs(properties_info['DATA_ROOT_PATH'])
    
        if not "PY27_PATH" in properties_info or properties_info['PY27_PATH'] == "":
            print("please define the option PY27_PATH")
            exit(1)
        else:
            if not os.path.exists(properties_info['PY27_PATH']): 
                print("the PY27_PATH is not found! "+properties_info['PY27_PATH'])
                exit(1)
            else:
                command = properties_info['PY27_PATH']+'/python -V'
                try:
                    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,shell=True,start_new_session=True)
                    for line in p.stdout:
                        if re.search("Python 2.7*", line.decode()):
                            break
                    else:
                        print('the PY27_PATH version is Incorrect, please change it')
                        exit(1)
                finally:
                    p.terminate()
                    p.wait()
        
        if not "PY35_PATH" in properties_info or properties_info['PY35_PATH'] == "":
            print("please define the option PY35_PATH")
            exit(1)
        else:
            if not os.path.exists(properties_info['PY35_PATH']): 
                print("the PY35_PATH is not found! "+properties_info['PY35_PATH'])
                exit(1)
            else:
                command = properties_info['PY35_PATH']+'/python -V'
                try:
                    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,shell=True,start_new_session=True)
                    for line in p.stdout:
                        if re.search("Python 3.5*", line.decode()):
                            break
                    else:
                        print('the PY35_PATH version is Incorrect, please change it')
                        exit(1)
                finally:
                    p.terminate()
                    p.wait()
    
        if not "PY27_PYLINT_PATH" in properties_info or properties_info['PY27_PYLINT_PATH'] == "":
            print("please define the option PY27_PYLINT_PATH")
            exit(1)
        else:
            if not os.path.exists(properties_info['PY27_PYLINT_PATH']): 
                print("the PY27_PYLINT_PATH is not found! "+properties_info['PY27_PYLINT_PATH'])
                exit(1)
                    
        if not "PY35_PYLINT_PATH" in properties_info or properties_info['PY35_PYLINT_PATH'] == "":
            print("please define the option PY35_PYLINT_PATH")
            exit(1)
        else:
            if not os.path.exists(properties_info['PY35_PYLINT_PATH']): 
                print("the PY35_PYLINT_PATH is not found! "+properties_info['PY35_PYLINT_PATH'])
                exit(1)

    except Exception as e:
        raise Exception(e)            
            
def merge_lang_from_codecc(code_lang):
    lang_list = ''
    try:
        if "CODECC_LANG_FLAG" in properties_info:
            code_lang_list = properties_info['CODECC_LANG_FLAG'].split(';')
            for code in code_lang_list:
                check_num = int(code_lang) & int(code.split(':')[1])
                if int(check_num) != 0:
                    if lang_list == "":
                        lang_list = code.split(':')[0]
                    else:
                        lang_list += ';'+code.split(':')[0]
    except Exception as e:
        raise Exception(e)
        
    return lang_list


def load_mutil_tool_properties(tool_type):
    try:
        global properties_info
        global properties_path
        current_path=sys.path[0]
        properties_path=current_path+'/../config/'+tool_type+'_config.properties'
        if not os.path.exists(properties_path):
            print('ERROR: the file path '+properties_path+' can not be found!')
            sys.exit(1)
        cov_properties = open(properties_path, encoding='utf-8')   #open the properties
        for line in cov_properties:
            if "=" in line:
                tmp = line.split("=",1)
                properties_info[tmp[0]] = tmp[1].replace("\n", "")
    except Exception as e:
        raise Exception(e)


def map_offline_properties_info(offline_properties_info):
    try:
        global properties_info
        global params_root
        if offline_properties_info != {}:
            offline_keys = offline_properties_info.keys()
            for key in offline_keys:
                if 'SCM_TYPE' in key or 'CERT_TYPE' in key:
                    properties_info[key] = offline_properties_info[key].strip().lower().replace('github','git')
                else:
                    properties_info[key] = offline_properties_info[key]
            if 'SVN_USER' in properties_info:
                properties_info["ACCOUNT"] = properties_info["SVN_USER"]
            
            if 'SVN_PASSWORD' in properties_info:
                properties_info["PASSWORD"] = properties_info["SVN_PASSWORD"]
            params_root['pipelineBuildId'] = properties_info['LANDUN_BUILDID']
            params_root['DEVOPS_PROJECT_ID'] = properties_info['DEVOPS_PROJECT_ID']
            params_root['DEVOPS_BUILD_TYPE'] = properties_info['DEVOPS_BUILD_TYPE']
            params_root['DEVOPS_AGENT_ID'] = properties_info['DEVOPS_AGENT_ID']
            params_root['DEVOPS_AGENT_SECRET_KEY'] = properties_info['DEVOPS_AGENT_SECRET_KEY']
            params_root['DEVOPS_AGENT_VM_SID'] = ''
            
            if 'LD_ENV_TYPE' in properties_info and 'LINUX_THIRD_PARTY' in properties_info['LD_ENV_TYPE']:
                software_root_path = ''
                if properties_info['LD_ENV_TYPE'] == 'LINUX_THIRD_PARTY':
                    if 'DEVOPS_AGENT_VM_SID' in properties_info:
                        params_root['DEVOPS_AGENT_VM_SID'] = properties_info['DEVOPS_AGENT_VM_SID']
                    software_root_path = properties_info['SOFTWARE_PATH']
                    # info = subprocess.Popen('lsof |grep '+software_root_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, shell=True)
                    # for line in info.stdout:
                    #     if 'can\'t stat() nfs file system '+software_root_path in str(line):
                    #         software_root_path = properties_info['SOFTWARE_PATH_TEMP']
                    #         break
                # if not os.path.exists(software_root_path+'/check.txt'):
                #     if getpass.getuser() == 'root':
                #         os.system('mkdir -p '+software_root_path)
                #         os.system('mount -t nfs -o nolock %s:%s %s' % (properties_info['SOFTWARE_DOMAIN'], properties_info['SOFTWARE_PATH'], software_root_path))
                if not os.path.exists(software_root_path+'/check.txt'):
                    setup_info='''########################################################################################################
#                                                                                                      #
#   check your env is :%s
#   Please use root or admin account run blew step under your server!
#   step-1: sudo mkdir -p %s
#   step-2: execute command to mount file path %s %s
#                                                                                                      #
########################################################################################################
'''
                    sys.stderr.write(setup_info % (properties_info['LD_ENV_TYPE'], software_root_path, properties_info['SOFTWARE_PATH'], software_root_path))
                    exit(1)
                third_party_env_update(software_root_path,properties_info)
                
    except Exception as e:
        raise Exception(e)

def third_party_env_update(software_root_path,properties_info):
    py2_bin_path = ''.join(software_root_path+"/python2/bin")
    py3_bin_path = ''.join(software_root_path+"/python3/bin")
    pylint2_bin_path = ''.join(software_root_path+"/pylint2")
    pylint3_bin_path = ''.join(software_root_path+"/pylint3")
    node_bin_path = ''.join(software_root_path+"/node/bin")
    jdk_bin_path = ''.join(software_root_path+"/jdk/bin")
    go_bin_path = ''.join(software_root_path+"/go/bin")
    go_path = ''.join(software_root_path+"/go")
    gometalinter_bin_path = ''.join(software_root_path+"/gometalinter/bin")
    mono_bin_path = ''.join(software_root_path+"/mono/bin")
    php_bin_path = ''.join(software_root_path+"/php/bin")
    if os.path.exists(py2_bin_path):
        print('third party env PY27_PATH: '+py2_bin_path)
        properties_info['PY27_PATH'] = py2_bin_path
    if os.path.exists(py3_bin_path):
        print('third party env PY35_PATH: '+py3_bin_path)
        properties_info['PY35_PATH'] = py3_bin_path
    if os.path.exists(pylint2_bin_path):
        print('third party env PY27_PYLINT_PATH: '+pylint2_bin_path)
        properties_info['PY27_PYLINT_PATH'] = pylint2_bin_path
    if os.path.exists(pylint3_bin_path):
        print('third party env PY35_PYLINT_PATH: '+pylint3_bin_path)
        properties_info['PY35_PYLINT_PATH'] = pylint3_bin_path
    if os.path.exists(node_bin_path):
        properties_info['SUB_PATH'] += os.pathsep+node_bin_path
    if os.path.exists(jdk_bin_path):
        properties_info['SUB_PATH'] += os.pathsep+jdk_bin_path
    if os.path.exists(go_bin_path):
        properties_info['SUB_PATH'] += os.pathsep+go_bin_path   
    if os.path.exists(gometalinter_bin_path):
        properties_info['SUB_PATH'] += os.pathsep+gometalinter_bin_path 
    if os.path.exists(mono_bin_path):
        properties_info['SUB_PATH'] += os.pathsep+mono_bin_path 
    if os.path.exists(php_bin_path):
        properties_info['SUB_PATH'] += os.pathsep+php_bin_path 
    if os.path.exists(go_path):
        properties_info['GOROOT'] = go_path 
        
        
def map_properties_info(offline_properties_info):
    try:
        global properties_info
        global params_root
        params_root =  {'codeccApiServer':properties_info['CODECC_API_SERVER'], 'codeccApiPort': properties_info['CODECC_API_PORT'], 'streamName': properties_info['STREAM_NAME'] , 'toolName': properties_info['TOOL_TYPE'].upper()}
        headers = {'Content-type': "application/json", 'x-devops-project-id': offline_properties_info['DEVOPS_PROJECT_ID'], 'x-devops-build-type': offline_properties_info['DEVOPS_BUILD_TYPE'], 'x-devops-agent-id': offline_properties_info['DEVOPS_AGENT_ID'], 'x-devops-agent-secret-key': offline_properties_info['DEVOPS_AGENT_SECRET_KEY']}
        if 'LD_ENV_TYPE' in offline_properties_info and 'LINUX_THIRD_PARTY' == offline_properties_info['LD_ENV_TYPE']:
            headers['x-devops-build-id'] = offline_properties_info['LANDUN_BUILDID']
            headers['x-devops-vm-sid'] = offline_properties_info['DEVOPS_AGENT_VM_SID']
        data_array = {}
        json_result = codecc_web.get_config_data_by_codecc(properties_info['STREAM_NAME'], properties_info['TOOL_TYPE'], headers)
        data_array = json_result['data']
        for key in data_array.keys():
            if 'scm_type' in key or 'cert_type' in key:
                properties_info[key.upper()] = data_array[key].strip().lower().replace('github','git')
            else:
                properties_info[key.upper()] = data_array[key]
                if 'task_id' in key:
                    params_root['taskId'] = data_array[key]
        if 'param_json' in data_array:
            param_array = json.loads(data_array['param_json'])
            for param_key in param_array.keys():
                properties_info[param_key.upper()] = param_array[param_key]
        
        if not 'ACCOUNT' in properties_info:
            properties_info['ACCOUNT'] = 'test'
    
        if not 'PASSWORD' in properties_info:
            properties_info['PASSWORD'] = 'test'
        
        if '\'' in properties_info["PASSWORD"]:
            properties_info["PASSWORD"] = '\"'+properties_info["PASSWORD"]+'\"'
        else:
            os_type = platform.system()
            if os_type == "Windows":
                properties_info["PASSWORD"] = '\"'+properties_info["PASSWORD"]+'\"'
            else:
                properties_info["PASSWORD"] = '\''+properties_info["PASSWORD"]+'\''
                            
        if '@' in properties_info["ACCOUNT"]:
            properties_info["ACCOUNT"] = properties_info["ACCOUNT"].split('@')[0]
        
        if 'URL' in properties_info:
            host = ''
            if '://' in properties_info['URL']:
                host = util.GetMiddleStr(properties_info["URL"], "://", ".com")+".com"
            elif 'git@' in properties_info['URL']:
                host = util.GetMiddleStr(properties_info["URL"], "git@", ".com")+".com"
            if "@" in host:
                host = host.split("@")[1]
            properties_info["HOST"] = host
        
        if 'ACCESS_TOKEN' in properties_info and properties_info['ACCESS_TOKEN'] != '':
            properties_info["URL"] = properties_info["URL"].replace('://', '://oauth2:'+properties_info["ACCESS_TOKEN"]+'@')
        
        properties_info["REVISION"] = "HEAD"
    except Exception as e:
        raise Exception(e) 
    return properties_info

def properties_git_info_update():
    try:
        #git项目，获取本地remote url和branch
        global properties_info
        keys = []
        if properties_info["SCM_TYPE"] == 'git':
            if 'REPO_RELPATH_MAP' in properties_info and json.loads(properties_info['REPO_RELPATH_MAP']) != {}:
                GIT_REPO_ALL_MAP = {}
                repo_relpath_map = json.loads(properties_info['REPO_RELPATH_MAP'])
                for key in repo_relpath_map.keys():
                    stream_code_path = ''.join(properties_info["STREAM_CODE_PATH"]+'/'+repo_relpath_map[key].replace('./', '/')).replace('//', '/')
                    info = scm.get_local_git_url(stream_code_path)
                    info['GIT_LOCAL_RELPATH'] = stream_code_path
                    GIT_REPO_ALL_MAP[key] = info
                    properties_info['GIT_REPO_ALL_MAP'] = GIT_REPO_ALL_MAP
            else:
                info = scm.get_local_git_url(properties_info["STREAM_CODE_PATH"])
                if info != {}:
                    keys = info.keys()
                for key in keys:
                    properties_info[key] = info[key]
    except Exception as e:
        raise Exception(e) 
        
def properties_update():
    try:
        global properties_info
        properties_info["STREAM_DATA_PATH"] = os.path.join(properties_info['DATA_ROOT_PATH'], properties_info['STREAM_NAME']+"_"+str(uuid.uuid1().hex)+"_"+properties_info['TOOL_TYPE'])
        properties_info["STREAM_RESULT_PATH"] = properties_info["STREAM_DATA_PATH"] +'/result'
        properties_info["PROJECT_FILE_LIST"]=os.path.join(properties_info["STREAM_DATA_PATH"], 'project_file_list.txt')
        if os.path.exists(properties_info["STREAM_DATA_PATH"]):
            file.delete_file_folder(properties_info["STREAM_DATA_PATH"])
            print ("删除了路径：",properties_info["STREAM_DATA_PATH"])
        if not os.path.exists(properties_info["STREAM_DATA_PATH"]):
            os.makedirs(properties_info["STREAM_DATA_PATH"])
            print ("添加了目录",properties_info["STREAM_DATA_PATH"])
            print(os.path.exists(properties_info["STREAM_DATA_PATH"]))
        #创建进程id文件
        properties_info["PID_FILE"]=os.path.join(properties_info["STREAM_DATA_PATH"], properties_info['STREAM_NAME']+str(os.getpid())+".pid").strip()
        
        #配置圈复杂度特殊参数
        if properties_info['TOOL_TYPE'] == "ccn":
            properties_info['PROJECT_AVG_FILE_CC_LIST'] = os.path.join(properties_info["STREAM_DATA_PATH"], 'project_avg_file_cc_list.txt')
        
        #获取项目语言并更新配置参数
        if properties_info['TOOL_TYPE'] == "dupc":
            code_lang = codecc_web.codecc_get_proj_language(properties_info['TASK_ID'])
            lang_list = merge_lang_from_codecc(code_lang)
            properties_info['TARGET_SUBFIXS'] = lang_list
            properties_info['PROJECT_DUPC_XML'] = os.path.join(properties_info["STREAM_DATA_PATH"], 'project_dupc.xml')
            properties_info['PROJECT_FILE_DUPC_JSON'] = os.path.join(properties_info["STREAM_DATA_PATH"], 'project_file_dupc.json')
       
        if properties_info['TOOL_TYPE'] == "goml":
            properties_info['PROJECT_GOML_JSON'] = os.path.join(properties_info["STREAM_DATA_PATH"], 'project_goml.json')
            if 'LANDUN_BUILDID' in properties_info and 'REL_PATH' in properties_info:
                properties_info.pop('REL_PATH')
            if (not 'REL_PATH' in properties_info or properties_info['REL_PATH'] == '') and not 'LANDUN_BUILDID' in properties_info:
                properties_info['REL_PATH'] = 'src'
                
        if 'REL_PATH' in properties_info and properties_info['REL_PATH'] != '':
            new_path = ''.join(properties_info["STREAM_CODE_PATH"]+'/'+properties_info['REL_PATH']).replace('./', '/').replace('//', '/')
            properties_info["STREAM_CODE_PATH"] = new_path
            
    except Exception as e:
        raise Exception(e) 


def generate_config(properties_info):
    try:
        properties_info["CONFIG_PATH"] = os.path.join(properties_info["STREAM_DATA_PATH"], 'tencent_config')
        current_path=sys.path[0]
        temp_config = os.path.join(current_path, 'tools_dep/config_temp/tencent_'+properties_info['TOOL_TYPE'])
        if properties_info['TOOL_TYPE'] == 'eslint':
            if os.path.exists(temp_config+'_standard') and properties_info['ESLINT_RC'] != 'standard':
                shutil.copyfile(temp_config+'_standard', properties_info["CONFIG_PATH"]+'_standard.js')
                properties_info["STANDARD_CONFIG_PATH"] = properties_info["CONFIG_PATH"]+'_standard.js'
            temp_config += '_'+properties_info['ESLINT_RC']
            properties_info["CONFIG_PATH"] += '.js'
        elif properties_info['TOOL_TYPE'] == 'detekt' or properties_info['TOOL_TYPE'] == 'occheck':
            properties_info["CONFIG_PATH"] += '.yml'
            
        if os.path.exists(temp_config):
            shutil.copyfile(temp_config, properties_info["CONFIG_PATH"])
            
        if properties_info['TOOL_TYPE'] == 'pylint' and os.path.exists(properties_info["CONFIG_PATH"]):
            update_pylint_config(properties_info)
        if properties_info['TOOL_TYPE'] == 'spotbugs' and os.path.exists(properties_info["CONFIG_PATH"]):
            update_spotbugs_config(properties_info)
        elif properties_info['TOOL_TYPE'] == 'checkstyle' and os.path.exists(properties_info["CONFIG_PATH"]):
            update_checkstyle_config(properties_info)
        elif properties_info['TOOL_TYPE'] == 'eslint' and os.path.exists(properties_info["CONFIG_PATH"]):
            checkers_list = []
            checker_options = {}
            if 'OPEN_CHECKERS' in properties_info:
                checkers_list = properties_info['OPEN_CHECKERS'].split(';')
            if 'CHECKER_OPTIONS' in properties_info:
                checker_options = json.loads(properties_info['CHECKER_OPTIONS'])
            if 'STANDARD_CONFIG_PATH' in properties_info:
                update_eslint_config(properties_info["STANDARD_CONFIG_PATH"], checkers_list, checker_options)
                update_eslint_config(properties_info["CONFIG_PATH"], checkers_list, checker_options)
            else:
                update_eslint_config(properties_info["CONFIG_PATH"], checkers_list, checker_options)
        elif properties_info['TOOL_TYPE'] == 'stylecop' and os.path.exists(properties_info["CONFIG_PATH"]):
            update_stylecop_config(properties_info)
        elif properties_info['TOOL_TYPE'] == 'detekt' and os.path.exists(properties_info["CONFIG_PATH"]):
            update_detekt_config(properties_info)
        elif properties_info['TOOL_TYPE'] == 'occheck' and os.path.exists(properties_info["CONFIG_PATH"]):
            update_occheck_config(properties_info)

    except Exception as e:
        raise Exception(e)

def update_stylecop_config(properties_info):
    try:
        tree = ET.ElementTree(file=properties_info["CONFIG_PATH"])
        root = tree.getroot()
        #delete checker
        if 'OPEN_CHECKERS' in properties_info:
            checkers_list = properties_info['OPEN_CHECKERS'].split(';')
            for elem in tree.iter():
                if 'Rule' == elem.tag and not elem.attrib['Name'] in checkers_list:
                    for enable_elem in elem.iter():
                        if 'BooleanProperty' in enable_elem.tag and enable_elem.attrib['Name'] == 'Enabled':
                            enable_elem.text = 'False'
        #update options
        if 'CHECKER_OPTIONS' in properties_info and json.loads(properties_info['CHECKER_OPTIONS']) != {}:
            key_values = {}
            checker_options = json.loads(properties_info['CHECKER_OPTIONS'])
            for option in checker_options.values():
                option = json.loads(option)
                for key in option.keys():
                    key_values[key] = option[key]
            for elem in tree.iter():
                for key in key_values.keys():
                    if 'Name' in elem.attrib and key == elem.attrib['Name']:
                        elem.text = str(key_values[key])        
        with open(properties_info["CONFIG_PATH"], 'wb') as file:
            tree.write(file, 'utf-8')
    except Exception as e:
        raise Exception(e)
        
def update_pylint_config(properties_info):
    try:
        with open(properties_info["CONFIG_PATH"], "a", encoding = 'utf-8') as file:
            if 'OPEN_CHECKERS' in properties_info:
                file.write('enable='+properties_info['OPEN_CHECKERS'].replace(';',',')+'\n')
            if 'CHECKER_OPTIONS' in properties_info and 'blank_rules' in properties_info['CHECKER_OPTIONS']:
                checker_options = json.loads(properties_info['CHECKER_OPTIONS'])
                option_list =  json.loads(checker_options['blank_rules'])
                keys = option_list.keys()
                for key in keys:
                    file.write(key+'='+option_list[key]+'\n')
    except Exception as e:
        raise Exception(e)

def update_spotbugs_config(properties_info):
    if 'OPEN_CHECKERS' in properties_info:
        checkers_list = properties_info['OPEN_CHECKERS'].split(';')
        with open(properties_info["CONFIG_PATH"], 'w') as file:
            file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            file.write('<FindBugsFilter>\n')
            for checker in checkers_list:
                if '' == checker:
                    continue
                file.write('<Match><Bug pattern=\"'+checker+'\" /></Match>\n')
            file.write('</FindBugsFilter>\n')
            
def update_checkstyle_config(properties_info):
    try:
        tree = ET.ElementTree(file=properties_info["CONFIG_PATH"])
        root = tree.getroot()
        checker_style=['com.tencent.checks.']
           
        if 'OPEN_CHECKERS' in properties_info:
            checkers_list = properties_info['OPEN_CHECKERS'].split(';')
            open_checkers_list = []
            for checker in checkers_list:
                if re.search("^com.tencent.checks.", checker):
                    open_checkers_list.append(checker)
                    continue
                short_checker=checker.rsplit('.',1)[1]
                if short_checker.endswith('Check'):
                    open_checkers_list.append(short_checker[:-5])
            checkers_list = open_checkers_list
            
            #delete skip_checkers
            for module in root.findall('module'):
                if module.attrib['name'] != 'TreeWalker' and not module.attrib['name'] in checkers_list:
                    root.remove(module)
                elif module.attrib['name'] == 'TreeWalker':
                    for tree_walker_module in module.findall('module'):
                        if not tree_walker_module.attrib['name'] in checkers_list:
                            module.remove(tree_walker_module)
            #update checker option
            if 'CHECKER_OPTIONS' in properties_info:
                change_checker_options={}
                checker_options = json.loads(properties_info['CHECKER_OPTIONS'])
                for key in checker_options.keys():
                    if re.search("^com.tencent.checks.", key):
                        change_checker_options[key] = checker_options[key]
                        continue
                    short_checker=key.rsplit('.',1)[1]
                    if short_checker.endswith('Check'):
                        change_checker_options[short_checker[:-5]] = checker_options[key]
                checker_options = change_checker_options
                for module in root.findall('module'):
                    if module.attrib['name'] != 'TreeWalker' and module.attrib['name'] in checkers_list and module.attrib['name'] in checker_options:
                        option_list =  json.loads(checker_options[module.attrib['name']])
                        keys = option_list.keys()
                        for key in keys:
                            if key == 'tokens':
                                for token in option_list[key]:
                                    ET.SubElement(module, 'property', attrib={'name':key, 'value':token})
                            else:
                                for property in module.findall('property'):
                                    if key in property.attrib['name']:
                                        property.attrib['value'] = option_list[key]
                    elif module.attrib['name'] == 'TreeWalker':
                        for tree_walker_module in module.findall('module'):
                            if tree_walker_module.attrib['name'] in checkers_list and tree_walker_module.attrib['name'] in checker_options:
                                option_list =  json.loads(checker_options[tree_walker_module.attrib['name']])
                                keys = option_list.keys()
                                for key in keys:
                                    if key == 'tokens':
                                        for token in option_list[key]:
                                            ET.SubElement(tree_walker_module, 'property', attrib={'name':key, 'value':token})
                                    else:
                                        for property in tree_walker_module.findall('property'):
                                            if key in property.attrib['name']:
                                                property.attrib['value'] = option_list[key]
        with open(properties_info["CONFIG_PATH"], 'wb') as file:
            file.write('<?xml version="1.0" encoding="UTF-8" ?><!DOCTYPE module PUBLIC "-//Checkstyle//DTD Checkstyle Configuration 1.3//EN" "https://checkstyle.org/dtds/configuration_1_3.dtd">'.encode('utf8'))
            tree.write(file, 'utf-8')

    except Exception as e:
        raise Exception(e)               
        
def update_eslint_config(config_file_path, checkers_list, checker_options):
    try:
        config_data = {}
        #delete filter checkers
        with open(config_file_path, 'r') as file:
            config_data = json.load(file)
            checker_list = config_data['rules']
            delete_checkers_list = []
            for checker in checker_list.keys():
                if not checker in checkers_list:
                    delete_checkers_list.append(checker)
            for delete_checker in delete_checkers_list:
                if delete_checker in config_data['rules']:
                    config_data['rules'][delete_checker]='off'
        #update checker option
        map_checker = {'max-len':'{ "code": xxx }'}
        for key in checker_options.keys():
            checker_value = ''
            for value in json.loads(checker_options[key]).values():
                checker_value = value
            if str(checker_value).isdigit():
                checker_value = int(checker_value)
            else:
                checker_value = str(checker_value)
            for map_key in map_checker.keys():
                if map_key == key:
                    checker_value = json.loads(map_checker[map_key].replace('xxx', str(checker_value)))
                    break
            config_data['rules'][key]= ["error", checker_value]
        #write new config
        with open(config_file_path, 'w') as file:
            file.write('module.exports =')
            json.dump(config_data,file, sort_keys=True, indent=4, separators=(',', ':'))
            file.write(';')
    except Exception as e:
        raise Exception(e)
        
def update_detekt_config(properties_info):
    try:
        open_checker_list = []
        skip_checker_list = []
        checker_options = {}
        if 'OPEN_CHECKERS' in properties_info:
            open_checker_list = properties_info['OPEN_CHECKERS'].split(';')
        if 'SKIP_FILTERS' in properties_info:
            skip_checker_list = properties_info['SKIP_FILTERS'].split(';')
        if 'CHECKER_OPTIONS' in properties_info:
            checker_options = json.loads(properties_info['CHECKER_OPTIONS'])
        config_file_path = properties_info["CONFIG_PATH"]
        with open(config_file_path, 'r', encoding='utf-8') as file:
            config_dict = yaml.load(file.read())
        for rule_set_key, rule_set_value in config_dict.items():
            if is_valid_detekt_rule_set(rule_set_key):
                for checker in rule_set_value.keys():
                    if re.match("([A-Z][a-z]+)+", checker):
                        if checker in open_checker_list:
                            config_dict[rule_set_key][checker]['active'] = True
                        else:
                            config_dict[rule_set_key][checker]['active'] = False
                for rule_key, rule_value in checker_options.items():
                    if rule_key in open_checker_list and rule_key in rule_set_value:
                        for option_key, option_value in json.loads(rule_value).items():
                            config_dict[rule_set_key][rule_key][option_key] = option_value
        with open(config_file_path, 'w', encoding='utf-8') as file:
            yaml.dump(config_dict, file, default_flow_style=False)
    except Exception as e:
        raise Exception(e)

def is_valid_detekt_rule_set(set_name):
    rule_set = ["comments", "complexity", "empty-blocks", \
        "exceptions", "formatting", "naming", "performance", \
            "potential-bugs", "style"]
    return set_name in rule_set

def update_occheck_config(properties_info):
    try:
        open_checker_str = ""
        checker_options = {}
        if 'OPEN_CHECKERS' in properties_info:
            open_checker_str = properties_info['OPEN_CHECKERS'].replace(";", ",")
        if 'CHECKER_OPTIONS' in properties_info:
            checker_options = json.loads(properties_info['CHECKER_OPTIONS'])
        config_file_path = properties_info["CONFIG_PATH"]
        config_dict = {}
        with open(config_file_path, 'r', encoding='utf-8') as file:
            config_dict = yaml.load(file.read())
        config_dict["Checks"] = "-*"
        if open_checker_str:
            config_dict["Checks"] = config_dict["Checks"] + "," + open_checker_str
        checker_option_list = []
        if "CheckOptions" in config_dict and len(config_dict["CheckOptions"]) > 0:
            checker_option_list = config_dict["CheckOptions"][:]
        for rule_key, rule_value in checker_options.items():
            for option_key, option_value in json.loads(rule_value).items():
                checker_option = {}
                checker_option["key"] = rule_key + "." + option_key
                checker_option["value"] = option_value
                for exist_option in config_dict["CheckOptions"]:
                    if exist_option["key"] == checker_option["key"]:
                        checker_option_list.remove(exist_option)
                        checker_option_list.append(checker_option)
                        break
                else:
                    checker_option_list.append(checker_option)
        config_dict["CheckOptions"] = checker_option_list
        with open(config_file_path, 'w', encoding='utf-8') as file:
            yaml.dump(config_dict, file, default_flow_style=False)
    except Exception as e:
        raise Exception(e)
