# QuestionBot

This is a simple bot meant to pick a random question at a specified interval from a list of questions, and post that question to a channel.

There are a few commands to know:

q/setModRole *role* : Sets the "moderator role" to *role*. Any user with this role can start or stop the questions or change the question update frequency.

q/setModReportChannel *chan* : Sets the channel that the bot should post mod reports to (I.E : Commands used, questions changed).

q/setQuestionTime *timeInSeconds* : Sets the time period that the question should be updated at. This will immediately cause the question to rotate.

q/setQuestionChannel *chan* : Sets the channel to which the questions should be posted. The bot will purge this channel, post its question, and pin that message every *timeInSeconds* seconds.

q/startQuestions, q/stopQuestions : Self explanatory. Starts (or stops) the question rotation.
