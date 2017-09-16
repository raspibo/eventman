# Eventbrite import

It's possible to import attendees from Eventbrite using both an exported CSV file or the Eventbrite's API.

## API import

On the Evenbrite site, go to the "Account Settings" -> "Developer" -> "App management" page.

Create a new app. Click on the "Show Client Secret and OAuth Token" link and copy "Your personal OAuth token".

Now go to the Eventbrite web page of your event, and copy the "eid" field of the URL.

In the EventMan "Import tickets" page, set the copied OAuth token and Event ID; it's also possible to select an existing event that will receive the new attendees, or create a brand new event with the information from Eventbrite.

If you've created a new event, don't forget to edit it to add a registration form so that it will contain at least "name", "surname", "email" (also adding "company" and "job title" is a good idea).


## CSV import

On the Evenbrite site, go to the "manage" page of your event and then go to the "Manage Attendees" -> "Orders" page.

From there, use the "Export to CSV" feature to get the CSV file.

Load this file in the EventMan "Import tickets" page, select an existing event that will receive the new attendees and click the "Import" button.

If you select this import method, please beware that you probably also want to edit the tools/qrcode\_reader.ini configuration file (see the comment about the limit\_field setting).
