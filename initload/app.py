import boto3
import os
import glob
from datetime import datetime, timezone
import logging
import time

logging.getLogger().setLevel(logging.INFO)

# global variables
AWS_ACCESS_KEY_ID =  os.getenv('aws_access_key_id')
AWS_SECRET_ACCESS_KEY = os.getenv('aws_secret_access_key')
S3_BUCKET_NAME = os.getenv('s3_bucket_name')
S3_OBJECT_NAME = os.getenv('s3_object_name')

MODEL_LOCATION = os.getenv('model_location')
MODEL_DIR = os.getenv('model_dir')
MODEL_FILE = os.getenv('model_file')
STORE_DIR = os.getenv('STORE_DIR')
ENDPOINT_URL = os.getenv('endpoint_url')



def missing_environment(var1, var2=None):
    if var2 == None:
        logging.error(f'Environment variable "{var1}" not set.')
    else:
        logging.error(f'Neither environment variable "{var1}" nor "{var2}" is set.')
    return False

def check_environment():
    global STORE_DIR, MODEL_LOCATION, MODEL_DIR, MODEL_FILE, MODEL_DIR_FULL, MODEL_FILE_FULL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_OBJECT_NAME
    if STORE_DIR == None:
        STORE_DIR = '/store'
    if MODEL_LOCATION == None:
        MODEL_LOCATION = 'checkpoints'
    if MODEL_DIR == None:
        if not S3_BUCKET_NAME == None:
            MODEL_DIR = S3_BUCKET_NAME
        else:
            return missing_environment('model_dir', 's3_bucket_name')
    if MODEL_FILE == None:
        if not S3_OBJECT_NAME == None:
            MODEL_FILE = S3_OBJECT_NAME
        else:
            return missing_environment('model_file', 's3_object_name')
    else:
        if S3_OBJECT_NAME == None:
            S3_OBJECT_NAME = MODEL_FILE
        else:
            return missing_environment('model_file', 's3_object_name')
    if MODEL_DIR == '':
        MODEL_DIR = None
    MODEL_DIR_FULL = os.path.join(STORE_DIR, MODEL_LOCATION, MODEL_DIR) if not MODEL_DIR == None else os.path.join(STORE_DIR, MODEL_LOCATION)
    MODEL_FILE_FULL = os.path.join(MODEL_DIR_FULL, MODEL_FILE) 
    return True

def check_keys():
    global STORE_DIR, MODEL_LOCATION, MODEL_DIR, MODEL_FILE, MODEL_DIR_FULL, MODEL_FILE_FULL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_OBJECT_NAME
    if AWS_ACCESS_KEY_ID == None:
        return missing_environment('aws_access_key_id')
    if AWS_SECRET_ACCESS_KEY == None:
        return missing_environment('aws_secret_access_key')
    if S3_BUCKET_NAME == None:
        return missing_environment('s3_bucket_name')
    return True



