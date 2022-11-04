#!/bin/bash 
# this function is Bash compatible, insert the function in your script and then place dialogCheck where you want it to be executed

function pythonCheck(){
  # Get the URL of the latest PKG From the Dialog GitHub repo
      downloadURL=$(curl --silent --fail "https://api.github.com/repos/macadmins/python/releases/latest" | awk -F '"' "/browser_download_url/ && /python_recommended_signed/ { print \$4; exit }")
  # Expected Team ID of the downloaded PKG
  expectedDialogTeamID="9GQZ7KUFR6"

  # Check for Dialog and install if not found
  if [ ! -e "/Library/ManagedFrameworks/Python/Python3.framework/Versions/Current/bin/python3" ]; then
    echo "Python not found. Installing..."
    # Create temporary working directory
    workDirectory=$( /usr/bin/basename "$0" )
    tempDirectory=$( /usr/bin/mktemp -d "/private/tmp/$workDirectory.XXXXXX" )
    # Download the installer package
    /usr/bin/curl --location --silent "$downloadURL" -o "$tempDirectory/Python.pkg"
    # Verify the download
    teamID=$(/usr/sbin/spctl -a -vv -t install "$tempDirectory/Python.pkg" 2>&1 | awk '/origin=/ {print $NF }' | tr -d '()')
    # Install the package if Team ID validates
    if [ "$expectedDialogTeamID" = "$teamID" ] || [ "$expectedDialogTeamID" = "" ]; then
      /usr/sbin/installer -pkg "$tempDirectory/Python.pkg" -target /
    else
      echo "Dialog Team ID verification failed."
      exit 1
    fi
    # Remove the temporary working directory when done
    /bin/rm -Rf "$tempDirectory"  
  else echo "Python found. Proceeding..."
  fi
}

pythonCheck