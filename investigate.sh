#!/bin/bash

# Check if the search term is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <search_term>"
    exit 1
fi

# Search term provided by the user
search_term=$1

# URLs with placeholders for the search term
url="https://gothamist.com/search?q={search_term}"

# Directory to save the search results pages
output_dir="search_results"
mkdir -p "$output_dir"

# Replace the placeholder with the search term
search_url=$(echo "$url" | sed "s/{search_term}/$search_term/g")
echo "Searching for '$search_term' using $search_url"

# Extract the domain name to use as the filename
domain=$(echo "$url" | awk -F[/:] '{print $4}')

# Fetch the search results page and save it to the output directory
curl -s "$search_url" -o "${output_dir}/${domain}_search_${search_term}.html"
echo "Fetched search results for '$search_term' from $search_url and saved as ${output_dir}/${domain}_search.html"
