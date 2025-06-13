#!/usr/bin/env python
import requests
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

# instantiate an MCP server client
mcp = FastMCP("C3SE", host="0.0.0.0", port=8395)

@mcp.tool()
def get_vera_intro() -> str:
    """Return the introduction of Vera"""
    url = 'https://www.c3se.chalmers.se/documentation/first_time_users/intro-vera/slides/'
    response = requests.get(url)
    response.raise_for_status()  # Raise an error if request fails

    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract main content (MkDocs Material uses <main id="main"> by default)
    main_content = soup.find('main')
    text = ""
    if main_content:
        text = main_content.get_text(separator='\n', strip=True)
    return text

# DEFINE RESOURCES

# Provide static resource content
@mcp.resource("c3se://news")
def get_c3se_news() -> str:
    """Return the news from c3se"""
    url = 'https://www.c3se.chalmers.se/#news'
    response = requests.get(url)
    response.raise_for_status()  # Raise an error if request fails

    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract main content (MkDocs Material uses <main id="main"> by default)
    main_content = soup.find('article')
    text = ""
    if main_content:
        text = main_content.get_text(separator='\n', strip=True)
    return text


def main():
    """Main function to run the server."""
    import argparse
    parser = argparse.ArgumentParser(description="Run the C3SE server.")
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        help="Transport method to use (stdio or sse). Default is stdio.",
    )
    args = parser.parse_args()
    # Check if the transport argument is provided
    if args.transport == "stdio":
        print("Launching the server with stdio transport...")
        mcp.run(transport=args.transport)
    elif args.transport == "sse":
        print("Launching the server with SSE transport...")
        mcp.run(transport=args.transport)
    else:
        print(f"Unknown transport method: {args.transport}. Defaulting to stdio.")
        mcp.run(transport="stdio")

# execute and return the stdio output
if __name__ == "__main__":
    main()    
