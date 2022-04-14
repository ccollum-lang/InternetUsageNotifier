# import the required libraries
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.auth.transport.requests
import requests

from twilio.rest import Client

import pickle
import os
import base64
import boto3
import email



#Creating session with Boto3
session = boto3.Session(
	aws_access_key_id = 'Your_Access_Key',
	aws_secret_access_key= 'Your_Secret_Key'
)

s3 = session.resource('s3')



# from bs4 import BeautifulSoup
# Define the SCOPES. If modifying it, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Twilio verification
account_sid = "Account_SID"
auth_token = "Auth_Token"

client = Client(account_sid, auth_token)

numbers = ['ENTER LIST OF NUMBERS']



def sendText(message):
	for number in numbers:
		client.messages.create(
			to = number,
			from_= "+12569523490",
			body = message
		)



def getEmails():

	os.chdir('/tmp')
	s3.Bucket('oauthtokens').download_file('credentials.json', 'credentials.json')

	try:
		s3.Bucket('oauthtokens').download_file('token.pickle', 'token.pickle')
	except:
		pass

	# Variable creds will store the user access token.
	# If no valid token found, we will create one.
	creds = None

	# The file token.pickle contains the user access token.
	# Check if it exists
	if os.path.exists('token.pickle'):

		# Read the token from the file and store it in the variable creds
		with open('token.pickle', 'rb') as token:
			creds = pickle.load(token)


	# If credentials are not available or are invalid, ask the user to log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
			creds = flow.run_local_server(port=0)

		# Save the access token in token.pickle file for the next run
		with open('token.pickle', 'wb') as token:
			pickle.dump(creds, token)

		s3.Bucket('oauthtokens').upload_file('token.pickle', 'token.pickle')	


	# Connect to the Gmail API
	service = build('gmail', 'v1', credentials=creds)


	# request a list of all the messages
	result = service.users().messages().list(userId='me').execute()


	# We can also pass maxResults to get any number of emails. Like this:
	# result = service.users().messages().list(maxResults=200, userId='me').execute()
	messages = result.get('messages')


	# messages is a list of dictionaries where each dictionary contains a message id.
	# iterate through all the messages
	for msg in messages:
		# Get the message from its id
		txt = service.users().messages().get(userId='me', id=msg['id']).execute()

		# Use try-except to avoid any Errors
		try:
			# Get value of 'payload' from dictionary 'txt'
			payload = txt['payload']
			headers = payload['headers']

			# Look for Subject and Sender Email in the headers
			for d in headers:
				if d['name'] == 'Subject':
					subject = d['value']
				if d['name'] == 'From':
					sender = d['value']

			# The Body of the message is in Encrypted format. So, we have to decode it.
			# Get the data and decode it with base 64 decoder.
			parts = payload.get('parts')[0]
			data = parts['body']['data']
			data = data.replace("-","+").replace("_","/")
			decoded_data = base64.b64decode(data)

			# Now, the data obtained is in lxml. So, we will parse
			# it with BeautifulSoup library
		#	soup = BeautifulSoup(decoded_data , "lxml")
			body = str(decoded_data)

			# Printing the subject, sender's email and message
			if 'doNotReply@cableone.net' in sender:
				print("Subject: ", subject)
				print("From: ", sender)
				print("Message: ", body)
			#	print('\n')

				# Send the message from Twilio
				message = subject + '. '
				if body.find('          days left') > 0:
					message = message + 'You have '+ body[body.find('          days left')-1] + " days left in your billing cycle."
					print(message)
					sendText(message)

				# Move message to trash
				service.users().messages().trash(userId='me', id=msg['id']).execute()
				break
		except Exception as e:
			print(e)



getEmails()
