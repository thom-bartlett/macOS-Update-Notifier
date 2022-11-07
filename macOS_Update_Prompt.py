#!/Library/ManagedFrameworks/Python/Python3.framework/Versions/Current/bin/python3

from asyncore import write
import requests
import datetime
import platform
import os
import json
import subprocess
from os.path import exists
from Foundation import NSLog, NSBundle
import sys
from packaging.version import Version
import plistlib
import logging
from logging.handlers import RotatingFileHandler
from SystemConfiguration import SCDynamicStoreCopyConsoleUser

# Settings logs to file if not from Jamf, for Jamf its better to have them report back to Jamf
if sys.argv[1] == '/':
    logging.basicConfig(format='%(asctime)s - %(message)s')
else:
    logging.basicConfig(filename='/Library/management/update.log', format='%(asctime)s - %(message)s')
    # add a rotating handler
    logger = logging.getLogger("Rotating Log")
    handler = RotatingFileHandler('/Library/management/update.log', maxBytes=1000000,
                                    backupCount=5)
    logger.addHandler(handler)

# Global Variables
Plist = "/Library/Management/update.plist"

class DialogAlert:
    def __init__(self, message):
        # set the default look of the alert
        if is_dark_mode():
            bannerimage = "/Library/Management/software_update-light.jpg"
            print ("dark mode")
        else:
            print ("light mode")
            bannerimage = "/Library/Management/software_update-dark.jpg"

        self.message = message
        infolink="https://support.apple.com/macos"
        self.content_dict = {
           # "alignment": "center",
            "button1text": "Update Now",
            "bannerimage": bannerimage,
            "infobuttonaction": infolink,
            "infobuttontext": "More Info",
            "message": message,
            "messagefont": "size=16",
            "title": "none",
            "button2text": "Defer",
            "moveable": 1,
            "ontop": 0,
            "width": "1100",
            "height": "510"

        }

    def alert(self, contentDict):
        """Runs the SwiftDialog app and returns the exit code"""
        jsonString = json.dumps(contentDict)
        exit_code = subprocess.run(["/usr/local/bin/dialog", "--jsonstring", jsonString, "--button1shellaction", "open -b com.apple.systempreferences /System/Library/PreferencePanes/SoftwareUpdate.prefPane"])
        return exit_code

def dialog_Check():
    """Ensure Dialog is installed"""
    dialogPath="/usr/local/bin/dialog"
    if os.path.exists(dialogPath):
        logger.warning("Swift Dialog Installed, proceeding")
    else:
        logger.warning("Swift Dialog not installed, exiting")
        sys.exit(1)

def read_Plist():
    """return value of Plist if is exists"""
    if os.path.exists(Plist):
        with open(Plist, 'rb') as fp:
            pl = plistlib.load(fp)
        return pl
    else:
        logger.warning("No Plist detected...")
        return

def is_dark_mode():
    appearanceBundle = NSBundle.bundleWithPath_(
        "/System/Library/PreferencePanes/Appearance.prefPane"
    )
    appearanceShared = appearanceBundle.classNamed_("AppearanceShared")
    app = appearanceShared.sharedAppearanceAccess()
    if app.theme() == 1:
        return False
    else:
        return True

def update_Plist(today, current_OS, final_Date=0):
    """Update Plist and create if necessary"""
    update_Dir = "/Library/Management"
    if os.path.exists(Plist):
        with open(Plist, 'rb') as data:
            plist = plistlib.load(data)
            plist.update({"last-run": today})
            # Check if OS updated since last run
            if Version(plist["current_OS"]) < Version(current_OS):
                plist.update({"current_OS": current_OS})
                plist.update({"deadline": final_Date})
        # Write updates out
        with open(Plist, 'wb') as file:
            plistlib.dump(plist, file)
    else:
        if not os.path.exists(update_Dir):
            os.makedirs(update_Dir)
        # Create Plist
        properties = {
           "create-time": today,
           "last-run": today,
           "current_OS": current_OS,
           "deadline": final_Date
        }
        days_Left = int((final_Date.date() - today.date()).days)
        with open(Plist, 'wb') as file:
            plistlib.dump(properties, file)

def run_Check(diff, postingDate, current_OS, update_Type, major_OS_Deadline):
    """Check if a dialog needs to be displayed"""
    today = datetime.datetime.today()
    final_Date = postingDate + datetime.timedelta(days=30)
    ran_Today = False
    if read_Plist():
        plist_Value = read_Plist()
        lastRun = plist_Value["last-run"]
        deadline = plist_Value["deadline"]
        if lastRun.date() == today.date():
            ran_Today = True
    else:
        lastRun = today
        deadline = final_Date
    if update_Type == "Major":
        deadline = major_OS_Deadline
    days_Left = int((deadline.date() - today.date()).days)
    update_Plist(today, current_OS, deadline)
    if days_Left > 23 and diff < 2:
        logger.warning("Still in Update grace period... exiting... ")
        return 1, days_Left
    elif days_Left > 0 and diff < 2:
        if ran_Today:
            logger.warning("Already ran today... exiting...")
            return 1, days_Left
        else:
            logger.warning("In regular update time frame... displaying dialog...")
            return 2, days_Left
    else:
        logger.warning("Deadline has passed... displaying dialog...")
        return 3, days_Left

