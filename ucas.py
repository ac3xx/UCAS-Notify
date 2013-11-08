import mechanize, html2text, re, string, os, shelve
from bs4 import BeautifulSoup
from twilio.rest import TwilioRestClient
import config

# Browser
br = mechanize.Browser()

# Browser options
br.set_handle_equiv(True)
br.set_handle_redirect(True)
br.set_handle_referer(True)
br.set_handle_robots(False)

# Follows refresh 0 but not hangs on refresh > 0
br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

# User-Agent
br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

# The site we will navigate into, handling it's session
br.open('http://track.ucas.com/')

# Select Form
br.select_form(nr=0)
br.form['PersonalId'] = config.personal_id
br.form['Password'] = config.password
# Login
br.submit()

track_page = br.response().read()
soup = BeautifulSoup(track_page)

# Status message = application-status-message
status = str(soup.findAll('p', attrs={'id': 'application-status-message'})[0])
status = html2text.html2text(status)

university_choices = {}

i = 0
# University choices
summaries = soup.findAll('div', attrs={'class': 'offer-summary'})
for summary in summaries:
	# Fetch name and course code
	universities = summary.findAll('div', attrs={'class': 'header'})
	course = ""
	for university in universities:
		if university.find('span') is not None:
			univeristy_name = ""
			for tag in university.find('span'):
				course = tag.strip()
				tag.replaceWith('')
			univeristy_name = ''.join(university.findAll(text=True)).strip()
			university_choices[course] = {'university': univeristy_name}
	# Fetch the status
	statii = summary.findAll('div', attrs={'class': 'subheader'})
	for status_code in statii:
		if status_code.find('span') is None:
			offer_status = ''.join(status_code.findAll(text=True)).strip()
			whitelist = string.letters + string.digits + ' '
			offer_status = ''.join(c for c in offer_status if c in whitelist)
			university_choices[course]['status'] = offer_status
	
	i = i + 1
# We now have university statii in university_choices
# Fetch the results of the last update

curdir = os.path.dirname(__file__)
last_update = shelve.open(os.path.join(curdir, 'choice_db'))

first_run = False
if not last_update.has_key('choices'):
	last_update['choices'] = university_choices
	first_run = True

last_choices = last_update['choices']

account = config.twilio_account
token = config.twilio_token
client = TwilioRestClient(account, token)

for choice in last_choices:
	if not last_choices[choice]['status'] == university_choices[choice]['status'] or first_run:
		update = last_choices[choice]['university']+" have updated their status from "+last_choices[choice]['status']+" to "+university_choices[choice]['status']
		client.messages.create(to=config.twilio_to, from_=config.twilio_from,
                                 body="UCAS: "+update)
		last_choices[choice]['status'] = university_choices[choice]['status']

last_update['choices'] = last_choices
last_update.sync()
last_update.close()
