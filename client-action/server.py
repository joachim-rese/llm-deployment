import os
import sys
from flask import Flask, request, json 
#import time
import datetime
#import requests

app = Flask(__name__)



def log(message, sev = 'I'):
    sys.stderr.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S ") + sev + " " + str(message) + "\n")


@app.route('/client-action', methods = ['POST'])
def translate():
    global languages

    if request.method == 'POST':
        log('[REQUEST] ' + str(request.get_data()))
        data = json.loads(request.data)

        return { 'status': 'ook' }

#        event = ''
#        if 'event' in data and 'name' in data['event']:
#            if data['event']['name'] == 'message_received':
#                event = 'I'
#            if data['event']['name'] == 'message_processed':
#                event = 'O'

#        if 'payload' in data:
#            payload = { **data['payload']}
#            text = payload

#            to_en = True

#            if event == 'O' or (event == '' and 'output' in text):
#                text = text['output']                  
#                if 'generic' in text and len(text['generic']) > 0:
#                    text = text['generic'][0]
#                    to_en = False

#            else:
#                if event == 'I' or (event == '' and 'input' in text):
#                    text = text['input']
            
#            if 'text' in text and isinstance(text['text'],str):
#                if languages == None:
#                    languages_all = get_languages()
#                    lang_enus = [l for l in languages_all if l['bcpcode'] == 'en-US']
#                    languages = (lang_enus + [l for l in languages_all if l['bcpcode'] in lang_enus[0]['to']]) if len(lang_enus) > 0 else [{'bcpcode': 'en-US', 'name': 'not found'}]

#                if not 'context' in payload:
#                    payload['context'] = {}
#                if not 'skills' in payload['context']:
#                    payload['context']['skills'] = {}
#                user_defined = payload['context']['skills']

#                if 'actions skill' in user_defined:
#                    user_defined = user_defined['actions skill']
#                else:
#                    if 'dialog skill' in user_defined:
#                        user_defined = user_defined['dialog skill']
#                    else:
#                        user_defined['main skill'] = {}
#                        user_defined = user_defined['main skill']
                
#                if not 'user_defined' in user_defined:
#                    user_defined['user_defined'] = {}

#                user_defined = user_defined['user_defined']
                
#                lang = user_defined['language'] if 'language' in user_defined else ''
#                lang_from = lang if to_en else 'en-US'
#                lang_to = 'en-US' if to_en or lang =='' else lang
               
#                (lang, text['text']) = sap_translate(text['text'], lang_from, lang_to)
#                if to_en:
#                    user_defined['language'] = lang
#                    user_defined['language_en'] = text['text']
#                else:
#                    if 'language' in user_defined:
#                        del user_defined['language']
                    
#            log('[RESPONSE] ' + str(payload))

#            return { 'payload': payload }
        
#        else:
#            return {'payload': {'text': ''}}
      
if __name__ == '__main__':
    _host = os.getenv('HOST')
    _port = os.getenv('PORT')
    app.run(host=_host if _host != None else '0.0.0.0', port=_port if _port != None else '8080')