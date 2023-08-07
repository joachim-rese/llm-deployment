import os
from flask import Flask, request, json 

app = Flask(__name__)

@app.route('/format', methods = ['POST'])
def format():
       
    if request.method == 'POST':
        data = json.loads(request.data)
        formatstr = data['format'] if 'format' in data.keys() else '{#1}{#2}{#3}'
        parameter1 = data['parameter1'] if 'parameter1' in data.keys() else ""
        parameter2 = data['parameter2'] if 'parameter2' in data.keys() else ""
        parameter3 = data['parameter3'] if 'parameter3' in data.keys() else ""
        formatstr = formatstr.replace("#1", "parameter1").replace("#2", "parameter2").replace("#3", "parameter3")
        output = eval('f"'+formatstr+'"')
        return {'formatted': output}
        
if __name__ == '__main__':
    _host = os.getenv('HOST')
    _port = os.getenv('PORT')
    app.run(host=_host if _host != None else '0.0.0.0', port=_port if _port != None else '8080')