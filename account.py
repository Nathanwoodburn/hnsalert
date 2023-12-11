import mysql.connector
from mysql.connector import Error
import dotenv
import os
import json
import time
from email_validator import validate_email, EmailNotValidError
import bcrypt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

dotenv.load_dotenv()

db_config = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

def verifyUser(userToken:str):
    # Get userID from userToken
    if (userToken.count('$') != 1):
        return False
    userToken = userToken.split('$')
    userID = userToken[0]
    userToken = userToken[1]
        
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT user_token FROM users WHERE id = %s", (userID,))
    user = cursor.fetchall()
    cursor.close()
    conn.close()

    # Read json token from first user
    user = user[0][0]
    userTokens = json.loads(user)
    for token in userTokens:
        if (token['token'] == userToken):
            if (token['expires'] > time.time()):
                return True
    
            
    return False


def createUser(email:str, password:str):
    # Check if email is valid
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        # email is not valid, exception message is human-readable
        return False

    # Check if email is already in use
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
    user = cursor.fetchall()
    cursor.close()
    conn.close()

    if (len(user) != 0):
        return False
    
    passwordHash = hashPassword(password)

    # Create user
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (email, password, admin, notifications, user_token, domains) VALUES (%s, %s, %s, %s, %s, %s)", (email, passwordHash, False, json.dumps({}), json.dumps([]), json.dumps([])))
    conn.commit()
    cursor.close()
    conn.close()

    return True


def login(email:str, password:str):
    # Check if email is valid
    try:
        valid = validate_email(email)
        email = valid.email
    except EmailNotValidError as e:
        # email is not valid, exception message is human-readable
        return False

    # Check if email is already in use
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM users WHERE email = %s", (email,))
    user = cursor.fetchall()
    cursor.close()
    conn.close()

    if (len(user) == 0):
        return False

    # Check if password is correct
    userID = user[0][0]
    if (checkPassword(password, user[0][1])):
        # Create new user token
        userToken = genToken()
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT user_token FROM users WHERE id = %s", (userID,))
        user = cursor.fetchall()
        cursor.close()
        conn.close()

        # Read json token from first user
        user = user[0][0]
        print(user)
        userTokens = json.loads(user)
        userTokens.append({'token': userToken, 'expires': time.time() + 86400})

        # Update user token
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET user_token = %s WHERE id = %s", (json.dumps(userTokens), userID,))
        conn.commit()
        cursor.close()
        conn.close()

        return str(userID) + '$' + userToken
    else:
        return False
    

def getUser(userToken:str):
    # Get userID from userToken
    if (userToken.count('$') != 1):
        return False
    userToken = userToken.split('$')
    userID = userToken[0]
    userToken = userToken[1]
        
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, admin, notifications, domains, created_at FROM users WHERE id = %s", (userID,))
    user = cursor.fetchall()
    cursor.close()
    conn.close()

    # Read json token from first user
    user = user[0]
    return {'id': user[0], 'email': user[1], 'admin': user[2], 'notifications': json.loads(user[3]), 'domains': json.loads(user[4]), 'created_at': user[5]}

def getUserFromID(userID:int):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, admin, notifications, domains, created_at FROM users WHERE id = %s", (userID,))
    user = cursor.fetchall()
    cursor.close()
    conn.close()

    # Read json token from first user
    user = user[0]
    return {'id': user[0], 'email': user[1], 'admin': user[2], 'notifications': json.loads(user[3]), 'domains': json.loads(user[4]), 'created_at': user[5]}

def logoutUser(userToken:str):
    pass


def hashPassword(password:str):
    # Use bcrypt to hash password
    password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    passwordHash = bcrypt.hashpw(password, salt)
    passwordHash = passwordHash.decode('utf-8')
    return passwordHash


def checkPassword(password:str, passwordHash:str):
    # Use bcrypt to check password
    password = password.encode('utf-8')
    passwordHash = passwordHash.encode('utf-8')
    if (bcrypt.checkpw(password, passwordHash)):
        return True
    else:
        return False
    
def genToken():
    # Generate a random token
    token = os.urandom(32)
    token = token.hex()
    return token

def updateNotifications(token, notifications):
    # Get userID from userToken
    if (token.count('$') != 1):
        return False
    token = token.split('$')
    userID = token[0]
    token = token[1]
        
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET notifications = %s WHERE id = %s", (json.dumps(notifications), userID,))
    conn.commit()
    cursor.close()
    conn.close()

    return True

def updateDomainNotifications(token, domain, notifications):
    # Get userID from userToken
    if (token.count('$') != 1):
        return False
    token = token.split('$')
    userID = token[0]
    token = token[1]
        
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT domains FROM users WHERE id = %s", (userID,))
    user = cursor.fetchall()
    cursor.close()
    conn.close()

    print(domain)
    print(notifications)

    # Read json token from first user
    user = user[0][0]
    user = json.loads(user)
    for userDomain in user:
        if (userDomain['name'] == domain):
            userDomain['notifications'] = notifications

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET domains = %s WHERE id = %s", (json.dumps(user), userID,))
    conn.commit()
    cursor.close()
    conn.close()

    return True

def updateNotificationProvider(token, provider,account):
    # Get userID from userToken
    if (token.count('$') != 1):
        return False
    token = token.split('$')
    userID = token[0]
    token = token[1]
        
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT notifications FROM users WHERE id = %s", (userID,))
    user = cursor.fetchall()
    cursor.close()
    conn.close()

    # Read json token from first user
    user = user[0][0]
    user = json.loads(user)
    user[provider] = account

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET notifications = %s WHERE id = %s", (json.dumps(user), userID,))
    conn.commit()
    cursor.close()
    conn.close()

    return True

def sendNotification(service, service_account, title, content):
    if (service == 'email'):
        sendEmail(service_account, title, content)
    elif (service == 'discord'):
        sendDiscordWebhook(service_account, title, content)
    elif (service == 'telegram'):
        pass
    else:
        return False
    
    return True

def sendEmail(email, title, content):
    sender_email = os.getenv('EMAIL_FROM')
    sender_password = os.getenv('EMAIL_PASSWORD')
    recipient_email = email

    # Create the MIME object
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = title

    # Add the email body
    body = content
    message.attach(MIMEText(body, 'plain'))

    # Connect to the SMTP server
    with smtplib.SMTP(os.getenv('EMAIL_HOST'), os.getenv('EMAIL_PORT')) as server:
        try:
            if (os.getenv('EMAIL_USE_TLS') == 'True'):
                server.starttls()
            
            server.login(sender_email, sender_password)

            # Send the email
            server.sendmail(sender_email, recipient_email, message.as_string())
            print("Email sent successfully.")
        except Exception as e:
            print(e)
            print("Email failed to send.")
    

def sendDiscordWebhook(webhook, title, content):
    # Create the webhook object
    headers = {
        'Content-Type': 'application/json'
    }

    payload = {
        "content": None,
        "embeds": [
            {
            "title": title,
            "description": content,
            "color": 5907868,
            "footer": {
                "text": "Powered by Woodburn",
                "icon_url": "https://woodburn.au/favicon.png"
            },
            # "timestamp": "2023-12-11T04:17:00.000Z"
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.localtime())
            }
        ],
        "username": "HNS Alert",
        "avatar_url": "https://woodburn.au/favicon.png",
        "attachments": []
        }
    response = requests.post(webhook, data=json.dumps(payload), headers=headers)

    if response.status_code == 204:
        print("Message sent successfully to Discord webhook.")
    else:
        print(f"Failed to send message to Discord webhook. Status code: {response.status_code}")

