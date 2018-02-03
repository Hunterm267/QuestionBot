import itertools
import discord
from discord.ext import commands
import asyncio
import BotConfig

description = '''This is a bot designed to help run the University of Arizona Students Discord Server.'''
bot = commands.Bot(command_prefix='t/', description=description)

print("Using Discord.py Version {0}".format(discord.__version__))

###################
### BOT STARTUP ###
###################
try:
	f = open("token.bot","r")
	tok = f.read()
	tok = tok.rstrip() # This strips any newline characters, whitespace, etc
	print("Successfully read token: {0}".format(tok))
except:
	print("There was an error opening the token file. Exiting...")
	exit()

print("Loading bot configuration...")
bc = BotConfig.BotConfig()

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

async def postAdminReport(event, reason, msg):
	adminChan = bc.getProperty('AdminReportChannel')
	report = "ADMIN EVENT: {0}.\nREASON: {1}.\n```{2}```".format(event, reason, msg)
	try:
		await bot.send_message(adminChan,report)
	except:
		print("Could not post to admin channel!")

##################
### BOT EVENTS ###
##################
@bot.event
async def on_ready():
	print('------')
	print('Logged in as {0} (ID: {1})'.format(bot.user.name,bot.user.id))
	print('------')

@bot.event
async def on_message(msg : discord.Message):
	if ("@everyone" in msg.content):
		emojis = msg.server.emojis
		spook = next((e for e in emojis if e.name == "spookeye"), None)
		if spook is not None:
			await bot.send_message(msg.channel,"{0} {1}".format(msg.author.mention,str(spook)))
	await bot.process_commands(msg)

@bot.event
async def on_member_join(member : discord.Member):
	await bot.send_message(member, "Welcome to \"{0}\". I'm Wilbur, a bot that helps run the server. Please be sure to check out the rules channel, and join in to the fun!".format(member.server.name))
	await bot.send_message(member, "We encourage you to tell us what your class rank is (Freshman, Sophomore, Junior, etc), to help our members find other people in the same year as them. To set this up, just send me a message (either in the server or as a direct message) with the text \'t/iama Freshman/Sophomore/Junior/Senior/etc\' (No quotes).\nYou can also just type \'t/iama\' and I'll give you examples on how to do this and what kind of things you can say.")
	await bot.send_message(member, "Again, welcome, and we hope you stay around!")

@bot.event
async def on_reaction_add(r : discord.Reaction, u : discord.Member):
	emoj = r.emoji
	if (r.count >= 1 and emoj == "\U000023EC"):
		msg = r.message
		msgTxt = msg.content
		msgAuth = msg.author
		await bot.delete_message(msg)
		await postModReport("A message was deleted", "Downvote threshold exceeded", "{0}: {1}".format(msgAuth,msgTxt))

#####################
### USER COMMANDS ###
#####################
@bot.command(pass_context=True)
async def iama(ctx, *, theClass="NoneSpecified"):
	theUser = ctx.message.author
	theServer = ctx.message.server
	if (theServer is None and theClass is not "NoneSpecified"): # This is a catch for someone trying to DM the bot. Ideally we'll add a check that will let them DM the bot eventually.
		botServers = list(bot.servers)
		withUser = [b for b in botServers if theUser in b.members]
		if (len(withUser) == 1): # If just one server is shared, we can assume that's the one we want to set
			await bot.send_message(theUser, "I see you are only in one server that I am also in. I assume you mean this command for \"{0}\"".format(withUser[0].name))
			theServer = withUser[0]
			theUser = next(u for u in theServer.members if u == theUser)
		elif (len(withUser) > 1): # Ask the user which server they meant
			await bot.send_message(theUser, "It looks like we share several servers. Which one did you mean to use this command for? Your choices are: {0}".format(", ".join([w.name for w in withUser])))
			msg = await bot.wait_for_message(author=theUser, timeout=15.0)
			if (msg is None): # If the user doesn't respond in time
				await bot.send_message(theUser, "It looks like you're a bit busy right now, so I'm going to get back to my other tasks. Send me this command again when you're ready!")
				return
			else: # Check and see if they typed something that makes sense
				try: # This will throw an exception if there's no match
					theServer = next(w for w in withUser if w.name.upper() == msg.content.upper())
				except:
					await bot.send_message(theUser, "Sorry, I didn't recognize \"{0}\" as a server we share. Please try sending me this command again.".format(msg.content))
					return
				theUser = next(u for u in theServer.members if u == theUser)
		else: # Don't know how we'd get here, but just in case we don't share any servers, there's nothing to do.
			await bot.send_message(theUser, "It looks like we don't share any servers, so I can't set your role anywhere! :(")
			return
	theRole = discord.utils.get(theServer.roles, name=theClass.title()) # This will return None if it doesn't exist
	userRoles = theUser.roles
	allowedRoles = [discord.utils.get(theServer.roles,name=r) for r in ["Freshman","Sophomore","Junior","Senior","Alumni","Grad Student","Tucsonan"]]
	newRoles = [r for r in userRoles if r not in allowedRoles] # This gets the users roles that aren't one of the ones we're managing (So they don't lose other roles like admin, etc)
	newRoles.append(theRole)
	if (theRole is not None): # Checks to make sure the given class is one of the allowed ones
		try:
			await bot.replace_roles(theUser, *newRoles)
			await bot.send_message(ctx.message.author, "Got it. I will set your role as \"{0}\" in \"{1}\"! Feel free to use this command again if you need to change your role!".format(theClass.title(),theServer.name))
		except:
			await bot.send_message(ctx.message.author, "Sorry. I understood what you told me, but something went wrong when I tried to set your role. Send a message to the server admins and let them know something went wrong.")
	elif (theClass.upper() == "NoneSpecified".upper()): # This catches if no class was given, and sends an example back
		await bot.send_message(ctx.message.author, "You can use this command to tell me what your class rank is. Just send a message that says \"t/iama ClassName\" (No quotes).\nFor example, if you're a Freshman, you'd send \"t/iama Freshman\".\nYour options are {0}".format(', '.join([r.name for r in allowedRoles])))
	else: # If the input didn't match anything
		await bot.send_message(ctx.message.author, "I'm sorry, I didn't recognize \"{0}\". Allowed choices are: {1}".format(theClass.title(),', '.join([r.name for r in allowedRoles])))

