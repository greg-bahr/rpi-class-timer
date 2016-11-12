# This is a timer for flashing a light in Mr. Langston's class.
# This timer polls google calendar for an event on the current day, and uses
# that event to set the schedule for the light flashing on that day.
# Schedules can be changed or created in the config.ini file that comes with
# this script.

# Made by Greg Bahr

from __future__ import print_function
import httplib2
import os
import time
import datetime
import RPi.GPIO as GPIO

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from ConfigParser import SafeConfigParser

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'RPI Class Timer'
pin = 24

def load_schedules():
    config = SafeConfigParser()
    config.read("config.ini")
    schedules = {}
    for section in config.sections():
        schedules[section] = {}
        for (key, val) in config.items(section):
            schedules[section][key] = datetime.datetime.now().replace(hour=int("{:0>2}".format(val.split(":")[0])), minute=int(val.split(":")[1]), second=0, microsecond=0)
    print("Schedules loaded.\n")
    return schedules

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'rpi-class-timer.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def get_current_schedule(service):
    today = datetime.date.today().strftime('%Y-%m-%d')+'T00:00:00Z'
    tommorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')+'T00:00:00Z'
    schedules = load_schedules()
    schedule = {}

    events = service.events().list(
        calendarId='primary', timeMin=today, timeMax=tommorrow, singleEvents=True,
        orderBy='startTime').execute()

    print("Listing events on " + today[0:10] + ".\n")
    for event in events['items']:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start,":", event['summary'])
        if(event['summary'] in schedules):
            schedule = []
            for hour in schedules[event['summary']]:
                schedule.append(schedules[event['summary']][hour])
    return schedule

def setup_GPIO():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

def main():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    tommorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    setup_GPIO()

    schedule = get_current_schedule(service)
    if not schedule:
        print("Schedule not found. Will look again.\n")
        time.sleep(5)
        main()
    print("\nSetting today's schedule to ", schedule)
    while datetime.date.today().strftime('%Y-%m-%d') != tommorrow:
        print("\n",datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ";", "Checking time.")
        current_time = datetime.datetime.now().replace(second=0, microsecond=0)
        for classend in schedule:
            if (classend - datetime.timedelta(minutes=8)) == current_time:
                print("\n" + "Flashing Light.")
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(480)
                print("Light off.")
                GPIO.output(pin, GPIO.LOW)

        time.sleep(10)
    main()

if __name__ == '__main__':
    main()
