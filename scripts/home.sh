#!/bin/bash

# Global HMAC variable
HMAC=""

get_hmac() {
    while true; do
        HMAC=$(dialog --clear --stdout \
            --title "HMAC Configuration" \
            --inputbox "Enter your HMAC key:" 10 50)
        
        if [ $? -ne 0 ]; then
            clear
            exit 0
        fi
        
        if [ -z "$HMAC" ]; then
            dialog --clear --stdout \
                --title "Error" \
                --msgbox "HMAC cannot be empty. Please try again." 8 40
            continue
        fi
        
        if ! echo "$HMAC" | grep -qE '^[a-fA-F0-9]{32,}$'; then
            dialog --clear --stdout \
                --title "Error" \
                --msgbox "Invalid HMAC format. Please enter a valid HMAC key." 8 50
            continue
        fi
        
        break
    done
}

validate_hmac() {
    if [ -z "$HMAC" ]; then
        dialog --clear --stdout \
            --title "Error" \
            --msgbox "HMAC not configured. Please restart the application." 8 50
        exit 1
    fi
}

home() {
  choice=$(dialog --clear --stdout \
    --title "Rex Radio Wrench" \
    --menu "Choose an action:" 15 50 7 \
    1 "Update Radio Information" \
    2 "Presenters" \
    3 "Exit")

  case $choice in
    1) update_radio ;;
    2) presenters_menu ;;
    3) clear; exit ;;
  esac
}