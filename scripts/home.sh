#!/bin/bash

home() {
  choice=$(dialog --clear --stdout \
    --title "Rex Radio Wrench" \
    --menu "Choose an action:" 15 50 5 \
    1 "Update Radio Information")

  case $choice in
    1) update_radio ;;
    2) show_versions ;;
    3) clear; exit ;;
  esac
}