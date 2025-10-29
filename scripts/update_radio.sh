update_radio() {
    # Validate HMAC is available
    validate_hmac
    
    choice=$(dialog --clear --stdout \
        --title "Update Radio Information" \
        --menu "Choose a parameter to update:" 15 50 6 \
        1 "Radio Name" \
        2 "Radio Description" \
        3 "Genres"
    )

    if [ -z "$choice" ]; then
        home
        return
    fi

    case $choice in
        1) update_config_field "name" "Radio Name" ;;
        2) update_config_field "description" "Radio Description" ;;
        3) update_config_field_array "genres" "Genres" ;;
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
    local message="${timestamp}${method}${path}${body}"
    
    # Generate HMAC signature using the HMAC key
    local signature
    signature=$(echo -n "$message" | openssl dgst -sha512 -hmac "$HMAC" -binary | base64 | tr -d '\n')

    echo "$signature"
}

# Function to get current configuration value for a specific field
get_current_config() {
    local field="$1"
    validate_hmac
    
    local timestamp=$(date +%s)
    local signature=$(generate_hmac_signature "GET" "/config/$field" "" "$timestamp")

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
        # Field doesn't exist, return empty value instead of erroring
        echo '{"field": "'$field'", "value": ""}'
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
        
    if [ $? -ne 0 ]; then
        return 1
    fi

    # Extract current value from the response
    local current_value=$(echo "$current_config" | jq -r '.value // ""')
    
    # Show input dialog with current value
    local dialog_result
    dialog_result=$(dialog --clear --stdout \
        --title "Update $field_display_name" \
        --inputbox "Enter new $field_display_name:" 10 50 "$current_value")
    local dialog_exit_code=$?
    
    # Check if user cancelled (exit code != 0)
    if [ $dialog_exit_code -ne 0 ]; then
        # User cancelled - go back to menu
        return 0
    fi
    
    # Check if user entered the same value as current (likely cancelled with pre-filled value)
    if [ "$dialog_result" = "$current_value" ]; then
        return 0
    fi
    
    # Check if user entered empty value
    if [ -z "$dialog_result" ]; then
        dialog --clear --stdout \
            --title "Error" \
            --msgbox "$field_display_name cannot be empty." 8 40
        return 1
    fi
    
    local new_value="$dialog_result"
    
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

# Function to update configuration field that contains an array (like genres)
update_config_field_array() {
    local field="$1"
    local field_display_name="$2"
    validate_hmac
    
    # Get current configuration for the specified field
    local current_config=$(get_current_config "$field")
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    # Extract current array values from the response
    local current_values=$(echo "$current_config" | jq -r '.value // []')
    
    # Define available genre options
    local genres=(
        "Rock" "Pop" "Jazz" "Classical" "Electronic" "Hip-Hop" "Country" 
        "R&B" "Blues" "Folk" "Reggae" "Punk" "Metal" "Indie" "Alternative"
        "Funk" "Soul" "Gospel" "Latin" "World" "Ambient" "Techno" "House"
        "Trance" "Drum & Bass" "Dubstep" "Trap" "Lo-Fi" "Experimental"
    )
    
    # Convert current values to a format for dialog checklist
    local selected_indices=()
    local genre_index=0
    
    # Create checklist options
    local checklist_options=()
    for genre in "${genres[@]}"; do
        # Check if this genre is currently selected
        local is_selected="off"
        if echo "$current_values" | jq -e --arg genre "$genre" '.[] | select(. == $genre)' >/dev/null 2>&1; then
            is_selected="on"
        fi
        
        checklist_options+=("$genre_index" "$genre" "$is_selected")
        ((genre_index++))
    done
    
    # Show multi-select dialog
    local selected_genres
    selected_genres=$(dialog --clear --stdout \
        --title "Select $field_display_name" \
        --checklist "Choose genres (use space to select/deselect):" 20 60 15 \
        "${checklist_options[@]}")
    
    local dialog_exit_code=$?
    
    # Check if user cancelled
    if [ $dialog_exit_code -ne 0 ]; then
        return 0
    fi
    
    # Convert selected indices to genre names
    local new_values="[]"
    if [ -n "$selected_genres" ]; then
        local selected_array="["
        local first=true
        for index in $selected_genres; do
            if [ "$first" = true ]; then
                first=false
            else
                selected_array+=","
            fi
            selected_array+="\"${genres[$index]}\""
        done
        selected_array+="]"
        new_values="$selected_array"
    fi
    
    # Prepare PATCH data for array
    local patch_data=$(jq -n --arg field "$field" --argjson value "$new_values" '[{"field": $field, "value": $value}]')
    
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

