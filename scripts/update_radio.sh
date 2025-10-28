update_radio() {
    # Validate HMAC is available
    validate_hmac
    
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

# Example function showing how to use HMAC for HTTP requests
update_radio_name() {
    # Validate HMAC is available
    validate_hmac
    
    # Example of using HMAC in HTTP request
    echo "Using HMAC: $HMAC"
    
    # Example curl command with HMAC header
    # curl -H "Authorization: Bearer $HMAC" \
    #      -H "Content-Type: application/json" \
    #      -X POST \
    #      -d '{"name":"new_radio_name"}' \
    #      "https://api.example.com/radio/update"
    
    dialog --clear --stdout \
        --title "Success" \
        --msgbox "Radio name update completed (example)" 8 40
}

