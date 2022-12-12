# coding=utf-8
__author__ = 'ealexand'

import csv
import os
import time
from flask import Blueprint, render_template, abort, current_app, jsonify, request
import numpy
import MikeTM
import Utilities as util

def index():
    return view_by_name("foo")

def view_by_name(model_name):
    return render_template(
        "slimCV.html",
        title=model_name + " (Matrix View)",
        model_name=model_name,
        models=os.listdir(current_app.config['METADATA_ROOT'])
    )

def get_metadata(model_name):
    metadataCSV = os.path.join(util.get_model_root(model_name), 'metadata.csv')
    metadata = []
    with open(metadataCSV, 'rb') as f:
        reader = csv.reader(f)
        rowNum = 0
        for row in reader:
            if rowNum == 0:
                colNames = row
            elif rowNum == 1:
                dataTypes = row
            else:
                temp = {}
                for i in range(len(row)):
                    temp[colNames[i]] = row[i]
                metadata.append(temp)
            rowNum += 1
    try:
        return jsonify({'metadata': metadata, 'fieldNames': colNames, 'dataTypes': dataTypes})
    except UnicodeDecodeError:
        for i in range(len(metadata)):
            try:
                jsonify({'metadata': metadata[i]})
            except UnicodeDecodeError:
                print 'UnicodeDecodeError on metadata row %d' % i
                print metadata[i]
                raise


