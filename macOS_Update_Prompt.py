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

def update_Online():
    URL = "https://gdmf.apple.com/v2/pmv"
    r = requests.get(URL, verify=False)
    list = r.json()
    # get first listing on version 12
    for i in (list["PublicAssetSets"]["macOS"]):
        if i["ProductVersion"].startswith("12"):
            macOS_Latest = i["ProductVersion"]
            break
    #macOS_Latest = list["AssetSets"]["macOS"][0]["ProductVersion"]
    posting_Date_STR = list["AssetSets"]["macOS"][0]["PostingDate"]
    # convert to date and give 7 day grace period
    posting_Date = datetime.datetime.strptime(posting_Date_STR, '%Y-%m-%d')
    start_Date = posting_Date + datetime.timedelta(days=7)
    final_Date = posting_Date + datetime.timedelta(days=30)
    today = datetime.date.today()
    days_Left = int((final_Date.date() - today).days)
    update_info = {"latest": macOS_Latest, "days_Left": days_Left, "posting": posting_Date_STR}
    return update_info

def update_Type(latest):
    current_OS = platform.mac_ver()[0]
    write_log(f"Current OS is: {current_OS}")
    write_log(F"latest OS: {latest}")
    current = Version(current_OS)
    latest = Version(latest)
    if latest == current:
        write_log("On Latest Version, exiting")
        exit
    else:
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
    
def main():
    # cleanup old file if it exists
    dialog_command_file = "/var/tmp/dialog.log"
    if os.path.exists(dialog_command_file):
        os.remove(dialog_command_file)
    # check if dialog is installed and latest
    dialog_Check()
    latest = update_Online()
    type = update_Type(latest["latest"])
    message =(f"## Your Update Path: **{type['current']}** → **{latest['latest']}**\n\nmacOS **{latest['latest']}** was released on **{latest['posting']}**.  "
    f"It is a **{type['type']}** update and will require around **{type['time']}** minutes downtime.\n\nDays Remaining to Update: **{latest['days_Left']}**\n\n"
    f"To begin the update, click on **Update Now** and follow the provided steps.\n*You can also use the [Self Service app](jamfselfservice://content?entity=policy&id=97&action=view) to update at your convenience*.")
    write_log(str(latest['days_Left']))
    if latest['days_Left'] > 23:
        write_log("Still in grace period, exiting")
        sys.exit(0)
    if latest['days_Left'] <= 0:
        write_log("Update is past deadline")
        update = "required"
        finalDialog = DialogAlert(message + "\n\n**Notice: You have passed the deadline and this message will persist until you install the update and reboot**")
        finalDialog.content_dict["ontop"] = 1
        finalDialog.content_dict.pop("button2text")
        i = 0
    while latest['days_Left'] <= 0:
        write_log(f"Update attempt: {i}")
        run_Final = finalDialog.alert(finalDialog.content_dict)
    
    mainDialog = DialogAlert(message)
    run_Main = mainDialog.alert(mainDialog.content_dict)
    if run_Main == 2:
        write_log("user deferred")
    elif run_Main == 0:
        write_log("user opened update page")
    else:
        write_log(f"Dialog closed with exit code: {run_Main}")

main()