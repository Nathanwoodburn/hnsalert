from flask import Flask, make_response, redirect, request, jsonify, render_template, send_from_directory
import dotenv
import os
import requests
import mysql.connector
from mysql.connector import Error
import sys
import time
import json
import account
import threading
import domains


dotenv.load_dotenv()

app = Flask(__name__)

db_config = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

service_prompts = {
    "discord": "https://discord.com/api/webhooks/11....",
    "telegram": "Telegram User ID",
    "email": "example@email.com"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    # Check if user is already logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            return redirect('/dashboard')
    
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')

    # Check if user is already logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            return redirect('/dashboard')

    # Check if user exists
    token = account.login(email, password)
    if (token):        
        resp = make_response(redirect('/dashboard'))
        resp.set_cookie('user_token', token)
        return resp
    else:
        return render_template('login.html', error='Invalid email or password')
    
@app.route('/signup')
def signup():
    # Check if user is already logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            return redirect('/dashboard')
    
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    password = request.form.get('password')

    # Check if user is already logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            return redirect('/dashboard')

    # Create user
    if (account.createUser(email, password)):
        resp = make_response(redirect('/dashboard'))
        resp.set_cookie('user_token', account.login(email, password))
        return resp

    else:
        return render_template('signup.html', error='Invalid email or password')
    
@app.route('/logout')
def logout():
    # Check if user is logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            resp = make_response(redirect('/'))
            resp.set_cookie('user_token', '', expires=0)
            return resp
    
    return redirect('/')
    

@app.route('/dashboard')
def dashboard():
    # Check if user is logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            # Get user data
            user = account.getUser(request.cookies.get('user_token'))
            error = ""
            if (request.args.get('error')):
                error = request.args.get('error')
            success = ""
            if (request.args.get('success')):
                success = request.args.get('success')


            # For each domain in domains get only the name
            domains = []
            for domain in user['domains']:
                domains.append(domain['name'])


            notifications = user['notifications']
            email = user['email'] + ' <a href="/test?service=email">Test</a>'

            if ('discord' in user['notifications']):
                discord = 'Linked (<a href="/link?service=discord">Change</a>) <a href="/test?service=discord">Test</a>'
            else:
                discord = "<a href='/link?service=discord'>Connect Discord</a>"

            if ('telegram' in user['notifications']):
                telegram = user['notifications']['telegram'] + ' (<a href="/link?service=telegram">Change</a>) <a href="/test?service=telegram">Test</a>'
            else:
                # telegram = "<a href='/link?service=telegram'>Connect Telegram</a>"
                telegram = "coming soon"

            expiry_week = {
                "email": True,
                "discord": False,
                "telegram": False
            }
            if ('expiry_week' in user['notifications']):
                expiry_week = user['notifications']['expiry_week']
            expiry_month = {
                "email": True,
                "discord": False,
                "telegram": False
            }
            if ('expiry_month' in user['notifications']):
                expiry_month = user['notifications']['expiry_month']
            transfer_notifications = {
                "email": True,
                "discord": False,
                "telegram": False
            }
            if ('transfer_notifications' in user['notifications']):
                transfer_notifications = user['notifications']['transfer_notifications']
            edit_notifications = {
                "email": True,
                "discord": False,
                "telegram": False
            }
            if ('edit_notifications' in user['notifications']):
                edit_notifications = user['notifications']['edit_notifications']



            return render_template('dashboard.html', domains=domains, notifications=notifications, 
                                   email=email, discord=discord, telegram=telegram,
                                      expiry_week=expiry_week,expiry_month=expiry_month,
                                      transfer=transfer_notifications,edit=edit_notifications,
                                      error=error,success=success,admin=user['admin'])
    
    return redirect('/login')

@app.route('/link')
def link_service():
    # Check if user is logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            # Get user data
            user = account.getUser(request.cookies.get('user_token'))
            service = request.args.get('service')
            service_prompt = service_prompts[service]
            if (service in user['notifications']):
                return render_template('link.html', service=service, account=user['notifications'][service],
                                       service_prompt=service_prompt)

            return render_template('link.html', service=service)
    
    return redirect('/login')

@app.route('/link', methods=['POST'])
def link_service_post():
    # Check if user is logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            # Get user data
            user = account.getUser(request.cookies.get('user_token'))
            service = request.args.get('service')
            account.updateNotificationProvider(request.cookies.get('user_token'), service, request.form.get('account'))
            
            return redirect('/dashboard')
    
    return redirect('/login')

@app.route('/test')
def test_service():
    # Check if user is logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            # Get user data
            user = account.getUser(request.cookies.get('user_token'))
            service = request.args.get('service')
            if (service in user['notifications']):
                notification_thread = threading.Thread(target=account.sendNotification, args=(service, user['notifications'][service], 'Test Notification','Test notification from HNS Alert'))
                notification_thread.start()
            elif (service == 'email'):
                notification_thread = threading.Thread(target=account.sendNotification, args=(service, user['email'], 'Test Notification','Test notification from HNS Alert'))
                notification_thread.start()
    
    return redirect('/dashboard')


@app.route('/notification-options', methods=['POST'])
def notification_options():
    # Check if user is logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            notifications = {
                "expiry_week": {
                    "email": False,
                    "discord": False,
                    "telegram": False
                },
                "expiry_month": {
                    "email": False,
                    "discord": False,
                    "telegram": False
                },
                "transfer_notifications": {
                    "email": False,
                    "discord": False,
                    "telegram": False
                },
                "edit_notifications": {
                    "email": False,
                    "discord": False,
                    "telegram": False
                }
            }        
            # Get user data
            user = account.getUser(request.cookies.get('user_token'))
            for key in request.form:
                if (key.endswith('_week')):
                    key = key[:-5]
                    notifications['expiry_week'][key] = True
                elif (key.endswith('_month')):
                    key = key[:-6]
                    notifications['expiry_month'][key] = True
                elif (key.endswith('_transfer')):
                    key = key[:-9]
                    notifications['transfer_notifications'][key] = True
                elif (key.endswith('_edit')):
                    key = key[:-5]
                    notifications['edit_notifications'][key] = True
            if not request.form.get('domain'):
                # Add user notifications
                if 'discord' in user['notifications']:
                    notifications['discord'] = user['notifications']['discord']

                account.updateNotifications(request.cookies.get('user_token'), notifications)
                return redirect('/dashboard')
            else:
                domain = request.form.get('domain').lower()                
                account.updateDomainNotifications(request.cookies.get('user_token'),
                                                  domain,notifications)
                return redirect('/' + domain + '/info')