def get_Latest_Update():
    """Download latest update info from Apple website"""
    # set to 4th param to work with Jamf
    if (sys.argv[1]) == '/':
        majorOS = str(sys.argv[4])
    else:
        majorOS = str(sys.argv[1])
    URL = "https://gdmf.apple.com/v2/pmv"
    r = requests.get(URL, verify=False)
    list = r.json()
    # get first listing on version specified
    for i in (list["PublicAssetSets"]["macOS"]):
        if i["ProductVersion"].startswith(majorOS):
            macOS_Latest = i["ProductVersion"]
            break
    #macOS_Latest = list["AssetSets"]["macOS"][0]["ProductVersion"]
    posting_Date_STR = list["AssetSets"]["macOS"][0]["PostingDate"]
    # convert to date and give 7 day grace period
    posting_Date = datetime.datetime.strptime(posting_Date_STR, '%Y-%m-%d')
    return macOS_Latest, posting_Date

def update_Type(latest, current_OS):
    """Check what type of update we are dealing with"""
    current = Version(current_OS)
    latest = Version(latest)
    diff = 0
    if current.major == latest.major:
        logger.warning("Major version match")
        if current.minor == latest.minor:
            logger.warning("features version match")
            if current.micro == latest.micro:
                logger.warning("Version processing error... exiting...")
                exit
            else:
                logger.warning("Minor version change detected")
                Update = "minor"
                time = 20
                diff = diff + latest.micro - current.micro
        else:
            logger.warning("Feature version change detected")
            Update = "feature"
            time = 40
            diff = diff + latest.minor - current.minor + latest.micro
    else:
        logger.warning("Major version change detected")
        Update = "Major"
        time = 60
        diff = diff + latest.major - current.major
    type = {"type": Update, "time": time, "current": current_OS, "diff": diff}
    logger.warning(f"Update type details: {type}")
    return type

def update_Check():
    """Check if updates show as available locally"""
    update = ["softwareupdate", "-l"]
    for i in range(1, 4):
        try:
            test = subprocess.run(update, text=True, timeout=30, capture_output=True)
            logger.warning(test.stderr)
            if test.stderr == "No new software available.\n":
                logger.warning("update available online but not locally... running kickstart")
                subprocess.run(["launchctl", "kickstart", "-k", "system/com.apple.softwareupdated"])
                if i == 3:
                    logger.warning("update not available locally")
                    return False
            else:
                logger.warning("update available locally")
                return True
        except subprocess.TimeoutExpired as e:
            logger.warning(f"Timeout expired with error: {e}. Running kickstart...")
            subprocess.run(["launchctl", "kickstart", "-k", "system/com.apple.softwareupdated"])

def build_Message():
    message =(f"### To learn how to update macOS follow the [macOS Upgrade Guide](https://docs.google.com/document/d/1qapEgeQXDAdAlMada6p6L7fmqxUWCECocHyA8GAqh3Q/edit?usp=sharing)\n\n"
    "***\n\n"
    f"### If you experience any issues, you can submit a ticket at with [WPromote Support](https://wpromote.happyfox.com/new/).\n\n"
    "### Connect with IT:\n\nSupport Slack Channel: #it-help\n\nEmail: help@support.com\n\n"
    "***\n\n"
    "Please note that the update may take about an hour to first download and then install. Please update after business hours.\n\n"
    "*Please save any critical business information on Google Drive prior to starting the upgrade in case your computer experiences an error during the process.")
    return message

def main():
    # Get arguments
    current_OS = platform.mac_ver()[0]
    # Jamf sends first arg as /
    if (sys.argv[1]) == '/':
        major_OS_Deadline = sys.argv[5]
        if len(sys.argv) > 6:
            if sys.argv[6] == "debug":
                current_OS = sys.argv[7]
    else:
        major_OS_Deadline = sys.argv[2]
        if len(sys.argv) > 3:
            if sys.argv[3] == "debug":
                current_OS = sys.argv[4]
                
    major_OS_Deadline = datetime.datetime.strptime(major_OS_Deadline, '%Y-%m-%d')
    # get latest update info from Apple        
    latest_info = get_Latest_Update()
    if Version(current_OS) < Version(latest_info[0]):
        # cleanup old dialog command file if it exists
        dialog_command_file = "/var/tmp/dialog.log"
        if os.path.exists(dialog_command_file):
            os.remove(dialog_command_file)
        # check if dialog is installed and latest
        dialog_Check()
        # Convert update release date to human readable format
        release = latest_info[1].strftime("%m/%d/%Y")
        # check whether update is minor, major, etc and how many updates behind we are
        type = update_Type(latest_info[0], current_OS)
        # check when update was run last and determine if it needs to be displayed
        check = run_Check(type["diff"], latest_info[1], current_OS, type["type"], major_OS_Deadline)
        if check[0] == 1:
            return
        elif check[0] == 2:
            message = build_Message()
            mainDialog = DialogAlert(message)
            run_Main = mainDialog.alert(mainDialog.content_dict)
            if run_Main.returncode == 2:
                logger.warning("user deferred")
            elif run_Main.returncode == 0:
                logger.warning("user opened update page")
            else:
                logger.warning(f"Dialog closed with exit code: {run_Main}")
        else: 
            logger.warning("Update is past deadline")
            message = build_Message()
            finalDialog = DialogAlert(message + "\n\n**Notice: You have passed the deadline and this message will persist until you install the update and reboot**")
            finalDialog.content_dict["ontop"] = 1
            finalDialog.content_dict.pop("button2text")
            run_Final = finalDialog.alert(finalDialog.content_dict)
            if run_Final.returncode == 2:
                logger.warning("user deferred")
            elif run_Final.returncode == 0:
                logger.warning("user opened update page")
            else:
                logger.warning(f"Dialog closed with exit code: {run_Final}")
    else:
        logger.warning("No update needed... exiting...")

main()