#!/bin/bash

API_BASE="http://host.docker.internal:8000"

presenters_menu() {
    validate_hmac

    while true; do
        local list_json
        list_json=$(presenters_list)
        if [ $? -ne 0 ]; then
            # If listing fails, still allow trying to add
            list_json="[]"
        fi

        # Build dialog menu options: existing presenter names first, then Add New at the bottom
        local options=()
        local idx=0
        local names
        names=$(echo "$list_json" | jq -r '.[].name' 2>/dev/null)
        while IFS= read -r name; do
            if [ -n "$name" ]; then
                options+=("$idx" "$name")
                idx=$((idx+1))
            fi
        done <<< "$names"
        # Add "Add New Presenter" option at the bottom
        options+=("add" "Add New Presenter")

        local choice
        choice=$(dialog --clear --stdout \
            --title "Presenters" \
            --menu "Select an action or presenter:" 20 60 15 \
            "${options[@]}")

        # Cancel/back
        if [ -z "$choice" ]; then
            return
        fi

        case "$choice" in
            add)
                presenter_add
                ;;
            *)
                # Get presenter name from list using the index
                local presenter_name
                presenter_name=$(echo "$list_json" | jq -r --argjson idx "$choice" '.[$idx].name // "Unknown"')
                # For now, no detail view. Could extend later.
                dialog --clear --stdout \
                    --title "Presenter" \
                    --msgbox "Selected presenter: $presenter_name" 8 40
                ;;
        esac
    done
}

presenters_list() {
    validate_hmac
    local path="/presenters"
    local method="GET"
    local body=""
    local timestamp=$(date +%s)
    local signature=$(generate_hmac_signature "$method" "$path" "$body" "$timestamp")

    local response
    response=$(curl -s -w "\n%{http_code}" \
        -H "x-signature: $signature" \
        -H "x-timestamp: $timestamp" \
        -H "Content-Type: application/json" \
        "$API_BASE$path")

    local http_code=$(echo "$response" | tail -n1)
    local resp_body=$(echo "$response" | head -n -1)

    if [ "$http_code" -eq 200 ]; then
        echo "$resp_body"
        return 0
    else
        dialog --clear --stdout \
            --title "Error" \
            --msgbox "Failed to fetch presenters. HTTP $http_code" 8 50
        return 1
    fi
}

presenter_add() {
    validate_hmac

    # Name input
    local name
    name=$(dialog --clear --stdout \
        --title "Add Presenter" \
        --inputbox "Enter presenter name:" 10 50 "")
    local ec=$?
    if [ $ec -ne 0 ]; then
        return 0
    fi
    if [ -z "$name" ]; then
        dialog --clear --stdout --title "Error" --msgbox "Name cannot be empty." 8 40
        return 1
    fi

    # Build schedules via loop
    local schedules_json="[]"
    while true; do
        local action
        action=$(dialog --clear --stdout \
            --title "Schedules" \
            --menu "Add schedule entries or finish:" 15 60 6 \
            1 "Add schedule" \
            2 "Finish")
        if [ -z "$action" ] || [ "$action" = "2" ]; then
            break
        fi

        # Day select
        local day
        day=$(dialog --clear --stdout \
            --title "Day" \
            --menu "Select day:" 15 40 8 \
            mon "monday" \
            tue "tuesday" \
            wed "wednesday" \
            thu "thursday" \
            fri "friday" \
            sat "saturday" \
            sun "sunday")
        if [ -z "$day" ]; then
            continue
        fi
        # Map short to full
        case "$day" in
            mon) day="monday";; tue) day="tuesday";; wed) day="wednesday";; thu) day="thursday";; fri) day="friday";; sat) day="saturday";; sun) day="sunday";;
        esac

        # Start time
        local start
        start=$(dialog --clear --stdout \
            --title "Start Time" \
            --inputbox "Enter start time (HH:MM):" 8 40 "09:00")
        if [ -z "$start" ]; then
            continue
        fi
        if ! echo "$start" | grep -Eq '^[0-2][0-9]:[0-5][0-9]$'; then
            dialog --clear --stdout --title "Error" --msgbox "Invalid start time format." 8 40
            continue
        fi
        # End time
        local end
        end=$(dialog --clear --stdout \
            --title "End Time" \
            --inputbox "Enter end time (HH:MM):" 8 40 "12:00")
        if [ -z "$end" ]; then
            continue
        fi
        if ! echo "$end" | grep -Eq '^[0-2][0-9]:[0-5][0-9]$'; then
            dialog --clear --stdout --title "Error" --msgbox "Invalid end time format." 8 40
            continue
        fi

        # Append entry using jq
        schedules_json=$(jq -c --arg day "$day" --arg start "$start" --arg end "$end" \
            '. + [{"day": $day, "start": $start, "end": $end}]' <<< "$schedules_json")
    done

    # Build request body
    local voice_id="nrD2uNU2IUYtedZegcGx"
    local model_id="eleven_multilingual_v2"
    local body_json
    body_json=$(jq -c --arg name "$name" --arg voice_id "$voice_id" --arg model_id "$model_id" \
        --argjson schedules "$schedules_json" \
        '{name: $name, voice_id: $voice_id, model_id: $model_id, schedules: $schedules}')

    # POST /presenters
    local path="/presenters"
    local method="POST"
    local timestamp=$(date +%s)
    local signature=$(generate_hmac_signature "$method" "$path" "$body_json" "$timestamp")

    local response
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "x-signature: $signature" \
        -H "x-timestamp: $timestamp" \
        -H "Content-Type: application/json" \
        -d "$body_json" \
        "$API_BASE$path")

    local http_code=$(echo "$response" | tail -n1)
    local resp_body=$(echo "$response" | head -n -1)

    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        dialog --clear --stdout --title "Success" --msgbox "Presenter added successfully." 8 50
    else
        dialog --clear --stdout --title "Error" --msgbox "Failed to add presenter. HTTP $http_code\n$resp_body" 12 70
    fi
}
