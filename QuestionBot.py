import itertools
import discord
from discord.ext import commands
import asyncio
import BotConfig
from threading import Timer
from numpy import random as rnd
import datetime as dt

description = '''Question of the day!'''
bot = commands.Bot(command_prefix='q/', description=description)

print("Using Discord.py Version {0}".format(discord.__version__))

###################
### BOT STARTUP ###
###################
print("Reading bot token...")
try:
	f = open("token.bot","r")
	tok = f.read()
	tok = tok.rstrip() # This strips any newline characters, whitespace, etc
	print("Successfully read token: {0}".format(tok))
except:
	print("There was an error opening the token file. Exiting...")
	exit()
print("Done.")

print("Loading bot configuration...")
bc = BotConfig.BotConfig()
print("Done.")

print("Loading Questions List...")
questions = [];
with open("questions.bot") as q:
	questions = q.readlines()
print("Got {0} questions".format(len(questions)))
print("Done.")
########################
### HELPER FUNCTIONS ###
########################
def isUserServerOwner(usr):
	usrServer = usr.server
	serverOwner = usrServer.owner
	if (usr == serverOwner):
		return True
	return False

def isUserServerOwner_Check(ctx):
	usr = ctx.message.author
	return isUserServerOwner(usr)

# This checks if the user has the role specified by the 'AdminRole' property or is the server owner
def isUserAdministrator(usr):
	# First check to see if the user has the admin role
	adminRole = bc.getProperty('AdminRole')
	userRoles = (r for r in usr.roles)
	try:
		return ((adminRole in userRoles) or isUserServerOwner(usr))
	except:
		print("An uncaught exception has occurred")
		return False
	return False

def isUserAdministrator_Check(ctx):
	usr = ctx.message.author
	return isUserAdministrator(usr)

# This checks if the user has the role specified by 'ModRole' property
def isUserModerator(usr):
	modRole = bc.getProperty('ModRole')
	userRoles = (r for r in usr.roles)
	try:
		return ((modRole in userRoles) or isUserAdministrator(usr))
	except:
		print("An uncaught exception has occurred.")
		return False
	return False

def isUserModerator_Check(ctx):
	usr = ctx.message.author
	return isUserModerator(usr)

async def postModReport(event, reason, msg):
	modChan = bc.getProperty('ModReportChannel')
	report = "MOD EVENT: {0}.\nREASON: {1}.\n```{2}```".format(event, reason, msg)
	try:
		await bot.send_message(modChan,report)
	except:
		print("Could not post to mod channel!")

##################
### BOT EVENTS ###
##################
@bot.event
async def on_ready():
	print('------')
	print('Logged in as {0} (ID: {1})'.format(bot.user.name,bot.user.id))
	print('------')

######################
### ADMIN COMMANDS ###
######################
@bot.command(pass_context=True)
@commands.check(isUserAdministrator_Check)
async def setModRole(ctx, r : discord.Role):
	usr = ctx.message.author
	bc.setProperty('ModRole',r)
	await bot.say("Moderator Role set to: {0} ({1})".format(r.name,r.id))

@bot.command(pass_context=True)
@commands.check(isUserAdministrator_Check)
async def setModReportChannel(ctx, chan : discord.Channel):
	bc.setProperty("ModReportChannel", chan)
	await bot.say("Mod Events will be reported to: {0}.".format(chan.name))

######################
### Question Setup ###
######################

# This sets what channel the questions should be posted to.
@bot.command(pass_context=True)
@commands.check(isUserModerator_Check)
async def setQuestionChannel(ctx, chan : discord.Channel):
	bc.setProperty("QuestionChannel", chan)
	await bot.say("Questions will be posted to: {0}.".format(chan.name))

# Takes the time to post a question as a 24 hour string, I.E "13:00" for 1 PM, "16:30" for 4:30 PM, etc.
# Note: The time periodic checker only has a resolution of 10 minutes, so the exact moment of execution is only precise to within that.
@bot.command()
@commands.check(isUserModerator_Check)
async def setRotateTime(hhmm):
	try:
		comps = hhmm.split(":")
		theTime = dt.time(hour=int(comps[0]),minute=int(comps[1]))
	except:
		await bot.say("There was a problem interpreting your string as a time")
		return;
	bc.setProperty("RotateTime",theTime)
	await bot.say("A new question will be posted every day at {0}".format(theTime))
	await postModReport("Question Rotate Time Changed", "setRotateTime command called", "New Time: {0}".format(theTime))

async def checkSchedule():
	nowTimeFull = dt.datetime.now();
	nowTime = dt.time(hour=nowTimeFull.hour,minute=nowTimeFull.minute,second=nowTimeFull.second)
	lastCheck = bc.getProperty("LastCheckTime")
	rotateTime = bc.getProperty("RotateTime");
	doQuestions = bc.getProperty("DoQuestions")
	if (rotateTime is not None and doQuestions is True):
		# The last check is a catch for if the rotate time is somewhere near midnight by evaluating to true if we last ran the scheduler "After" the current time (I.E 23:55 -> 00:05)
		if (nowTime >= rotateTime and (lastCheck < rotateTime or lastCheck >= nowTime)):
			await doRotateQuestion()
	# Now schedule the next check
	bc.setProperty("LastCheckTime",nowTime);
	await asyncio.sleep(600) # Wait 10 minutes for the next check
	theTask = asyncio.ensure_future(checkSchedule())

async def doRotateQuestion():
	qchan = bc.getProperty("QuestionChannel")
	if (qchan is not None):
		await bot.purge_from(qchan,limit=10000)
		num = rnd.randint(len(questions));
		if (num == bc.getProperty("LastNum")):
			if (num < len(questions)-1):
				num = num+1;
			else:
				num = num-1;
		bc.setProperty("LastNum",num)
		await bot.send_message(qchan,questions[num])
		await postModReport("Question Rotated (Next ID: {0})".format(num), "Rotation Time reached ({0})".format(bc.getProperty("RotateTime")),questions[num])


# These next two just start and stop the question rotations. Starting starts the "doRotate()" function which continually calls itself in a non-blocking manner (I.E The previous invocation exits as soon as the next one is called, so we don't get an infinite pile of blocked functions)
# The questions are started by calling doRotate() on another thread, which in turn keeps calling itself indefinitely. The prefs class keeps a handle on the current running/waiting task so it can be killed if needed.
# The questions are stopped by calling cancel() on the currently running/waiting async task. This will kill the task even if it's currently sleeping.
@bot.command()
@commands.check(isUserModerator_Check)
async def startQuestions():
	rtime = bc.getProperty("RotateTime")
	if (rtime is None):
		await bot.say("WARNING: A rotation time has not been set. Defaulting to 00:00 (Midnight)")
		midnight = dt.time() # Defaults to 00:00
		await setRotateTime("00:00")
	qchan = bc.getProperty("QuestionChannel");
	if (qchan is None):
		await bot.say("WARNING: A question channel has not been set. Questions may not be posted.")
	bc.setProperty("DoQuestions",True);
	await postModReport("Question Rotation Starting", "Question rotation start command used.", "Questions started")

@bot.command()
@commands.check(isUserModerator_Check)
async def stopQuestions():
	bc.setProperty("DoQuestions",False)
	await postModReport("Question Rotation Stopping", "Question rotation stop command used", "Questions stopped.")

# Everything's good. Let's go!
print("Starting task scheduler...")
asyncio.ensure_future(checkSchedule())
print("Done.")

print("Startup complete. Launching bot...")
bot.run(tok)
