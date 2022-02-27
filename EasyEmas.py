
from os import path
import os
from tkinter import E
import pandas as pd
import datetime
import time

import requests



#url request templates
URL_LOGIN = "https://emas.ui.ac.id/login/token.php"
URL_WEBSERVICE = "https://emas.ui.ac.id/webservice/rest/server.php"

#true = have not login yet
#false = login completed
login_status = True

while(login_status):
    #checking previous login by login_token.token file
    if path.exists("login_token.token") == True:
        f= open("login_token.token","r")
        if f.mode == 'r':
            login_token = f.read()
        f.close()
        try:
            #testing if the token is correct
            if requests.get(URL_WEBSERVICE, {'wstoken': login_token,'wsfunction' : 'core_webservice_get_site_info', 'moodlewsrestformat' : 'json'}).json()['errorcode'] == 'invalidtoken':
                #removing token if false
                if os.path.exists("login_token.token"):
                    try:
                        os.remove(f"login_token.token")
                    except Exception:
                        print('cant remove login_token.token . is there any active process using it?')
                        exit()                
                print('Token Invalid, please login again')
                login_status = True
        except Exception:
            #prints welcome and exits the loop if there is no 'errorcode' in the request. this is pretty janky way to do it
            print('Login successful using the saved token with the username of ' + 
                    requests.get(URL_WEBSERVICE, {'wstoken': login_token,'wsfunction' : 'core_webservice_get_site_info', 'moodlewsrestformat' : 'json'}).json()['username'])
            login_status = False
            pass



    else:
        #if login_token.token doesnt exist, try to create one.
        login = input("Enter Username : ")
        loginpass =  input("Enter Password : ")
        
        try:
            #testing if the token is correct
            if requests.get(URL_LOGIN, {'username': login,'password' : loginpass,'service' : 'moodle_mobile_app'}).json()['errorcode'] == 'invalidlogin':
                print('Token Invalid, please try again')
                continue
        except Exception:
            pass
        

        #getting the token
        login_response = requests.get(URL_LOGIN, {'username': login,'password' : loginpass,'service' : 'moodle_mobile_app'})
        
        #deleting username and password
        login = 0
        loginpass =  0

        #set the login_token var with the login_response, saves it to login_token.token
        login_token = login_response.json()['token']
        f= open("login_token.token","w+")
        f.write(login_token)
        f.close()
        print('Login successful with the username of ' + 
            requests.get(URL_WEBSERVICE, {'wstoken': login_token,'wsfunction' : 'core_webservice_get_site_info', 'moodlewsrestformat' : 'json'}).json()['username'] + 
            ' . Saving login token')
        login_status = False

#dataframe for assignments
df = pd.DataFrame([],columns =  ["MATKUL", "NAMA TUGAS", "DEADLINE TANGGAL","DEADLINE JAM", "STATUS", "TIMELEFT", "UNIXSTAMP"])

#getting the assignments for this token/user
assignment_response = requests.get(URL_WEBSERVICE, {'wstoken': login_token,'wsfunction' : 'mod_assign_get_assignments', 'moodlewsrestformat' : 'json'})



#loop trough each courses to get the submission status
for x in assignment_response.json()['courses']:
    #preventing submission status request for the entire assigments that has ever assigned to this user by limiting the submission status request to only the non overdue assignments. i dont know how to explain this clearly
    for y in x['assignments']:
        #timing is using unix timestamps
        if y['duedate'] > int(time.time()):
            #requesting submission response, sometimes it returns unknown for no reason. also accomodate for singular and group submission.
            submission_response = requests.get(URL_WEBSERVICE, {'wstoken': login_token,'wsfunction' : 'mod_assign_get_submission_status', 'moodlewsrestformat' : 'json', 'assignid' : y['id']})
            try:
                sub_status = submission_response.json()['lastattempt']['submission']['status']
            except Exception:
                try:
                    sub_status = submission_response.json()['lastattempt']['teamsubmission']['status']
                    
                except Exception:
                    sub_status ='Unknown'
                    pass
                pass
                
            #creating a new entry for the submission
            df.loc[-1] = [
                x['fullname'],
                y['name'], 
                datetime.date.fromtimestamp(y['duedate']).isoformat(),
                datetime.datetime.fromtimestamp(y['duedate']).time().isoformat(),
                sub_status,
                str(datetime.datetime.fromtimestamp(y['duedate']) - datetime.datetime.fromtimestamp(time.time())).split(".")[0],
                y['duedate']
            ]  

            #sorting the submission by the closest to the current time, or the nearest deadline
            df = df.sort_values(by='UNIXSTAMP')  # sorting by index
            df.index = df.index + 1  # shifting index
            df = df.reset_index(drop=True)

#drops the table used for sorting the assignments      
df = df.drop(['UNIXSTAMP'], axis=1)      
print(df)

input("Press Enter to continue...")