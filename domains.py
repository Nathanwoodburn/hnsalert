import mysql.connector
from mysql.connector import Error
import dotenv
import os
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import re
import account

dotenv.load_dotenv()

db_config = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

def addDomain(userID:int, domain:str):
    # Get user domains
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT domains FROM users WHERE id = %s", (userID,))
    user = cursor.fetchall()
    cursor.close()
    conn.close()

    # Read json domains from first user
    user = user[0][0]
    userDomains = json.loads(user)

    # Check if domain is already in use
    for userDomain in userDomains:
        if (userDomain['name'] == domain):
            return False
        
    # Add domain to user
    userDomains.append({
        "name": domain,
        "status": "pending"
    })

    # Update user domains
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET domains = %s WHERE id = %s", (json.dumps(userDomains), userID))
    conn.commit()
    cursor.close()
    conn.close()
    return True


def verifyDomain(domain:str):
    # Remove any trailing slashes
    domain = domain.rstrip('/')
    # Remove any protocol
    domain = domain.replace('https://', '')
    domain = domain.replace('http://', '')
    domain = domain.lower()
    # Verify domain contains only valid characters
    if (re.match("^[a-z0-9.-]*$", domain) == None):
        return False
    return domain

def deleteDomain(userID:int, domain:str):
    # Get user domains
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT domains FROM users WHERE id = %s", (userID,))
    user = cursor.fetchall()
    cursor.close()
    conn.close()

    # Read json domains from first user
    user = user[0][0]
    userDomains = json.loads(user)

    # Check if domain is already in use
    for userDomain in userDomains:
        if (userDomain['name'] == domain):
            userDomains.remove(userDomain)
            break
        
    # Update user domains
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET domains = %s WHERE id = %s", (json.dumps(userDomains), userID))
    conn.commit()
    cursor.close()
    conn.close()
    return True

def syncDomains():
    # Verify connection to HSD node
    try:
        r = requests.get('http://x:' + os.getenv('HSD_API_KEY') + '@' + os.getenv('HSD_IP') 
                         + ':' + os.getenv('HSD_PORT'))
        if (r.status_code != 200):
            return "HSD node is not responding"
        # Check to make sure the node is synced
        data = r.json()
        if (data['chain']['progress'] < 0.999):
            return "HSD node is not synced"

    except:
        return False

    # Get all users
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, domains FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    # Loop through users
    for user in users:
        userID = user[0]
        userDomains = json.loads(user[1])
        # Loop through user domains
        for userDomain in userDomains:
            customNotifications = False
            if 'notifications' in userDomain:
                customNotifications = userDomain['notifications']

            # Check if domain is pending
            if (userDomain['status'] == 'pending'):
                try:
                    r = requests.post('http://x:' + os.getenv('HSD_API_KEY') + '@' + os.getenv('HSD_IP') 
                         + ':' + os.getenv('HSD_WALLET_PORT'), json={'method': 'importname', 'params': [userDomain['name']]})
                    
                    if (r.status_code == 200):
                        # Update domain status
                        userDomain['status'] = 'added'
                    
                        # Set some defaults
                        userDomain['transfering'] = 0
                        userDomain['next'] = 'none'
                        userDomain['when'] = 0
                        userDomain['records'] = ''

                        # Update user domains
                        conn = mysql.connector.connect(**db_config)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE users SET domains = %s WHERE id = %s", (json.dumps(userDomains), userID))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                except:
                    pass
            
            # Get domain info
            r = requests.post('http://x:' + os.getenv('HSD_API_KEY') + '@' + os.getenv('HSD_IP') 
                         + ':' + os.getenv('HSD_PORT'), json={'method': 'getnameinfo', 'params': [userDomain['name']]})
            if (r.status_code == 200):
                data = r.json()
                print(json.dumps(data, indent=4))
                # Check if domain is registered
                info = data['result']['info']
                if (info == None):
                    # Update domain status
                    userDomain['status'] = 'error'
                    userDomain['transfering'] = 0
                    userDomain['next'] = 'open for bidding'
                    userDomain['when'] = 0
                    # Update user domains
                    conn = mysql.connector.connect(**db_config)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET domains = %s WHERE id = %s", (json.dumps(userDomains), userID))
                    conn.commit()
                    cursor.close()
                    conn.close()
                    continue

                if (userDomain['transfering'] != info['transfer']):
                    # Update domain status
                    if (notify('transfer', customNotifications, userID)):
                            alert('transfer', userDomain['name'], userID)
                    userDomain['transfering'] = info['transfer']

                if (userDomain['records'] != info['data'] and userDomain['records'] != ''):
                    # Update domain status
                    if (notify('dns', customNotifications, userID)):
                        alert('dns', userDomain['name'], userID)
                userDomain['records'] = info['data']

                
                if 'stats' in info:
                    if 'blocksUntilExpire' in info['stats']:
                        # Update domain status
                        userDomain['next'] = 'expires'

                        previous = userDomain['when']
                        userDomain['when'] = info['stats']['blocksUntilExpire'] 

                        if (crossTimeAlert(previous, userDomain['when']) or True):
                            if (notify('expire', customNotifications, userID,
                                       crossTimeAlert(previous, userDomain['when']))):
                                alert('expire', userDomain['name'], userID, crossTimeAlert(previous, userDomain['when']))

                    elif 'blocksUntilBidding' in info['stats']:
                        # Update domain status
                        userDomain['next'] = 'opens for bidding'
                        userDomain['when'] = info['stats']['blocksUntilBidding']

                # Update user domains
                conn = mysql.connector.connect(**db_config)
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET domains = %s WHERE id = %s", (json.dumps(userDomains), userID))
                conn.commit()
                cursor.close()
                conn.close()

                
                    
            else:
                return "Failed to get info about domain: " + userDomain['name'] + "<br>" + str(r.text)
    return "Finished syncing domains"

