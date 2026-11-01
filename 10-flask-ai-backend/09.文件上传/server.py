from flask import Flask, request, render_template,redirect,url_for,make_response, session
import time
import json
app = Flask(__name__)

@app.route('/')
def index():
    return 'helloworld'



@app.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('imgAvater')
        filename = str(time.time()) + file.filename
        info={
            'title':'上传成功',
            'content':'成功上传'+file.filename,
            'path':'/upload',
            'img':filename
        }
        res =make_response(render_template('info.html',info=info))
        #拼接时间戳+文件名
        
        file.save('./static/upload/imgs/'+filename)
        return res
    else:
        return render_template('upload.html')



@app.route('/api/upload', methods=['POST'])
def apiUpload():
    file = request.files.get('imgAvater')
    username = request.form.get('username')
    password = request.form.get('password')
    filename = str(time.time()) + file.filename
    info={
        'title':'上传成功',
        'content':'成功上传'+file.filename,
        'path':'/upload',
        'img':filename,
        'username':username,
        'password':password
    }
    
    #拼接时间戳+文件名
    
    file.save('./static/upload/imgs/'+filename)
    return json.dumps(info)
    
    

if __name__ == '__main__':
    app.run(debug=True)