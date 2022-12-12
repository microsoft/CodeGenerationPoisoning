# Copyright (c) 2012, Psiphon Inc.
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

'''
Periodically checks S3 upload bucket for new items. Gets them, deletes them.
Decrypts them and stores them in the diagnostic-info-DB.
'''

import time
import smtplib
import json
import yaml
import multiprocessing
from boto.s3.connection import S3Connection

from config import config
import logger
import utils
import decryptor
import datastore
import sender
import datatransformer
import redactor


# This should be set by the service manager when it receives SIGTERM
terminate = False

_SLEEP_TIME_SECS = 60
_BUCKET_ITEM_MIN_SIZE = 100


def _is_bucket_item_sane(key):
    if key.size < _BUCKET_ITEM_MIN_SIZE or key.size > int(config['s3ObjectMaxSize']):
        err = 'item not sane size: %d' % key.size
        logger.error(err)
        return False

    return True


def _bucket_iterator(bucket):
    logger.debug_log('_bucket_iterator start')

    while True:
        for key in bucket.list():
            logger.debug_log('_bucket_iterator: %s' % key)

            if terminate:
                logger.debug_log('got terminate; _bucket_iterator breaking')
                return

            contents = None

            # Do basic sanity checks before trying to download the object
            if _is_bucket_item_sane(key):
                logger.debug_log('_bucket_iterator: good item found, yielding')
                contents = key.get_contents_as_string()

            # Make sure to delete the key *before* proceeding, so we don't
            # try to re-process if there's an error.
            key.delete()

            if contents:
                yield contents

        logger.debug_log('_bucket_iterator: no item found, sleeping')
        time.sleep(_SLEEP_TIME_SECS)

    logger.debug_log('_bucket_iterator end') # unreachable


def _should_email_data(diagnostic_info):
    '''
    Determine if this diagnostic info should be emailed. Not all diagnostic
    info bundles have useful information that needs to be immediately seen by
    a human. Additionally, trying to email too many feedbacks can produce a backlog.
    '''
    #return diagnostic_info.get('Feedback', {}).get('Message', {}).get('text')
    return diagnostic_info.get('Feedback', {}).get('Message', {}).get('text') and diagnostic_info.get('Feedback', {}).get('email')


def go():
    '''
    Spawns the worker subprocesses and sends data to them.
    '''
    logger.debug_log('go: start')

    s3_conn = S3Connection(config['aws_access_key_id'], config['aws_secret_access_key'])
    bucket = s3_conn.get_bucket(config['s3_bucket_name'])

    # Set up the multiprocessing
    worker_manager = multiprocessing.Manager()
    # We only want to pull items out of S3 as we process them, so the queue needs to be
    # limited to the number of worker processes.
    work_queue = worker_manager.Queue(maxsize=config['numProcesses'])
    # Spin up the workers
    worker_pool = multiprocessing.Pool(processes=config['numProcesses'])
    [worker_pool.apply_async(_process_work_items, (work_queue,)) for i in range(config['numProcesses'])]

    # Note that `_bucket_iterator` throttles itself if/when there are no
    # available objects in the bucket.
    for encrypted_info_json in _bucket_iterator(bucket):
        if terminate:
            logger.debug_log('go: got terminate; closing work_queue')
            work_queue.close()
            break

        logger.debug_log('go: enqueueing work item')
        # This blocks if the queue is full
        work_queue.put(encrypted_info_json)
        logger.debug_log('go: enqueued work item')

    logger.debug_log('go: done')


def _process_work_items(work_queue):
    '''
    This runs in the multiprocessing forks to do the actual work. It is a long-lived loop.
    '''
    while True:
        if terminate:
            logger.debug_log('got terminate; stopping work')
            break

        # In theory, all bucket items should be usable by us, but there's
        # always the possibility that a user (or attacker) is messing with us.
        try:
            logger.debug_log('_process_work_items: dequeueing work item')
            # This blocks if the queue is empty
            encrypted_info_json = work_queue.get()
            logger.debug_log('_process_work_items: dequeued work item')

            logger.debug_log('_process_work_items: processing item')

            diagnostic_info = None

            encrypted_info = json.loads(encrypted_info_json)

            diagnostic_info = decryptor.decrypt(encrypted_info)
            if not diagnostic_info:
                logger.error('diagnostic_info decrypted empty')
                # Also throw, so we get an email about it
                raise Exception('diagnostic_info decrypted empty')

            diagnostic_info = diagnostic_info.strip()
            if not diagnostic_info:
                logger.error('diagnostic_info stripped empty')
                # Also throw, so we get an email about it
                raise Exception('diagnostic_info stripped empty')

            # HACK: PyYaml only supports YAML 1.1, which is not a true superset
            # of JSON. Therefore it can (and does) throw errors on some Android
            # feedback. We will try to load using JSON first.
            # TODO: Get rid of all YAML feedback and remove it from here.
            try:
                diagnostic_info = json.loads(diagnostic_info)
                logger.debug_log('_process_work_items: loaded JSON')
            except:
                diagnostic_info = yaml.safe_load(diagnostic_info)
                logger.debug_log('_process_work_items: loaded YAML')

            if not diagnostic_info:
                logger.error('diagnostic_info unmarshalled empty')
                # Also throw, so we get an email about it
                raise Exception('diagnostic_info unmarshalled empty')

            logger.log('feedback id: %s' % diagnostic_info.get('Metadata', {}).get('id'))

            # Modifies diagnostic_info
            utils.convert_psinet_values(config, diagnostic_info)

            if not utils.is_diagnostic_info_sane(diagnostic_info):
                # Something is wrong. Skip and continue.
                continue

            # Modifies diagnostic_info
            redactor.redact_sensitive_values(diagnostic_info)

            # Modifies diagnostic_info
            datatransformer.transform(diagnostic_info)

            # Store the diagnostic info
            record_id = datastore.insert_diagnostic_info(diagnostic_info)
            if record_id is None:
                # An error occurred or diagnostic info was a duplicate.
                continue

            if _should_email_data(diagnostic_info):
                logger.debug_log('_process_work_items: should email')
                # Record in the DB that the diagnostic info should be emailed
                datastore.insert_email_diagnostic_info(record_id, None, None)

            # Store an autoresponder entry for this diagnostic info
            datastore.insert_autoresponder_entry(None, record_id)

            logger.debug_log('decrypted diagnostic data')

        except decryptor.DecryptorException as e:
            logger.exception()
            logger.error(str(e))
            try:
                # Something bad happened while decrypting. Report it via email.
                sender.send(config['decryptedEmailRecipient'],
                            config['emailUsername'],
                            u'S3Decryptor: bad object',
                            encrypted_info_json,
                            None)  # no html body
            except smtplib.SMTPException as e:
                logger.exception()
                logger.error(str(e))

        # yaml.constructor.ConstructorError was being thown when a YAML value
        # consisted of just string "=". Probably due to this PyYAML bug:
        # http://pyyaml.org/ticket/140
        except (ValueError, TypeError, yaml.constructor.ConstructorError) as e:
            # Try the next attachment/message
            logger.exception()
            logger.error(str(e))

        except Exception as e:
            try:
                # Something bad happened while decrypting. Report it via email.
                sender.send(config['decryptedEmailRecipient'],
                            config['emailUsername'],
                            u'S3Decryptor: unhandled exception',
                            str(e) + '\n---\n' + str(diagnostic_info),
                            None)  # no html body
            except smtplib.SMTPException as e:
                logger.exception()
                logger.error(str(e))
            raise

    logger.debug_log('_process_work_items: done')
