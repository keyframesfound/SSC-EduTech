# SSC-EduTech
Improving technology for education

## Amazon Quick
### Personal Email Tracker for EDB Teacher training 
The personal email tracker for EDB teacher tracking checks the EDB website every week, searches keyword (e.g. ICT) and sees all of the recent notices that are added from the last 7 days. Then the tracker sends an email to the respective teacher and notifies them of classes / trainings that concern them. An email is sent to their inbox every week and they can reply to the email while also replying to the trigger email (replytocal@aws.com). All of this then triggers the second flow which runs when the trigger email is interacted with. The second flow checks the user email inbox to see the latest weekly summary then sees which days the teacher would like to add. If it does not conflict with their current calendar it would be added, but in the case that it conflicts with their current calendar, there would be a secondary email that tells the user that there is a conflict. On the secondary email, the user may override this conflict and add it anyways.
```
Prompt 1 (Main Flow):
Make an automated email flow that when triggered checks the user email inbox for the latest Weekly ICT Course Summary from EDB Training Calendar subject email. Check the replies and the email content to see which events the teacher would like to add to their calender, if there are no conflicts with the teachers calender then add to the calender and send a new email saying added. If there are conflicts the email is still sent to the user and it tells them there are conflicts, and the user is able to reply to this email to override it and still add it to calender even if its conflicted
```
```
Prompt 2 (Secondary calendar flow):
I am an ICT teacher of a secondary school, in charge of teaching senior form ICT and the IT Department in Hong Kong. I want a weekly summary sent to my email  ryanyeung0925@gmail.com, please go to https://tcs.edb.gov.hk/tcs/publicCalendar/start.htm and retrieve relavant courses in the past 7 days
```

