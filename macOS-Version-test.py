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

def write_log(text):
    """logger for depnotify"""
    NSLog("[mdm-switch] " + str(text))

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

def update_Online():
    URL = "https://gdmf.apple.com/v2/pmv"
    r = requests.get(URL, verify=False)
    list = r.json()
    # get first listing on version 12
    for i in (list["PublicAssetSets"]["macOS"]):
        if i["ProductVersion"].startswith("13"):
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
    
print (update_Online())