def load_model():
    global STORE_DIR, MODEL_LOCATION, MODEL_DIR, MODEL_FILE, MODEL_DIR_FULL, MODEL_FILE_FULL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_OBJECT_NAME, ENDPOINT_URL
    if not os.path.exists(STORE_DIR):
        logging.error(f'Directory "{STORE_DIR}" not mounted')
        return False
    for dir in [os.path.join(STORE_DIR, 'checkpoints'), os.path.join(STORE_DIR, 'indexes'), os.path.join(STORE_DIR, 'models'), MODEL_DIR_FULL]:
        if not os.path.exists(dir):
             os.makedirs(dir)
             logging.info(f'Directory "{dir}" created.')
    if not os.path.exists(MODEL_DIR_FULL):
        os.makedirs(MODEL_DIR_FULL)
        logging.info(f'Directory "{MODEL_DIR_FULL}" created.')
    if ENDPOINT_URL != None:
        logging.info(f'Endpoint URL: "{ENDPOINT_URL}"')
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY) if ENDPOINT_URL == None else \
         boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, endpoint_url=ENDPOINT_URL)
    object_list = []

    response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME)
    filedir = {}
    content = ''
    for file_full in glob.iglob(MODEL_DIR_FULL + '/**/*', recursive=True):
        file = os.path.relpath(file_full, MODEL_DIR_FULL)
        content = content + f'\n {str(os.stat(file_full).st_size) if os.path.isfile(file_full) else "dir":>10}  {datetime.fromtimestamp(os.stat(file_full).st_mtime, tz=timezone.utc)}  {file}'
        if os.path.isfile(file_full):
            filedir[file] = {'filepath': file_full, 'date': datetime.fromtimestamp(os.stat(file_full).st_mtime, tz=timezone.utc), 'size': os.stat(file_full).st_size}
    logging.info(f'Model directory is "{MODEL_DIR_FULL}". Content: {content}')
    wait = False
    force = False

    # check origin
    bucket_filename = os.path.join(MODEL_DIR_FULL, '_bucket.txt')
    try:
        with open(bucket_filename, "r") as _f:
            bucket = _f.read()
    except Exception:
        bucket = '-'
    if not bucket.startswith(S3_BUCKET_NAME) or not bucket.endswith(S3_OBJECT_NAME) or not str(ENDPOINT_URL) in bucket:
        # different bucket -> delete old content
        force = True

    for object in response['Contents']:
        bucket_file = object['Key']
        if bucket_file.endswith('/') or bucket_file not in filedir.keys():
            continue
        file_stat = filedir[object['Key']]
        if object['LastModified'] > file_stat['date'] or object['Size'] != file_stat['size'] or force:
            logging.info(f'File {bucket_file} in bucket differs from filesystem -> deleting')
            os.remove(file_stat['filepath'])
            wait = True
        filedir.pop(object['Key'])
    for k in filedir.keys():
        if filedir[k]['filepath'] != bucket_filename:
            logging.info(f'File {k} not in bucket -> deleting')
            os.remove(filedir[k]['filepath'])
    if wait:
        # wait a few seconds to ensure that file deletion has finished
        time.sleep(5)

    if S3_OBJECT_NAME == '*':
        response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME)
        for object in response['Contents']:
            object_list.append(object['Key'])
    else:
        object_list.append(S3_OBJECT_NAME)

    count = 0
    start_time = time.time()
    keys_checked = False
    for object in object_list:
        if not keys_checked:
            if not check_keys():
                return False
            keys_checked = True
        if object.endswith('/'):
            continue
        model_file_full = os.path.join(MODEL_DIR_FULL, object) if S3_OBJECT_NAME == '*' else MODEL_FILE_FULL
        if not os.path.isfile(model_file_full):
            object_path = object.split('/')
            index = 1
            while index < len(object_path):
                subpath = os.path.join(MODEL_DIR_FULL, *object_path[0:index])
                if not os.path.exists(subpath):
                    os.makedirs(subpath)
                    logging.info(f'Directory "{subpath}" created.')
                index = index + 1
            logging.info(f'Start downloading: {S3_BUCKET_NAME}/{object}')
            s3.download_file(S3_BUCKET_NAME, object, model_file_full)
            count = count + 1
        else:
            logging.info(f'Model file "{object}" already exists -> download skipped.')
    elapsed_time = time.time() - start_time
    logging.info(f'Download of {count} files successfully completed, elapsed time: {elapsed_time:.2f}s.')

    if force:
        with open(bucket_filename, "w") as _f:
            _f.write(f'{S3_BUCKET_NAME}|{str(ENDPOINT_URL)}|{S3_OBJECT_NAME}')
        time.sleep(5)
        # wait a few seconds to ensure that file is closed
        logging.info(f'File {bucket_filename} written.')

    return True



if __name__ == '__main__':
    if not check_environment() or not load_model():
        # exit with error
        exit(1)