######################
### ADMIN COMMANDS ###
######################
@bot.command(pass_context=True)
@commands.check(isUserServerOwner_Check)
async def setAdminRole(ctx, r : discord.Role):
	bc.setProperty('AdminRole',r)
	await bot.say("Administrator Role set to: {0} ({1})".format(r.name,r.id))

@bot.command(pass_context=True)
@commands.check(isUserAdministrator_Check)
async def setModReportChannel(ctx, chan : discord.Channel):
	bc.setProperty("ModReportChannel", chan)
	await bot.say("Mod Events will be reported to: {0}.".format(chan.name))

@bot.command(pass_context=True)
@commands.check(isUserAdministrator_Check)
async def setAdminReportChannel(ctx, chan : discord.Channel):
	bc.setProperty("AdminReportChannel", chan)
	await bot.say("Admin Events will be reported to: {0}.".format(chan.name))

#FIXME: Need to make sure that ban/kick can't be used on protected roles
@bot.command(pass_context=True)
@commands.check(isUserAdministrator_Check)
async def ban(ctx, target : discord.Member, *, reason : str):
	usr = ctx.message.author
	# Check to make sure we're not trying to ban ourselves
	if (usr == target):
		await bot.say("I can't do that. Why would you want to ban yourself?")
		return
	# Check to make sure the targeted user isn't a mod or admin
	if (isUserAdministrator(target) or isUserModerator(target)):
		await bot.say("I won't ban server moderators or administrators. They might unplug me.")
		return
	# Finally, ban the user
	await bot.send_message(target, "You have been banned from: \"{0}\". The reason for your ban is: \"{1}\". This ban will not expire.".format(target.server.name,reason))
	await bot.ban(target, delete_message_days=0)
	await postAdminReport("User banned", reason, "Banned User: {0}. Ban issued by {1}".format(target,usr))
	await bot.say("The banhammer has fallen. :hammer:")

####################
### MOD COMMANDS ###
####################
@bot.command(pass_context=True)
@commands.check(isUserServerOwner_Check)
async def setModRole(ctx, r : discord.Role):
	usr = ctx.message.author
	bc.setProperty('ModRole',r)
	await bot.say("Moderator Role set to: {0} ({1})".format(r.name,r.id))

@bot.command(pass_context=True)
@commands.check(isUserModerator_Check)
async def kick(ctx, target : discord.Member, *, reason : str):
	# Check to make sure we're not trying to ban ourselves
	if (ctx.message.author == target):
		await bot.say("I can't do that. Why would you want to kick yourself? :(")
		return
	# Last, check to make sure the targeted user isn't a mod or admin
	if (isUserAdministrator(target) or isUserModerator(target)):
		await bot.say("I won't kick server moderators or administrators. They might unplug me. :(")
		return

	await bot.send_message(target, "You have been kicked from: \"{0}\". The reason for your kick is: \"{1}\". You are free to rejoin, but be aware future infractions will result in a ban.".format(target.server.name,reason))
	await bot.kick(target)
	await postModReport("User kicked", reason, "Kicked User: {0}. Kick issued by {1}.".format(target,ctx.message.author))
	await bot.say("And they're gone! :wave:")

####################
### JUST FOR FUN ###
####################


print("Startup complete. Launching bot...")
bot.run(tok)
