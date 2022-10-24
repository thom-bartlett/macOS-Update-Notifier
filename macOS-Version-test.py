#!/Library/ManagedFrameworks/Python/Python3.framework/Versions/Current/bin/python3
import platform
from Foundation import NSLog
from packaging.version import Version

def write_log(text):
    """logger for depnotify"""
    NSLog("[mdm-switch] " + str(text))

def update_Type(latest):
    current_OS = platform.mac_ver()[0]
    write_log(f"Current OS is: {current_OS}")
    write_log(F"latest OS: {latest}")

    # Going to remove this check as I am using Jamf scoping to see if update appears locally
    # if not update_Check():
    #     write_log("New Update available on Apple website but not locally, exiting")
    #     sys.exit(0)
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
update_Type("13")