import os
import sys
from flask import Flask, request, json 
import time
import datetime
import requests
import pickle
import base64

app = Flask(__name__)

url = os.getenv('SERVICE_URL')
if url == None:
    url = 'https://eu-de.ml.cloud.ibm.com/ml/v4/deployments/<servicename>/predictions?version=2021-05-01'

apikey = os.getenv('SERVICE_APIKEY')

auth_url = os.getenv('AUTH_URL')
if auth_url == None:
    auth_url = 'https://iam.cloud.ibm.com/identity/token'



expires_at = 0
headers = {}

def log(message, sev = 'I'):
    sys.stderr.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S ") + sev + " " + str(message) + "\n")



@app.route('/<servicename>', methods = ['POST'])
def relay(servicename):
    global headers, expires_at

    http_status = 200
    if request.method == 'POST':

        if time.time() >= expires_at:
            auth_payload = {'grant_type': 'urn:ibm:params:oauth:grant-type:apikey', 'apikey': apikey}
            token_response = requests.post(auth_url, data=auth_payload)
            if not token_response.status_code == 200:
                response = {'status': f"auth token request failed with status {str(token_response.status_code)}"}
                return response, 500
            token_data = token_response.json()
            headers = {'Authorization': f"Bearer {token_data['access_token']}"}
            expires_at = time.time() + token_data['expires_in'] - 30
            log('[AUTH] new token')

        data = json.loads(request.data)
        log('[REQUEST] ' + str(data))

        return_field = None
        if 'input_data' in data:
            payload = data
            if len(data['input_data']) > 0 and 'fields' in data['input_data'][0]:
                try:
                    index = data['input_data'][0]['fields'].index('__return')
                    if len(data['input_data'][0]['values'][0]) > index:
                        return_field = data['input_data'][0]['values'][0].pop(index)
                    data['input_data'][0]['fields'].pop(index)
                except ValueError:
                    pass

        else:
            data_base64 = base64.b64encode(pickle.dumps(data)).decode("utf-8")
            payload = { 'input_data': [{'fields': ['base64'], 'values': [[data_base64]]}] }

        service_response = requests.post(url.replace('<servicename>', servicename), json=payload, headers=headers)

        if service_response.status_code == 200:
            try:
                service_data = service_response.json()
                if service_data['predictions'][0]['fields'][0] == 'base64':
                    response = pickle.loads(base64.b64decode(service_data['predictions'][0]['values'][0][0].encode('utf-8')))
                elif 'predictions' in service_data:
                    response = service_data
                else:
                    response = {'status': 'malformatted service response'}
                    http_status = 400
            except ValueError:
                response = {'status': 'malformatted service response'}
                http_status = 400
        else:
            response = {'status': f"service failed with status {str(service_response.status_code)}"}
            http_status = service_response.status_code
    else:
        response = {'status': 'method {request.method} not supported'}
        http_status = 404

    log('[RESPONSE] ' + str(response))
    if return_field:
        if not isinstance(return_field, list):
            return_field = [return_field]
        nav = response
        if 'predictions' in nav and len(nav['predictions']) > 0:
            nav = nav['predictions'][0]
        if 'values' in nav and len(nav['values']) > 0:
            nav = nav['values'][0]
            if isinstance(nav, list) and len(nav) > 0:
                nav = nav[0]
        result = {_return_field: nav[_return_field] if _return_field in nav else '' for _return_field in return_field}
        return result, http_status
    else:
        return response, http_status

if __name__ == '__main__':
    _host = os.getenv('HOST')
    _port = os.getenv('PORT')
    app.run(host=_host if _host != None else '0.0.0.0', port=_port if _port != None else '8080')