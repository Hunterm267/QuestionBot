import pickle
import datetime as dt

class BotConfig:
	def __init__(self):
		try:
			with open("QuestionBot.config","rb") as f:
				self.config = pickle.load(f)
			print("Loaded config file successfully!")
		except:
			print("Error: Unable to load config file. Creating new file.")
			self.config = {}
			nowTimeFull = dt.datetime.now();
			nowTime = dt.time(hour=nowTimeFull.hour,minute=nowTimeFull.minute)
			self.config["LastCheckTime"] = nowTime;
			self.config["DoQuestions"] = False;

	def setProperty(self,prop,val):
		self.config[prop] = val
		try:
			with open("QuestionBot.config","wb") as f:
				pickle.dump(self.config,f,pickle.HIGHEST_PROTOCOL)
		except:
			print("There was an error when saving the config file...")

	def getProperty(self,prop):
		retval = None
		try:
			retval = self.config[prop]
		except:
			retval = None
		return retval
