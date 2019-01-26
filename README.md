# QuestionBot

This is a simple bot meant to pick a random question at a specified interval from a list of questions, and post that question to a channel.

There are a few commands to know:

q/setModRole *role* : Sets the "moderator role" to *role*. Any user with this role can start or stop the questions or change the question update frequency.

q/setModReportChannel *chan* : Sets the channel that the bot should post mod reports to (I.E : Commands used, questions changed).

q/setRotateTime *HH:MM* : Sets the time at which to post a new question. *HH:MM* is given in 24-hour time, I.E 13:45 for 1:45 PM.

q/setQuestionChannel *chan* : Sets the channel to which the questions should be posted. The bot will purge this channel and post the next question every day after the time set in setRotateTime passes.

q/startQuestions, q/stopQuestions : Self explanatory. Starts (or stops) the question rotation. If setRotateTime has not been called, defaults to 00:00 (Midnight)
