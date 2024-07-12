#!/bin/bash

# List of URLs to curl
urls=(
    "https://apnews.com/"
    "https://www.aljazeera.com/"
    "https://www.reuters.com/"
    "https://gothamist.com/"
    "https://www.latimes.com/"
    "https://news.yahoo.com/"
)

# Directory to save the landing pages
output_dir="landing_pages"
mkdir -p "$output_dir"

# Loop through each URL and use curl to fetch the landing page
for url in "${urls[@]}"; do
    # Extract the domain name to use as the filename
    domain=$(echo "$url" | awk -F[/:] '{print $4}')
    # Fetch the landing page and save it to the output directory
    curl -s "$url" -o "${output_dir}/${domain}.html"
    echo "Fetched landing page from $url and saved as ${output_dir}/${domain}.html"
done

echo "All landing pages fetched successfully."
