#!/Library/ManagedFrameworks/Python/Python3.framework/Versions/Current/bin/python3

from asyncore import write
import requests
import datetime
import platform
import os
import json
import subprocess
from os.path import exists
from Foundation import NSLog
import sys
from packaging.version import Version
import plistlib

class DialogAlert:
    def __init__(self, message):
        # set the default look of the alert
        self.message = message
        infolink="https://support.apple.com/en-au/HT201222"
        self.content_dict = {
            "alignment": "center",
            "button1text": "Update Now",
            "bannerimage": "https://github.com/unfo33/venturewell-image/blob/main/update_logo_2.jpeg?raw=true",
            "infobuttonaction": infolink,
            "infobuttontext": "More Info",
            "message": message,
            "messagefont": "size=16",
            "title": "none",
            "button2text": "Defer",
            "moveable": 1,
            "ontop": 0
        }

    def alert(self, contentDict):
        """Runs the SwiftDialog app and returns the exit code"""
        jsonString = json.dumps(contentDict)
        exit_code = subprocess.run(["/usr/local/bin/dialog", "--jsonstring", jsonString, "--button1shellaction", "open -b com.apple.systempreferences /System/Library/PreferencePanes/SoftwareUpdate.prefPane"])
        return exit_code

def dialog_Check():
    dialogPath="/usr/local/bin/dialog"
    if os.path.exists(dialogPath):
        write_log("Swift Dialog Installed, proceeding")
    else:
        write_log("Swift Dialog not installed, exiting")
        sys.exit(1)

def run_Check(diff):
    update_Plist = "/Library/Management/update.plist"
    today = datetime.date.today()
    with open(update_Plist, 'rb') as fp:
        pl = plistlib.load(fp)
    lastRun = pl["last-run"]
    #deadline = datetime.datetime.strptime(pl["deadline"], '%Y-%m-%d')
    deadline = pl["deadline"]
    days_Left = int((deadline.date() - today).days)
    if days_Left > 23 and diff < 2:
        write_log("Still in Update grace period... exiting... ")
        return 1, days_Left
    elif days_Left > 0 and diff < 2:
        write_log("In regular update time frame... displaying dialog...")
        return 2, days_Left
    else:
        write_log("Deadline has passed... displaying dialog...")
        return 3, days_Left

def run_Time(postingDate, current_OS):
    # Set variables
    update_Plist = "/Library/Management/update.plist"
    update_Dir = "/Library/Management"
    # Get time data
    now = datetime.datetime.now()
    todayString = str(datetime.date.today())
    final_Date = postingDate + datetime.timedelta(days=30)
    # Check if plist exists
    if not os.path.exists(update_Plist):
        if not os.path.exists(update_Dir):
            os.makedirs(update_Dir)
        # Create Plist
        properties = {
           "create-time": todayString,
           "last-run": now,
           "current_OS": current_OS,
           "deadline": final_Date
        }
        fileName=open(update_Plist,'wb')
        plistlib.dump(properties, fileName)
        fileName.close()
    else:
        # Update Plist
        with open(update_Plist, 'rb') as data:
            plist = plistlib.load(data)
            plist.update({"last-run": now})
            # Check if OS updated since last run
            if Version(plist["current_OS"]) < Version(current_OS):
                plist.update({"current_OS": current_OS})
                plist.update({"deadline": final_Date})
        # Write updates out
        with open(update_Plist, 'wb') as file:
            plistlib.dump(plist, file)

def update_Online():
    # set to 4th param to work with Jamf
    majorOS = str(sys.argv[4])
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
    current = Version(current_OS)
    latest = Version(latest)
    diff = 0
    if current.major == latest.major:
        write_log("Major version match")
        if current.minor == latest.minor:
            write_log("features version match")
            if current.micro == latest.micro:
                write_log("Version processing error... exiting...")
                exit
            else:
                write_log("Minor version change detected")
                Update = "minor"
                time = 20
                diff = diff + latest.micro - current.micro
        else:
            write_log("Feature version change detected")
            Update = "feature"
            time = 40
            diff = diff + latest.minor - current.minor + latest.micro
    else:
        write_log("Major version change detected")
        Update = "Major"
        time = 60
        diff = diff + latest.major - current.major
    type = {"type": Update, "time": time, "current": current_OS, "diff": diff}
    write_log(f"Update type details: {type}")
    return type

def write_log(text):
    """logger for depnotify"""
    NSLog("[mdm-switch] " + str(text))

def update_Check():
    # check for updates
    update = ["softwareupdate", "-l"]
    for i in range(1, 4):
        try:
            test = subprocess.run(update, text=True, timeout=30, capture_output=True)
            write_log(test.stderr)
            if test.stderr == "No new software available.\n":
                write_log("update available online but not locally... running kickstart")
                subprocess.run(["launchctl", "kickstart", "-k", "system/com.apple.softwareupdated"])
                if i == 3:
                    write_log("update not available locally")
                    return False
            else:
                write_log("update available locally")
                return True
        except subprocess.TimeoutExpired as e:
            write_log(f"Timeout expired with error: {e}. Running kickstart...")
            subprocess.run(["launchctl", "kickstart", "-k", "system/com.apple.softwareupdated"])

def build_Message(current, latest, release, type, time, left):
    message =(f"## Your Update Path: **{current}** → **{latest}**\n\nmacOS **{latest}** was released on **{release}**.  "
    f"It is a **{type}** update and will require around **{time}** minutes downtime.\n\nDays Remaining to Update: **{left}**\n\n"
    f"To begin the update, click on **Update Now** and follow the provided steps.\n*You can also use the [Self Service app](jamfselfservice://content?entity=policy&id=97&action=view) to update at your convenience*.")
    return message

def main():
    # cleanup old file if it exists
    dialog_command_file = "/var/tmp/dialog.log"
    if os.path.exists(dialog_command_file):
        os.remove(dialog_command_file)
    # check if dialog is installed and latest
    dialog_Check()
    current_OS = platform.mac_ver()[0]
    latest_info = update_Online()
    if Version(current_OS) < Version(latest_info[0]):
        # Write to disk update info
        run_Time(latest_info[1], current_OS)
        # Convert to human readable format
        release = latest_info[1].strftime("%m/%d/%Y")
        # check whether update is minor, major, etc and how many updates behind we are
        type = update_Type(latest_info[0], current_OS)
        # check when update was run last and determine if it needs to be displayed
        check = run_Check(type["diff"])
        if check[0] == 1:
            return
        elif check[0] == 2:
            message = build_Message(current_OS, latest_info[0], release, type["type"], type["time"], check[1])
            mainDialog = DialogAlert(message)
            run_Main = mainDialog.alert(mainDialog.content_dict)
            if run_Main == 2:
                write_log("user deferred")
            elif run_Main == 0:
                write_log("user opened update page")
            else:
                write_log(f"Dialog closed with exit code: {run_Main}")
        else: 
            write_log("Update is past deadline")
            message = build_Message(current_OS, latest_info[0], release, type["type"], type["time"], 0)
            finalDialog = DialogAlert(message + "\n\n**Notice: You have passed the deadline and this message will persist until you install the update and reboot**")
            finalDialog.content_dict["ontop"] = 1
            finalDialog.content_dict.pop("button2text")
            run_Final = finalDialog.alert(finalDialog.content_dict)
            if run_Final == 2:
                write_log("user deferred")
            elif run_Final == 0:
                write_log("user opened update page")
            else:
                write_log(f"Dialog closed with exit code: {run_Final}")
    else:
        write_log("No update needed... updating last run and exiting...")
        run_Time(latest_info[1], current_OS)

main()