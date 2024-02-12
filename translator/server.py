import os
from flask import Flask, request, json 
import time
import requests

app = Flask(__name__)

languages = None

sap_translation_apikey = os.getenv('SAP_TRANSLATION_APIKEY') or ''
sap_translation_url = os.getenv('SAP_TRANSLATION_URL') or ''
sap_translation_stalled = 0

 # translate a document
def sap_translate(text, lang_from="", lang_to="en-US"):
    global sap_translation_apikey, sap_translation_url, sap_translation_stalled
    if lang_from == lang_to:
        return (lang_from, text)
    
    if sap_translation_stalled > 0:
        diff = time.time() - sap_translation_stalled
        if diff > 60:
            sap_translation_stalled = 0
    if sap_translation_stalled < 1:

        if sap_translation_url == '':
            return ('', 'ERROR: translation')

        headers =  {"apikey": sap_translation_apikey, "Content-Type": "application/json"}
        data = { "sourceLanguage": lang_from, "targetLanguage": lang_to, "contentType": "text/plain", "encoding": "plain", "strictMode": False, "data": text }
        response = requests.post(sap_translation_url+'/translation', data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            return (response.json()['sourceLanguage'], response.json()['data'])
        else:
            sap_translation_active = False
            print(f"Call to translation service failed with http status {str(response.status_code)}")
            return ('', 'ERROR: translation')

# get available languages
def get_languages():
    global sap_translation_apikey, sap_translation_url
    headers =  {"apikey": sap_translation_apikey}
    response = requests.get(sap_translation_url+'/languages', headers=headers)
    if response.status_code == 200:
        #print("gl-->" + str(response.json()['languages']))
        return response.json()['languages']
    else:
        print(f"Call to translation service failed with http status {str(response.status_code)}")
        return [{'bcpcode': 'en-US', 'name': 'English', 'to': ['en-US']}]

@app.route('/translate', methods = ['POST'])
def translate():
    global languages

    if request.method == 'POST':
        data = json.loads(request.data)

        print("Payload received: " + str(data))
        if 'payload' in data:
            payload = { **data['payload']}
            text = payload

            to_en = True

            if 'output' in text:
                text = text['output']                  
                if 'generic' in text and len(text['generic']) > 0:
                    text = text['generic'][0]
                    to_en = False

            else:
                if 'input' in text:
                    text = text['input']
            
            if 'text' in text and isinstance(text['text'],str):
                if languages == None:
                    languages_all = get_languages()
                    lang_enus = [l for l in languages_all if l['bcpcode'] == 'en-US']
                    languages = (lang_enus + [l for l in languages_all if l['bcpcode'] in lang_enus[0]['to']]) if len(lang_enus) > 0 else [{'bcpcode': 'en-US', 'name': 'not found'}]

                if not 'context' in payload:
                    payload['context'] = {}
                if not 'skills' in payload['context']:
                    payload['context']['skills'] = {}
                user_defined = payload['context']['skills']

                if 'actions skill' in user_defined:
                    user_defined = user_defined['actions skill']
                else:
                    if 'dialog skill' in user_defined:
                        user_defined = user_defined['dialog skill']
                    else:
                        user_defined['actions skill'] = {}
                        user_defined = user_defined['actions skill']
                
                if not 'user_defined' in user_defined:
                    user_defined['user_defined'] = {}

                user_defined = user_defined['user_defined']
                
                lang = user_defined['language'] if 'language' in user_defined else ''
                lang_from = lang if to_en else 'en-US'
                lang_to = 'en-US' if to_en or lang =='' else lang

                print(f"text: {text['text']}, lang_from: {lang_from}, lang_to: {lang_to}")
                
                (lang, text['text']) = sap_translate(text['text'], lang_from, lang_to)
                if to_en:
                    user_defined['language'] = lang

            return { 'payload': payload }
        
        else:
            return {'payload': {'text': ''}}
      
if __name__ == '__main__':
    _host = os.getenv('HOST')
    _port = os.getenv('PORT')
    app.run(host=_host if _host != None else '0.0.0.0', port=_port if _port != None else '8080')