import boto3
import os
import logging
import time

logging.getLogger().setLevel(logging.INFO)

# global variables
S3_ACCESS_KEY_ID =  os.getenv('s3_access_key_id')
S3_SECRET_ACCESS_KEY = os.getenv('s3_secret_access_key')
S3_BUCKET_NAME = os.getenv('s3_bucket_name')
S3_OBJECT_NAME = os.getenv('s3_object_name')

MODEL_DIR = os.getenv('model_dir')
MODEL_FILE = os.getenv('model_file')
STORE_DIR = os.getenv('STORE_DIR')



def missing_environment(var1, var2=None):
    if var2 == None:
        logging.error(f'Environment variable "{var1}" not set.')
    else:
        logging.error(f'Neither environment variable "{var1}" nor "{var2}" is set.')
    return False

def check_environment():
    global STORE_DIR, MODEL_DIR, MODEL_FILE, MODEL_DIR_FULL, MODEL_FILE_FULL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_OBJECT_NAME
    if STORE_DIR == None:
        STORE_DIR = '/store'
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
    MODEL_DIR_FULL = os.path.join(STORE_DIR, 'checkpoints', MODEL_DIR)
    MODEL_FILE_FULL = os.path.join(MODEL_DIR_FULL, MODEL_FILE) 
    return True

def check_keys():
    global STORE_DIR, MODEL_DIR, MODEL_FILE, MODEL_DIR_FULL, MODEL_FILE_FULL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_OBJECT_NAME
    if S3_ACCESS_KEY_ID == None:
        return missing_environment('s3_access_key_id')
    if S3_SECRET_ACCESS_KEY == None:
        return missing_environment('s3_secret_access_key')
    if S3_BUCKET_NAME == None:
        return missing_environment('s3_bucket_name')
    return True



def load_model():
    global STORE_DIR, MODEL_DIR, MODEL_FILE, MODEL_DIR_FULL, MODEL_FILE_FULL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_OBJECT_NAME
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
    if not os.path.isfile(MODEL_FILE_FULL):
        logging.info(f'Start downloading: {S3_BUCKET_NAME}/{S3_OBJECT_NAME}')
        if not check_keys():
            return False
        s3 = boto3.client('s3', aws_access_key_id=S3_ACCESS_KEY_ID, aws_secret_access_key=S3_SECRET_ACCESS_KEY)
        start_time = time.time()
        s3.download_file(S3_BUCKET_NAME, S3_OBJECT_NAME, MODEL_FILE_FULL)
        elapsed_time = time.time() - start_time
        logging.info(f'Download of file "{MODEL_FILE_FULL}" successfully completed, elapsed time: {elapsed_time:.2f}s.')
    else:
        logging.info(f'Model file "{MODEL_FILE_FULL}" exists already -> download skipped.')
    return True



if __name__ == '__main__':
    if not check_environment() or not load_model():
        # exit with error
        exit(1)
