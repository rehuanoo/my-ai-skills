from flask import Flask,redirect, url_for,request,render_template
from flask_cors import CORS
# 实例化app应用
app = Flask(__name__)
CORS(app)
# 定义首页路由
@app.route('/')
def hello_world():
    return 'Hello World!'

# 定义一个产品路由
@app.route('/news')
def news():
    return '<p>news page</p>'


# 定义一个路由的另一种办法
def product():
    return '<h1>product page</h1>'
app.add_url_rule('/product', view_func=product)

@app.route('/user/admin')
def admin():
    return '<h1>hello admin</h1>'
 
@app.route('/user/user')
def user():
    return '<h1>hello user</h1>'

@app.route('/usercontent/<userType>')
def usercontent(userType):
    print(url_for('admin'))
    if userType == 'admin':
        return redirect(url_for('admin'))
    else:
        # return redirect(url_for('user'))等于
        return redirect('/user/user')


@app.route('/login',methods=['GET','POST'])
def login():
    
    if request.method == 'GET':
        return render_template('index.html')
#         return '''
#      <form action="/login" method="post">
#     <input type="text" name="username" placeholder="请输入用户名">
#     <input type="password" name="password" placeholder="请输入密码">
#     <button type="submit">登录</button>
#   </form>
# '''
    elif request.method == 'POST':
        fruits=['apple','banana','orange','梨子']
        userDict = {'username':'zs','age':'18','gender':'男','fruits':fruits}
        # 使用请求对象获取post提交的数据
        user=request.form.get('username')
        # 获取get提交的gender数据
        gender=request.args.get('gender')
        print(gender)
        if user == 'admin':
            return redirect(url_for('admin'))
        else:
            # return redirect(url_for('user'))
            return render_template('user.html',username=user,gender=gender,userDict=userDict)
        
@app.route('/api/weather')
def weather1():
    # 获取get提交的参数
    city=request.args.get('city')
    return '{"city":"'+city+'","temperature":30}'

@app.route('/weather')
def weather():
   return render_template('weather.html')


    

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0',port=8080) 