def alert(event,domain,userID, time=False):
    notification_name = {
        'transfer': 'transfer_notifications',
        'dns': 'edit_notifications'
    }

    # Get user
    user = account.getUserFromID(userID)
    # Check if domain has custom notifications
    customNotifications = False
    for domainInfo in user['domains']:
        if (domainInfo['name'] == domain):
            if 'notifications' in domainInfo:
                customNotifications = domainInfo['notifications']
            break
    
    if (customNotifications):
        # Send custom notification
        if (event != 'expire'):
            send(customNotifications[notification_name[event]], domain, event,userID)
        elif (time == 'month'):
            send(customNotifications['expiry_month'], domain, event,userID)
        elif (time == 'week'):
            send(customNotifications['expiry_week'], domain, event,userID)
        
    else:
        if (event != 'expire'):
            send(user['notifications'][notification_name[event]], domain, event,userID)
        elif (time == 'month'):
            send(user['notifications']['expiry_month'], domain, event,userID)
        elif (time == 'week'):
            send(user['notifications']['expiry_week'], domain, event,userID)

def send(providers,domain:str,event,userID):
    user = account.getUserFromID(userID)

    title = {
        'transfer': 'Transfer Alert for {domain}',
        'dns': '{domain} has had a DNS update',
        'expire': '{domain} will expire soon'
    }
    content = {
        'transfer': 'The domain {domain} has started a transfer to a new wallet',
        'dns': 'The domain {domain} has had a DNS update',
        'expire': '{domain} will expire in {time}'
    }


    title = title[event].replace('{domain}',domain.capitalize()+'/')
    content = content[event].replace('{domain}',domain.capitalize()+'/')
    if (event == 'expire'):
        domainInfo = getCachedDomainInfo(domain)
        content = content.replace('{time}',blocksToTime(domainInfo['when']))

    if (providers['email']):
        account.sendEmail(user['email'],title,content)
    if (providers['discord']):
        if ('discord' in user['notifications']):
            account.sendDiscordWebhook(user['notifications']['discord'],title,content)


def notify(event, customNotifications, userID, time=False):
    # TODO this will check if the user has notifications enabled for the event
    # This should make the sync a bit faster but it's not a huge deal
    if (event == 'transfer'):
        return True
    if (event == 'dns'):
        return True    
    if (event == 'expire'):
        return True

    return True

def crossTimeAlert(was, now):
    # Check for each of these times to see if we should alert
    month = 4320
    week = 1008

    # If the time crossed the month mark
    if (was > month and now <= month):
        return "month"
    # If the time crossed the week mark
    if (was > week and now <= week):
        return "week"
    
    return False



def getCachedDomainInfo(domain):
    # Get domain info from user domains
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT domains FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    # Loop through users
    for user in users:
        userDomains = json.loads(user[0])
        # Loop through user domains
        for userDomain in userDomains:
            if (userDomain['name'] == domain):
                return userDomain
    return False



def blocksToTime(blocks):
    # Get minutes
    minutes = blocks * 10
    years, minutes = divmod(minutes, 525600)
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)

    # Build the string
    time_string = ""
    if years:
        time_string += f"{years} {'year' if years == 1 else 'years'}, "
    if days:
        time_string += f"{days} {'day' if days == 1 else 'days'}, "
    if hours and not years:
        time_string += f"{hours} {'hour' if hours == 1 else 'hours'}, "
    if minutes and not years and not days:
        time_string += f"{minutes} {'min' if minutes == 1 else 'mins'}"

    if not time_string:
        time_string = "now"
    return time_string.rstrip(', ')
