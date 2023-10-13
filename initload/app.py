import boto3
import ibm_boto3
from ibm_botocore.client import Config, ClientError
import os
import glob
from datetime import datetime, timezone
import logging
import time
import argparse

logging.getLogger().setLevel(logging.INFO)

# global variables
SETTINGS = { 
    'ENDPOINT': os.getenv('s3_endpoint'),
    'INSTANCE': os.getenv('s3_instance'),
    'APIKEY': os.getenv('s3_apikey'),
    'PROVIDER': os.getenv('s3_provider'),
    'AWS_ACCESS_KEY_ID': os.getenv('aws_access_key_id'),
    'AWS_SECRET_ACCESS_KEY': os.getenv('aws_secret_access_key'),
    'S3_BUCKET_NAME': os.getenv('s3_bucket_name'),
    'S3_OBJECT_NAME': os.getenv('s3_object_name'),
    'MODEL_LOCATION': os.getenv('model_location'),
    'MODEL_DIR': os.getenv('model_dir'),
    'MODEL_FILE': os.getenv('model_file'),
    'STORE_DIR': os.getenv('STORE_DIR'),
    'FORCE_DOWNLOAD': os.getenv('force_download'),
    'UPLOAD_BUCKET_NAME':  os.getenv('upload_bucket_name'),
    'UPLOAD_DIR':  os.getenv('upload_dir'),
    'UPLOAD_ACCESS_KEY_ID':  os.getenv('upload_access_key_id'),
    'UPLOAD_SECRET_ACCESS_KEY':  os.getenv('upload_secret_access_key'),
    'UPLOAD_ENDPOINT': os.getenv('upload_endpoint')
}


def get_buckets():
    global SETTINGS
    print("Retrieving list of buckets")
    try:
        #cos = ibm_boto3.resource("s3", ibm_api_key_id=SETTINGS['APIKEY'], ibm_service_instance_id=SETTINGS['INSTANCE'], \
        #                        config=Config(signature_version="oauth"), endpoint_url=SETTINGS['ENDPOINT'])
        cos = ibm_boto3.resource("s3", aws_access_key_id=SETTINGS['AWS_ACCESS_KEY_ID'], aws_secret_access_key=SETTINGS['AWS_SECRET_ACCESS_KEY'], \
                                 endpoint_url=SETTINGS['ENDPOINT'])
        buckets = cos.buckets.all()
        for bucket in buckets:
            print("Bucket Name: {0}".format(bucket.name))
    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to retrieve list buckets: {0}".format(e))

def get_bucket_contents(bucket_name):
    print("Retrieving bucket contents from: {0}".format(bucket_name))
    try:
        #cos = ibm_boto3.resource("s3", ibm_api_key_id=SETTINGS['APIKEY'], ibm_service_instance_id=SETTINGS['INSTANCE'], \
        #                        config=Config(signature_version="oauth"), endpoint_url=SETTINGS['ENDPOINT'])
        cos = ibm_boto3.resource("s3", aws_access_key_id=SETTINGS['AWS_ACCESS_KEY_ID'], aws_secret_access_key=SETTINGS['AWS_SECRET_ACCESS_KEY'], \
                                endpoint_url=SETTINGS['ENDPOINT'])
        files = cos.Bucket(bucket_name).objects.all()
        for file in files:
            print("{0} ({2}, {1} bytes).".format(file.key, file.size, file.last_modified.strftime("%m/%d/%Y %H:%M:%S")))
    except ClientError as be:
        print("CLIENT ERROR: {0}\n".format(be))
    except Exception as e:
        print("Unable to retrieve bucket contents: {0}".format(e))


def missing_environment(var1, var2=None):
    if var2 == None:
        logging.error(f'Environment variable "{var1}" not set.')
    else:
        logging.error(f'Neither environment variable "{var1}" nor "{var2}" is set.')
    return False

def check_environment():
    global SETTINGS
    if SETTINGS['STORE_DIR'] == None:
        SETTINGS['STORE_DIR'] = '/store'
    if SETTINGS['MODEL_LOCATION'] == None:
        SETTINGS['MODEL_LOCATION'] = 'checkpoints'
    if SETTINGS['MODEL_DIR'] == None:
        if not SETTINGS['S3_BUCKET_NAME'] == None:
            SETTINGS['MODEL_DIR'] = SETTINGS['S3_BUCKET_NAME']
        else:
            return missing_environment('model_dir', 's3_bucket_name')
    if SETTINGS['MODEL_FILE'] == None:
        if not SETTINGS['S3_OBJECT_NAME'] == None:
            SETTINGS['MODEL_FILE'] = SETTINGS['S3_OBJECT_NAME']
        else:
            return missing_environment('model_file', 's3_object_name')
    else:
        if SETTINGS['S3_OBJECT_NAME'] == None:
            SETTINGS['S3_OBJECT_NAME'] = SETTINGS['MODEL_FILE']
        else:
            return missing_environment('model_file', 's3_object_name')
    if SETTINGS['MODEL_DIR'] == '':
        SETTINGS['MODEL_DIR'] = None
    SETTINGS['MODEL_DIR_FULL'] = os.path.join(SETTINGS['STORE_DIR'], SETTINGS['MODEL_LOCATION'], SETTINGS['MODEL_DIR']) if not SETTINGS['MODEL_DIR'] == None \
        else os.path.join(SETTINGS['STORE_DIR'], SETTINGS['MODEL_LOCATION'])
    SETTINGS['MODEL_FILE_FULL'] = os.path.join(SETTINGS['MODEL_DIR_FULL'], SETTINGS['MODEL_FILE']) 
    return True

