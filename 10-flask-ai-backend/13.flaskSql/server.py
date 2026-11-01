from flask import Flask, request, render_template,redirect,url_for,make_response, session,g
import sqlite3

app = Flask(__name__)


# 设置密钥
app.secret_key = 'dev-only-change-me'

DATABASE = './database/sqlite.db'

def connect_db():
    return sqlite3.connect(DATABASE)

# 每次请求前连接数据库
@app.before_request
def before_request():
    g.db = connect_db()

# 每次请求后关闭数据库
@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

def list_user(users):
    lists = []
    for user in users:
        lists.append({
            'id': user[0],
            'username': user[1],
            'password': user[2],
            'gender': user[3],
            'avater': user[4],
            'age': user[5],
            'isDelete': user[6],
            'score':user[7],
            'project':user[8]
        })
    return lists
@app.route('/')
def index():
    # 数据查找
    query = 'SELECT * FROM user'
    cursor = g.db.execute(query)
    users = cursor.fetchall()
    users = list_user(users)
    # print(users)
    return render_template('index.html', users=users)
    

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        score = request.form.get('score')

        # 从数据库中查找username是否存在
        query = "SELECT * FROM user WHERE username = '%s'" % username
        cursor = g.db.execute(query)
        user = cursor.fetchall()
        if len(user) > 0:
            info = {
                'title': '注册失败',
                'content': '用户名已存在',
                'path': '/register',
                'img': 'payfail'
            }
            res = make_response(render_template('info.html', info=info))
            return res
        

        # 编写插入语句
        query = "INSERT INTO user(username,password,score) values ( '%s' , '%s' ,'%s')" % (username,password,score)
        g.db.execute(query)
        g.db.commit()
        info={
            'title':'注册成功',
            'content':'欢迎回家',
            'path':'/user',
            'img':'paysuccess'
        }
        res =make_response(render_template('info.html',info=info)) 
        session['username'] = username
        return res



@app.route('/editUser', methods=['GET', 'POST'])
def editUser():
    if request.method == 'GET':
        username = session.get('username')
        # 通过username查找用户信息
        query = "SELECT * FROM user WHERE username = '%s'" % username
        user = g.db.execute(query).fetchone()
        userDict={
            'id': user[0],
            'username': user[1],
            'password': user[2],
            'gender': user[3],
            'avater': user[4],
            'age': user[5],
            'isDelete': user[6],
            'score':user[7],
            'project':user[8]
        }
        return render_template('editUser.html', user=userDict)
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        score = request.form.get('score')
        query = "UPDATE user SET password = '%s',score='%s' WHERE username = '%s'" % (password,score,username)
        g.db.execute(query)
        g.db.commit()
        info = {
                'title': '修改成功',
                'content': '修改成功',
                'path': '/editUser',
                'img': 'payfail'
            }
        res = make_response(render_template('info.html', info=info))
        return res
        
        # 从数据库中查找username是否存在
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        # 从数据库中查找username，password是否对应，并且isDelete is null
        query = "SELECT * FROM user WHERE username = '%s' AND password = '%s' AND isDelete is null" % (username, password)
        user = g.db.execute(query).fetchone()
        userDict={
            'id': user[0],
            'username': user[1],
            'password': user[2],
            'gender': user[3],
            'avater': user[4],
            'age': user[5],
            'isDelete': user[6],
            'score':user[7],
            'project':user[8]
        }
        # print(users)
        if len(userDict) > 0:
            session['username'] = username
            info = {
                'title': '登录成功',
                'content': '欢迎回家',
                'path': '/user',
                'img': 'paysuccess'
            }
            # 跳转到editUser页面，进行修改密码
            res = make_response(render_template('editUser.html', user=userDict))
            return res
            # return render_template('editUser.html', user=users)
        else:
            info = {
                'title': '登录失败',
                'content': '用户名或密码错误',
                'path': '/login',
                'img': 'payfail'
            }
            res = make_response(render_template('info.html', info=info))

        


@app.route('/user')
def user():
    username = session.get('username')
    return render_template('user.html',username=username)



if __name__ == '__main__':
    app.run(debug=True)