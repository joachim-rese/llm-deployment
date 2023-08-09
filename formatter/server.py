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
            params = re.findall(data['regex'], text) if 'regex' in data.keys() and data['regex'].strip() != "" else [text]
        except Exception as e:
            return {'formatted': f"REGEX ERROR: {str(e)}"}
        
        print(f"params--> {str(params)}")
        
        index = 1
        for _param in params:
            _parts = [_part for _part in _param] if isinstance(_param, (tuple, list)) else [_param]
            for _part in _parts:
                formatstr = formatstr.replace(f"#{str(index)}", _part)
                index = index + 1

        output = eval('f"'+formatstr+'"')
        return {'formatted': output}
        
if __name__ == '__main__':
    _host = os.getenv('HOST')
    _port = os.getenv('PORT')
    app.run(host=_host if _host != None else '0.0.0.0', port=_port if _port != None else '8080')