def check_keys():
    global SETTINGS
    if SETTINGS['AWS_ACCESS_KEY_ID'] == None:
        return missing_environment('aws_access_key_id')
    if SETTINGS['AWS_SECRET_ACCESS_KEY'] == None:
        return missing_environment('aws_secret_access_key')
    if SETTINGS['S3_BUCKET_NAME'] == None:
        return missing_environment('s3_bucket_name')
    return True



def load_model():
    global SETTINGS
    if not os.path.exists(SETTINGS['STORE_DIR']):
        logging.error(f"Directory \"{SETTINGS['STORE_DIR']}\" not mounted")
        return False
    for dir in [os.path.join(SETTINGS['STORE_DIR'], 'checkpoints'), os.path.join(SETTINGS['STORE_DIR'], 'indexes'), os.path.join(SETTINGS['STORE_DIR'], 'models'), SETTINGS['MODEL_DIR_FULL']]:
        if not os.path.exists(dir):
             os.makedirs(dir)
             logging.info(f'Directory "{dir}" created.')
    if not os.path.exists(SETTINGS['MODEL_DIR_FULL']):
        os.makedirs(SETTINGS['MODEL_DIR_FULL'])
        logging.info(f"Directory \"{SETTINGS['MODEL_DIR_FULL']}\" created.")

    # get s3 client object
    if SETTINGS['ENDPOINT'] != None:
        logging.info(f"Endpoint: \"{SETTINGS['ENDPOINT']}\"")

    if SETTINGS['PROVIDER'] == 'IBM':
        s3 = ibm_boto3.client("s3", ibm_api_key_id=SETTINGS['APIKEY'], ibm_service_instance_id=SETTINGS['INSTANCE'], \
                                config=Config(signature_version="oauth"), endpoint_url=SETTINGS['ENDPOINT'])
    
    else:
    
        s3 = boto3.client('s3', aws_access_key_id=SETTINGS['AWS_ACCESS_KEY_ID'], aws_secret_access_key=SETTINGS['AWS_SECRET_ACCESS_KEY']) if SETTINGS['ENDPOINT'] == None else \
            boto3.client('s3', aws_access_key_id=SETTINGS['AWS_ACCESS_KEY_ID'], aws_secret_access_key=SETTINGS['AWS_SECRET_ACCESS_KEY'], endpoint_url=SETTINGS['ENDPOINT'])
    
    response = s3.list_objects_v2(Bucket=SETTINGS['S3_BUCKET_NAME'])
    bucket_objects = response['Contents']

    object_list = []

    # cleanup local dir
    filedir = {}
    content = ''
    for file_full in glob.iglob(SETTINGS['MODEL_DIR_FULL'] + '/**/*', recursive=True):
        file = os.path.relpath(file_full, SETTINGS['MODEL_DIR_FULL'])
        content = content + f'\n {str(os.stat(file_full).st_size) if os.path.isfile(file_full) else "dir":>10}  {datetime.fromtimestamp(os.stat(file_full).st_mtime, tz=timezone.utc)}  {file}'
        if os.path.isfile(file_full):
            filedir[file] = {'filepath': file_full, 'date': datetime.fromtimestamp(os.stat(file_full).st_mtime, tz=timezone.utc), 'size': os.stat(file_full).st_size}
    logging.info(f"Model directory is \"{SETTINGS['MODEL_DIR_FULL']}\". Content: {content}")
    wait = False
    force = False

    # check origin
    bucket_path, _ = os.path.split(SETTINGS['S3_OBJECT_NAME'])
    if bucket_path != "" and not bucket_path.endswith('/'):
        bucket_path = bucket_path + '/'
    bucket_filename = os.path.join(SETTINGS['MODEL_DIR_FULL'], '_bucket.txt')
    try:
        with open(bucket_filename, "r") as _f:
            bucket = _f.read()
    except Exception:
        bucket = '-'
    if not bucket.startswith(SETTINGS['S3_BUCKET_NAME']) or not bucket.endswith(SETTINGS['S3_OBJECT_NAME']) or not str(SETTINGS['ENDPOINT']) in bucket:
        # different bucket -> delete old content
        force = True
    if SETTINGS['FORCE_DOWNLOAD'] == 'true':
        logging.info(f"FORCE_DOWNLOAD set -> deleting directory content!")
        force = True

    # drop files on local that do not match bucket
    for object in bucket_objects:
        bucket_file = object['Key']
        bucket_base = bucket_file[len(bucket_path):]  # filename relative to dir in bucket
        if bucket_file.endswith('/') or bucket_base not in filedir.keys():
            # object is dir or does not exist on local
            continue
        file_stat = filedir[bucket_base]
        if object['LastModified'] > file_stat['date'] or object['Size'] != file_stat['size'] or force:
            logging.info(f"File {bucket_file} in bucket differs from filesystem -> deleting")
            os.remove(file_stat['filepath'])
            wait = True
        filedir.pop(bucket_base)

    # loop on files on local that are not in bucket
    for k in filedir.keys():
        if filedir[k]['filepath'] != bucket_filename:
            logging.info(f"File {k} not in bucket -> deleting")
            os.remove(filedir[k]['filepath'])

    if wait:
        # wait a few seconds to ensure that file deletion has finished
        time.sleep(5)

    if SETTINGS['S3_OBJECT_NAME'].endswith('*'):
        for object in bucket_objects:
            if object['Key'].startswith(bucket_path):
                object_list.append(object['Key'])
    else:
        object_list.append(SETTINGS['S3_OBJECT_NAME'])

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
        
        model_file_base = object[len(bucket_path):]
        model_file_full = os.path.join(SETTINGS['MODEL_DIR_FULL'], model_file_base)
        if not os.path.isfile(model_file_full):
            object_path = model_file_base.split('/')
            index = 1
            while index < len(object_path):
                subpath = os.path.join(SETTINGS['MODEL_DIR_FULL'], *object_path[0:index])
                if not os.path.exists(subpath):
                    os.makedirs(subpath)
                    logging.info(f'Directory "{subpath}" created.')
                index = index + 1
            logging.info(f"Start downloading: {SETTINGS['S3_BUCKET_NAME']}/{object}  ->  {model_file_full}")
            
            if SETTINGS['PROVIDER'] == 'IBM':
                s3.download_file(SETTINGS['S3_BUCKET_NAME'], object, model_file_full)
            else:
                s3.download_file(SETTINGS['S3_BUCKET_NAME'], object, model_file_full)
            
            count = count + 1
        else:
            logging.info(f'Model file "{object}" already exists ({model_file_full})-> download skipped.')
    elapsed_time = time.time() - start_time
    logging.info(f'Download of {count} files successfully completed, elapsed time: {elapsed_time:.2f}s.')

    if force:
        with open(bucket_filename, "w") as _f:
            _f.write(f"{SETTINGS['S3_BUCKET_NAME']}|{str(SETTINGS['ENDPOINT'])}|{SETTINGS['S3_OBJECT_NAME']}")
        time.sleep(5)
        # wait a few seconds to ensure that file is closed
        logging.info(f'File {bucket_filename} written.')

    return True


