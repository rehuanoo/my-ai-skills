from flask import Flask, request, render_template,redirect,url_for,make_response, session


app = Flask(__name__)

@app.route('/')
def index():
    return 'helloworld'


@app.route('/user')
def user():
    #获取登录信息，返回具体的用户数据
    #获取cookie的登录凭证
    username = request.cookies.get('username')
    islogin = request.cookies.get('islogin')
    pass
    return '用户界面，欢迎：'+username

@app.route('/failure')
def failure():
    return '登录失败'

@app.route('/logout')
def logout():
    res = make_response('退出登录')
    res.delete_cookie('username')
    res.delete_cookie('islogin')
    return res
    

@app.route('/login',methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    day = request.form.get('remember')
    if username == 'admin' and password == '123456':
        # 登录成功
        res = redirect(url_for('user'))

        time = 60*60*24*int(day)
        # 有效时间max_age是按秒来算
        res.set_cookie('username',username,max_age=time)
        res.set_cookie('islogin','true',max_age=time)

        # res = make_response('登录成功')
        # res.set_cookie('username',username)
        # res.set_cookie('islogin','true')
        return res
    else:
        return redirect(url_for('failure'))
    

if __name__ == '__main__':
    app.run(debug=True)