import itertools
import discord
from discord.ext import commands
import asyncio
import BotConfig
from threading import Timer
from numpy import random as rnd

description = '''Question of the day!'''
bot = commands.Bot(command_prefix='t/', description=description)

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

# This updates the frequency at which new questions will be posted. Calling this will also trigger an immediate question rotation if rotation was already happening.
@bot.command(pass_context=True)
@commands.check(isUserModerator_Check)
async def setQuestionTime(ctx, timeInSeconds):
	bc.setProperty("QuestionTime",int(timeInSeconds))
	await bot.say("A new question will be posted every {0} seconds".format(timeInSeconds))
	await postModReport("Question update frequency changed", "Current question will also be rotated if rotation is turned on", "New Interval: {0} seconds".format(int(timeInSeconds)))
	if (bc.rotateTask is not None):
		bc.rotateTask.cancel()
		theTask = asyncio.ensure_future(doRotate());
		bc.rotateTask = theTask;

# This function is never called directly by a user/the bot. It's called as a result of calling startQuestions or setQuestionTime. This function then keeps calling itself until stopQuestions is called.
# This needed to be done this way because discord.py wraps @bot.command() tagged functions in a special "Command" class, which asyncio.ensure_future doesn't know how to handle.
# We get around this by calling a non-bot command (So a normal function) from inside a bot command. Since ensure_future is non-blocking, and the function being called is executed in another thread, we have no issue having that thread wait for a while.
async def doRotate():
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
		await postModReport("Question Rotated (Next ID: {0})".format(num), "Question time limit reached ({0} seconds)".format(bc.getProperty("QuestionTime")),questions[num])
		await asyncio.sleep(bc.getProperty("QuestionTime"))
		theTask = asyncio.ensure_future(doRotate())
		bc.rotateTask = theTask;

# These next two just start and stop the question rotations. Starting starts the "doRotate()" function which continually calls itself in a non-blocking manner (I.E The previous invocation exits as soon as the next one is called, so we don't get an infinite pile of blocked functions)
# The questions are started by calling doRotate() on another thread, which in turn keeps calling itself indefinitely. The prefs class keeps a handle on the current running/waiting task so it can be killed if needed.
# The questions are stopped by calling cancel() on the currently running/waiting async task. This will kill the task even if it's currently sleeping.
@bot.command()
@commands.check(isUserModerator_Check)
async def startQuestions():
	await postModReport("Question Rotation Starting", "Question rotation start command used.", "Questions started")
	theTask = asyncio.ensure_future(doRotate());
	bc.rotateTask = theTask;

@bot.command()
@commands.check(isUserModerator_Check)
async def stopQuestions():
	await postModReport("Question Rotation Stopping", "Question rotation stop command used", "Questions stopped.")
	bc.rotateTask.cancel();

# Everything's good. Let's go!
print("Startup complete. Launching bot...")
bot.run(tok)
