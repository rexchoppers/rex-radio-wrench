update_radio() {
    # Validate HMAC is available
    validate_hmac
    
    choice=$(dialog --clear --stdout \
        --title "Update Radio Information" \
        --menu "Choose a parameter to update:" 15 50 5 \
        1 "Radio Name" \
        2 "Radio Description"
    )

    if [ -z "$choice" ]; then
        home
        return
    fi

    case $choice in
        1) update_config_field "name" "Radio Name" ;;
        2) update_config_field "description" "Radio Description" ;;
    esac

    home
}

# Function to generate HMAC signature for requests
generate_hmac_signature() {
    local method="$1"
    local path="$2"
    local body="$3"
    local timestamp="$4"
    
    # Create the message to sign
    local message="${method}${path}${body}${timestamp}"
    
    # Generate HMAC signature using the HMAC key
    echo -n "$message" | openssl dgst -sha512 -hmac "$HMAC" -binary | base64
}

# Function to get current configuration value for a specific field
get_current_config() {
    local field="$1"
    validate_hmac
    
    local timestamp=$(date +%s)
    local signature=$(generate_hmac_signature "GET" "/config/$field" "" "$timestamp")

    # Output to file for debugging
    echo "Signature: $signature" > debug.txt
    echo "Timestamp: $timestamp" >> debug.txt
    echo "Field: $field" >> debug.txt
    echo "HMAC: $HMAC" >> debug.txt
    echo "Message: $message" >> debug.txt
    echo "Body: $body" >> debug.txt
    echo "HTTP Code: $http_code" >> debug.txt
    echo "Response: $response" >> debug.txt
    
    # Make GET request to fetch current config for specific field
    local response=$(curl -s -w "\n%{http_code}" \
        -H "x-signature: $signature" \
        -H "x-timestamp: $timestamp" \
        -H "Content-Type: application/json" \
        "http://host.docker.internal:8000/config/$field")

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -eq 200 ]; then
        echo "$body"
    elif [ "$http_code" -eq 400 ]; then
        dialog --clear --stdout \
            --title "Error" \
            --msgbox "Configuration field '$field' not found." 8 50
        return 1
    else
        dialog --clear --stdout \
            --title "Error" \
            --msgbox "Failed to fetch configuration. HTTP $http_code" 8 50
        return 1
    fi
}

# Generic function to update any configuration field
update_config_field() {
    local field="$1"
    local field_display_name="$2"
    validate_hmac
    
    # Get current configuration for the specified field
    local current_config=$(get_current_config "$field")
    
    exit 0
    
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    

    # Extract current value from the response
    local current_value=$(echo "$current_config" | jq -r '.value // ""')
    
    # Show input dialog with current value
    local new_value=$(dialog --clear --stdout \
        --title "Update $field_display_name" \
        --inputbox "Enter new $field_display_name:" 10 50 "$current_value")
    
    if [ $? -ne 0 ]; then
        # User cancelled
        return 0
    fi
    
    if [ -z "$new_value" ]; then
        dialog --clear --stdout \
            --title "Error" \
            --msgbox "$field_display_name cannot be empty." 8 40
        return 1
    fi
    
    # Prepare PATCH data
    local patch_data="[{\"field\": \"$field\", \"value\": \"$new_value\"}]"
    
    # Generate HMAC signature for PATCH request
    local timestamp=$(date +%s)
    local signature=$(generate_hmac_signature "PATCH" "/config" "$patch_data" "$timestamp")
    
    # Make PATCH request
    local response=$(curl -s -w "\n%{http_code}" \
        -X PATCH \
        -H "x-signature: $signature" \
        -H "x-timestamp: $timestamp" \
        -H "Content-Type: application/json" \
        -d "$patch_data" \
        "http://host.docker.internal:8000/config")
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -eq 200 ]; then
        dialog --clear --stdout \
            --title "Success" \
            --msgbox "$field_display_name updated successfully!" 8 40
    else
        dialog --clear --stdout \
            --title "Error" \
            --msgbox "Failed to update $field_display_name. HTTP $http_code\nResponse: $body" 10 60
    fi
}