def get_theta(model_name):
    start = time.time()
    includedMetadataIndices = getIncludedMetadata(model_name)
    print 'Got metadata (%.2f sec)' % (time.time() - start)

    start = time.time()
    model_root = util.get_model_root(model_name)
    thetaCSV = os.path.join(model_root, 'theta.csv')
    theta = []
    topicProps = {}
    with open(thetaCSV, 'rb') as f:
        reader = csv.reader(f)
        currDoc = 0
        currIndex = 0 # This is only incremented if we actually include the doc
        maxTopic = 0
        for row in reader:
            if currDoc in includedMetadataIndices:
                theta.append({})
                for i in range(0, len(row), 2):
                    topicNum = int(row[i])
                    prop = float(row[i+1])
                    theta[currIndex][topicNum] = prop
                    maxTopic = max(maxTopic, topicNum)
                    if topicNum in topicProps:
                        topicProps[topicNum].append(prop)
                    else:
                        topicProps[topicNum] = [prop]
                currIndex += 1
            currDoc += 1
    print 'Got theta (%.2f sec)' % (time.time() - start)

    start = time.time()
    topicMetadataList = [{} for i in range(maxTopic+1)]
    for i in range(maxTopic+1):
        if i in topicProps:
            currTopicList = topicProps[i]
            topicMetadataList[i]['numDocs'] = len(currTopicList)
            topicMetadataList[i]['min'] = numpy.min(currTopicList)
            topicMetadataList[i]['max'] = numpy.max(currTopicList)
            topicMetadataList[i]['median'] = numpy.median(currTopicList)
            topicMetadataList[i]['mean'] = numpy.mean(currTopicList)
            topicMetadataList[i]['variance'] = numpy.var(currTopicList)
            topicMetadataList[i]['range'] = topicMetadataList[i]['max'] - topicMetadataList[i]['min']
            #topicMetadataList[i]['outliers'] = 0 #TODO: fill this in
            #topicMetadataList[i]['uniformity'] = 0 #TODO: fill this in
        else:
            topicMetadataList[i] = {
                'numDocs': 0,
                'min': 0,
                'max': 0,
                'median': 0,
                'mean': 0,
                'variance': 0,
                'range': 0
            }
    topicMetadataFields = ['min','max','median','mean','variance','range','numDocs']#,'outliers','uniformity']
    print 'Got topic metadata (%.2f sec)' % (time.time() - start)

    returnDict = {
        'theta': theta,
        'numDocs': len(theta),
        'numTopics': maxTopic + 1,
        'topicMetadata': topicMetadataList,
        'topicMetadataFields': topicMetadataFields
    }

    try:
        topicNameFile = os.path.join(model_root, 'topicNames.csv')
        topicNames = []
        with open(topicNameFile, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                topicNames = row
                break
        returnDict['colList'] = topicNames
    except IOError:
        pass

    try:
        groupFilePath = os.path.join(model_root, 'docGroups.csv')
        groups = {}
        with open(groupFilePath, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                groups[row[0]] = map(int, row[1:])
        returnDict['docGroups'] = groups
    except IOError:
        returnDict['docGroups'] = {}

    try:
        groupFilePath = os.path.join(model_root, 'topicGroups.csv')
        groups = {}
        with open(groupFilePath, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                groups[row[0]] = map(int, row[1:])
        returnDict['topicGroups'] = groups
    except IOError:
        returnDict['topicGroups'] = {}

    print 'Jsonifying and sending...'

    return jsonify(returnDict)


def getIncludedMetadata(model_name):
    metadataCSV = os.path.join(util.get_model_root(model_name), 'metadata.csv')
    includedMetadataIndices = []
    with open(metadataCSV, 'rb') as f:
        reader = csv.reader(f)
        rowNum = 0
        for row in reader:
            if rowNum == 0:
                colNames = row
            elif rowNum == 1:
                dataTypes = row
            else:
                temp = {}
                for i in range(len(row)):
                    temp[colNames[i]] = row[i]
                includedMetadataIndices.append(rowNum - 2)
            rowNum += 1
    return includedMetadataIndices


def set_group_name(model_name, group_file, group_name, group):
    # First, load any pre-existing groups to compare
    groups = {}
    groupFilePath = os.path.join(util.get_model_root(model_name), group_file)
    try:
        with open(groupFilePath, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                groups[row[0]] = row[1:]
    except IOError:
        pass

    groups[group_name] = map(int, group.split(','))
    with open(groupFilePath, 'wb') as f:
        writer = csv.writer(f)
        for groupName in groups:
            writer.writerow([groupName] + groups[groupName])
    return jsonify({'groups':groups})


def get_groups(model_name, group_file):
    try:
        groupFilePath = os.path.join(util.get_model_root(model_name), group_file)
        groups = {}
        with open(groupFilePath, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                groups[row[0]] = map(int, row[1:])
        return jsonify({'groups':groups})
    except IOError:
        return jsonify({})

def getAnovaOrder(model_name, fieldName, debug=False):
    try:
        mtm = MikeTM.TopicModel(current_app.config['METADATA_ROOT'], model_name)
        anovaOrder = mtm.anovaColsRanks(fieldName)
        if debug:
            return anovaOrder
        else:
            return jsonify({'anovaOrder':[str(v) for v in anovaOrder]})
    except KeyError:
        print 'KeyError while getting ANOVA order. Probably from bad metadata field name. Check capitalization?'
        return jsonify({'anovaOrder':[]})

def getContrastOrder(model_name, fieldName, group1, group2=[], debug=False):
    group1 = group1.split(',')
    if group2=='matrix' or group2=='[ALL]':
        group2 = []
    else:
        group2 = group2.split(',')
    mtm = MikeTM.TopicModel(current_app.config['METADATA_ROOT'], model_name)
    contrastOrder = mtm.contrastColsRanks(fieldName, group1, group2)
    if debug:
        return contrastOrder
    else:
        return jsonify({'contrastOrder':[str(v) for v in contrastOrder]})

if __name__=='__main__':
    print getAnovaOrder('ShakespeareChunkedOptimized_50','Genre',debug=True)
    print getContrastOrder('ShakespeareChunkedOptimized_50','Genre','comedy',debug=True)
    print getContrastOrder('ShakespeareChunkedOptimized_50','Genre','tragedy','history',debug=True)
    print getContrastOrder('ShakespeareChunkedOptimized_50','Genre','romance',debug=True)
    print getContrastOrder('ShakespeareChunkedOptimized_50','Genre',['comedy','tragedy'],debug=True)