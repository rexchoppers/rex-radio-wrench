update_radio() {
    choice=$(dialog --clear --stdout \
        --title "Update Radio Information" \
        --menu "Choose a parameter to update:" 15 50 5 \
        1 "Radio Name"
    )

    if [ -z "$choice" ]; then
        home
        return
    fi

    case $choice in
        1) update_radio_name ;;
    esac

    home
}