#region domains
@app.route('/new-domain', methods=['POST'])
def new_domain():
    # Check if user is logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            # Get user data
            user = account.getUser(request.cookies.get('user_token'))
            domain = request.form.get('domain')
            # Verify domain
            domain = domains.verifyDomain(domain)
            if (domain):
                # Add domain to user
                if (domains.addDomain(user['id'], domain)):
                    return redirect('/dashboard?success=Domain added')
                else:
                    return redirect('/dashboard?error=Unable to add domain')
            else:
                return redirect('/dashboard?error=Invalid domain')
    
    return redirect('/login')

@app.route('/<domain>/delete')
def delete_domain(domain):
    # Check if user is logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            # Get user data
            user = account.getUser(request.cookies.get('user_token'))
            # Delete domain from user
            if (domains.deleteDomain(user['id'], domain)):
                return redirect('/dashboard?success=Domain deleted')
            else:
                return redirect('/dashboard?error=Unable to delete domain')
    
    return redirect('/login')

@app.route('/sync')
def sync_domains():
    # Check if user is logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            # Get user data
            user = account.getUser(request.cookies.get('user_token'))
            if (user['admin'] == False):
                return redirect('/dashboard?error=You are not an admin')

            # Sync domains
            result =domains.syncDomains()
            return redirect('/dashboard?error=' + result)
    
    return redirect('/login')

@app.route('/<domain>/info')
def domain(domain):
    # Check if user is logged in
    if 'user_token' in request.cookies:
        if (account.verifyUser(request.cookies.get('user_token'))):
            # Get domain info
            domainInfo = domains.getCachedDomainInfo(domain)
            print(domainInfo)
            if (domainInfo):
                if (domainInfo['status'] == 'pending'):
                    return redirect('/dashboard?error=Domain is pending<br>Please wait a few minutes')


                next = domainInfo['next']
                when_blocks = domainInfo['when']
                when_time = domains.blocksToTime(when_blocks)
                transfering = domainInfo['transfering'] == 1

                expiry_week = {
                "email": False,
                "discord": False,
                "telegram": False
                }
                expiry_month = {
                    "email": False,
                    "discord": False,
                    "telegram": False
                }
                transfer_notifications = {
                    "email": False,
                    "discord": False,
                    "telegram": False
                }
                edit_notifications = {
                    "email": False,
                    "discord": False,
                    "telegram": False
                }

                if ('notifications' in domainInfo):
                    if ('expiry_week' in domainInfo['notifications']):
                        expiry_week = domainInfo['notifications']['expiry_week']
                    
                    if ('expiry_month' in domainInfo['notifications']):
                        expiry_month = domainInfo['notifications']['expiry_month']
                    if ('transfer_notifications' in domainInfo['notifications']):
                        transfer_notifications = domainInfo['notifications']['transfer_notifications']
                    if ('edit_notifications' in domainInfo['notifications']):
                        edit_notifications = domainInfo['notifications']['edit_notifications']

                return render_template('info.html', domain=str(domain).capitalize(),
                                       next=next,when_blocks=when_blocks,when_time=when_time,
                                       transfering=transfering,expiry_week=expiry_week,
                                       expiry_month=expiry_month, transfer=transfer_notifications,
                                       edit=edit_notifications)
            else:
                return render_template('info.html', domain=str(domain).capitalize())
    
    return redirect('/login')



#endregion

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory('templates/assets', path)


# region Application
def db_init():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, email VARCHAR(255), password VARCHAR(255), admin BOOLEAN, notifications JSON, user_token JSON, domains JSON, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    cursor.close()
    conn.close()
    
    print('Database initialized', flush=True)


if __name__ == '__main__':
    db_init()
    app.run(host='0.0.0.0', port=5000, debug=True)

# endregion
