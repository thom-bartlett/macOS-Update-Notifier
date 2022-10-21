# macOS-Update-Notifier
Nudge like tool to prompt users to update. See https://github.com/macadmins/nudge for the inspiration

# Workflow
- Pulls down data from Apple website about latest version of macOS
- Compares whether current computer is on latest version
- If not is uses the softwareupdate binary to double check there is actually an update available
- If not it will run the jumpstart command
- If it passes checks it will display a dialog using Swift Dialog - https://github.com/bartreardon/swiftDialog 

# Features
- Displays date update was released from Apple so uses know how far behind they are 
- Grace period of 7 days after release to ensure people have a chance to update on their own
- Displays if it is a major or minor update and (very roughly) estimates how long it will take
- Has logic to run kickstart command if needed - Soon will have logic to delete softwareupdate plist for additional fixing
- Coming Soon - Grace period after initial deployment 
