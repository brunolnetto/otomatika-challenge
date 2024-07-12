#!/bin/bash

# Check if the search term is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <search_term>"
    exit 1
fi

# Search term provided by the user
search_term=$1

# URLs with placeholders for the search term
urls=(
    "https://www.aljazeera.com/search/{search_term}"
    "https://www.reuters.com/site-search/?query={search_term}"
    "https://apnews.com/search?q={search_term}"
    "https://gothamist.com/search?q={search_term}"
    "https://www.latimes.com/search?q={search_term}"
    "https://search.yahoo.com/search?p={search_term}"
)

# Directory to save the search results pages
output_dir="search_results"
mkdir -p "$output_dir"

# Loop through each URL, replace the placeholder with the search term, and fetch the search results page
for url in "${urls[@]}"; do
    # Replace the placeholder with the search term
    search_url=$(echo "$url" | sed "s/{search_term_string}/$search_term/g")
    
    # Extract the domain name to use as the filename
    domain=$(echo "$url" | awk -F[/:] '{print $4}')
    
    # Fetch the search results page and save it to the output directory
    curl -s "$search_url" -o "${output_dir}/${domain}_search.html"
    echo "Fetched search results for '$search_term' from $search_url and saved as ${output_dir}/${domain}_search.html"
done

echo "All search results fetched successfully."