def upload():
    global SETTINGS
    print(f"Transfering files from {SETTINGS['MODEL_DIR_FULL']} to bucket {SETTINGS['UPLOAD_BUCKET_NAME']}/{SETTINGS['UPLOAD_DIR']}\n")
    s3 = boto3.client('s3', aws_access_key_id=SETTINGS['UPLOAD_ACCESS_KEY_ID'], aws_secret_access_key=SETTINGS['UPLOAD_SECRET_ACCESS_KEY']) if SETTINGS['UPLOAD_ENDPOINT'] == None else \
            boto3.client('s3', aws_access_key_id=SETTINGS['UPLOAD_ACCESS_KEY_ID'], aws_secret_access_key=SETTINGS['UPLOAD_SECRET_ACCESS_KEY'], endpoint_url=SETTINGS['ENDPOINT'])
    for file_full in glob.iglob(SETTINGS['MODEL_DIR_FULL'] + '/**/*', recursive=True):
        if os.path.isfile(file_full):
            file = os.path.relpath(file_full, SETTINGS['MODEL_DIR_FULL'])
            if file == '_bucket.txt':
                continue
            object_name = ((SETTINGS['UPLOAD_DIR'] + '/') if SETTINGS['UPLOAD_DIR'] != None else '') + file
            logging.info(f'Copying file {file} to {object_name}')
            try:
              response = s3.upload_file(file_full, SETTINGS['UPLOAD_BUCKET_NAME'], object_name)
            except ClientError as e:
              logging.error(f"Error during upload: {str(response)}")
              return False
    return True



if __name__ == '__main__':
    #get_buckets()
    #exit()
    #get_bucket_contents("llama-models-for-eval")
    #exit()

    parser = argparse.ArgumentParser(
                    prog='ProgramName',
                    description='What the program does',
                    epilog='Text at the bottom of help')
    parser.add_argument('action', choices=[None, 'show', 'upload', 'buckets'], nargs='?')
    args = parser.parse_args()

    if args.action == 'buckets':
        get_buckets()
        exit()

    if args.action == 'show':
        get_bucket_contents(SETTINGS['S3_BUCKET_NAME'])
        exit()

    if args.action == 'upload':
        if not check_environment():
            exit(1)
        upload()
        exit()

    if not check_environment() or not load_model():
        # exit with error
        exit(1)
