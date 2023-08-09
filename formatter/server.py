import os
import re
from flask import Flask, request, json 

app = Flask(__name__)

@app.route('/format', methods = ['POST'])
def format():
       
    if request.method == 'POST':
        data = json.loads(request.data)
        formatstr = data['format'] if 'format' in data.keys() else '{#1}{#2}{#3}'
        text = data['text'] if 'text' in data.keys() else ""
        
        try:
            params = re.findall(data['regex'], text) if 'regex' in data.keys() and data['regex'] != "" else [text]
        except Exception as e:
            return {'formatted': f"REGEX ERROR: {str(e)}"}
        
        for _idx, _param in enumerate(params):
            formatstr = formatstr.replace(f"#{str(_idx+1)}", _param)

        output = eval('f"'+formatstr+'"')
        return {'formatted': output}
        
if __name__ == '__main__':
    _host = os.getenv('HOST')
    _port = os.getenv('PORT')
    app.run(host=_host if _host != None else '0.0.0.0', port=_port if _port != None else '8080')