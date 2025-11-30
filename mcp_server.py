"""
MCP Server with FastMCP - Custom Tools Server (HTTP/SSE)

This server exposes tools via the Model Context Protocol (MCP) over HTTP.
Tools can be used by any MCP-compatible client.

Includes Open Library API tools for book search and discovery.

Run with: python mcp_server.py
Server will be available at: http://localhost:8000/sse
"""

from mcp.server.fastmcp import FastMCP
from datetime import datetime
import httpx
from typing import Optional

# Create the FastMCP server with HTTP transport
mcp = FastMCP("Tools Server")

# ============ Open Library: Search Books ============
@mcp.tool()
def search_books(query: str, limit: int = 5, sort: str = "relevance") -> str:
    """
    Search for books on Open Library.

    Args:
        query: The search query (title, author, or general search term)
        limit: Maximum number of results to return (default: 5, max: 20)
        sort: Sort order - "relevance", "new" (newest), "old" (oldest), or "rating"

    Returns:
        A formatted list of books matching the search query
    """
    limit = min(max(1, limit), 20)  # Clamp between 1 and 20
    
    sort_param = ""
    if sort == "new":
        sort_param = "&sort=new"
    elif sort == "old":
        sort_param = "&sort=old"
    elif sort == "rating":
        sort_param = "&sort=rating"
    
    url = f"https://openlibrary.org/search.json?q={query}&limit={limit}{sort_param}"
    
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        num_found = data.get("num_found", 0)
        docs = data.get("docs", [])
        
        if not docs:
            return f"No books found for query: '{query}'"
        
        result = f"Found {num_found} books for '{query}'. Showing top {len(docs)}:\n\n"
        
        for i, book in enumerate(docs, 1):
            title = book.get("title", "Unknown Title")
            authors = ", ".join(book.get("author_name", ["Unknown Author"]))
            first_year = book.get("first_publish_year", "N/A")
            edition_count = book.get("edition_count", 0)
            key = book.get("key", "")
            
            # Get cover URL if available
            cover_id = book.get("cover_i")
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else "No cover"
            
            result += f"{i}. **{title}**\n"
            result += f"   Author(s): {authors}\n"
            result += f"   First Published: {first_year}\n"
            result += f"   Editions: {edition_count}\n"
            result += f"   Open Library: https://openlibrary.org{key}\n"
            result += f"   Cover: {cover_url}\n\n"
        
        return result
        
    except httpx.TimeoutException:
        return f"Error: Request timed out while searching for '{query}'"
    except Exception as e:
        return f"Error searching for books: {str(e)}"


# ============ Open Library: Search Authors ============
@mcp.tool()
def search_authors(query: str, limit: int = 5) -> str:
    """
    Search for authors on Open Library.

    Args:
        query: The author name to search for
        limit: Maximum number of results to return (default: 5, max: 20)

    Returns:
        A formatted list of authors matching the search query with their top works
    """
    limit = min(max(1, limit), 20)
    
    url = f"https://openlibrary.org/search/authors.json?q={query}&limit={limit}"
    
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        num_found = data.get("numFound", 0)
        docs = data.get("docs", [])
        
        if not docs:
            return f"No authors found for query: '{query}'"
        
        result = f"Found {num_found} authors for '{query}'. Showing top {len(docs)}:\n\n"
        
        for i, author in enumerate(docs, 1):
            name = author.get("name", "Unknown")
            key = author.get("key", "")
            birth_date = author.get("birth_date", "N/A")
            top_work = author.get("top_work", "N/A")
            work_count = author.get("work_count", 0)
            top_subjects = author.get("top_subjects", [])[:5]
            
            result += f"{i}. **{name}**\n"
            result += f"   Birth Date: {birth_date}\n"
            result += f"   Works: {work_count}\n"
            result += f"   Top Work: {top_work}\n"
            if top_subjects:
                result += f"   Subjects: {', '.join(top_subjects)}\n"
            result += f"   Open Library: https://openlibrary.org/authors/{key}\n"
            result += f"   Photo: https://covers.openlibrary.org/a/olid/{key}-M.jpg\n\n"
        
        return result
        
    except httpx.TimeoutException:
        return f"Error: Request timed out while searching for author '{query}'"
    except Exception as e:
        return f"Error searching for authors: {str(e)}"


# ============ Open Library: Browse by Subject ============
@mcp.tool()
def browse_subject(subject: str, limit: int = 5, ebooks_only: bool = False) -> str:
    """
    Browse books by subject/genre on Open Library.

    Args:
        subject: The subject to browse (e.g., "science_fiction", "romance", "mystery", 
                 "fantasy", "biography", "history", "love", "adventure")
        limit: Maximum number of books to return (default: 5, max: 20)
        ebooks_only: If True, only return books with available ebooks

    Returns:
        A formatted list of popular books in the given subject
    """
    limit = min(max(1, limit), 20)
    
    # Format subject for URL (replace spaces with underscores, lowercase)
    subject_formatted = subject.lower().replace(" ", "_")
    
    ebooks_param = "&ebooks=true" if ebooks_only else ""
    url = f"https://openlibrary.org/subjects/{subject_formatted}.json?limit={limit}{ebooks_param}&details=true"
    
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        subject_name = data.get("name", subject)
        work_count = data.get("work_count", 0)
        works = data.get("works", [])
        
        if not works:
            return f"No books found for subject: '{subject}'. Try subjects like: science_fiction, romance, mystery, fantasy, biography, history, love, adventure"
        
        result = f"📚 **{subject_name}** - {work_count} total works\n"
        result += f"Showing top {len(works)} books:\n\n"
        
        for i, work in enumerate(works, 1):
            title = work.get("title", "Unknown Title")
            authors = work.get("authors", [])
            author_names = ", ".join([a.get("name", "Unknown") for a in authors]) if authors else "Unknown Author"
            edition_count = work.get("edition_count", 0)
            key = work.get("key", "")
            has_fulltext = "✓ Available" if work.get("has_fulltext") else "✗ Not available"
            cover_id = work.get("cover_id")
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else "No cover"
            
            result += f"{i}. **{title}**\n"
            result += f"   Author(s): {author_names}\n"
            result += f"   Editions: {edition_count}\n"
            result += f"   Full text: {has_fulltext}\n"
            result += f"   Open Library: https://openlibrary.org{key}\n"
            result += f"   Cover: {cover_url}\n\n"
        
        # Add related subjects if available
        related_subjects = data.get("subjects", [])[:5]
        if related_subjects:
            result += "**Related Subjects:** "
            result += ", ".join([s.get("name", "") for s in related_subjects])
            result += "\n"
        
        # Add top authors in this subject if available
        top_authors = data.get("authors", [])[:3]
        if top_authors:
            result += "**Top Authors in this Subject:** "
            result += ", ".join([f"{a.get('name', '')} ({a.get('count', 0)} works)" for a in top_authors])
            result += "\n"
        
        return result
        
    except httpx.TimeoutException:
        return f"Error: Request timed out while browsing subject '{subject}'"
    except Exception as e:
        return f"Error browsing subject: {str(e)}"


# ============ Open Library: Get Author Works ============
@mcp.tool()
def get_author_works(author_id: str, limit: int = 10) -> str:
    """
    Get works by a specific author using their Open Library ID.

    Args:
        author_id: The Open Library author ID (e.g., "OL23919A" for J.K. Rowling)
        limit: Maximum number of works to return (default: 10, max: 50)

    Returns:
        A formatted list of works by the author
    """
    limit = min(max(1, limit), 50)
    
    # Clean up author_id if full path is provided
    if "/" in author_id:
        author_id = author_id.split("/")[-1]
    
    url = f"https://openlibrary.org/authors/{author_id}/works.json?limit={limit}"
    
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        entries = data.get("entries", [])
        
        if not entries:
            return f"No works found for author ID: '{author_id}'"
        
        result = f"Works by author {author_id}:\n\n"
        
        for i, work in enumerate(entries, 1):
            title = work.get("title", "Unknown Title")
            key = work.get("key", "")
            subjects = work.get("subjects", [])[:3]
            first_publish = work.get("first_publish_date", "N/A")
            
            # Get cover
            covers = work.get("covers", [])
            cover_url = f"https://covers.openlibrary.org/b/id/{covers[0]}-M.jpg" if covers else "No cover"
            
            result += f"{i}. **{title}**\n"
            result += f"   First Published: {first_publish}\n"
            if subjects:
                result += f"   Subjects: {', '.join(subjects)}\n"
            result += f"   Open Library: https://openlibrary.org{key}\n"
            result += f"   Cover: {cover_url}\n\n"
        
        return result
        
    except httpx.TimeoutException:
        return f"Error: Request timed out while fetching works for author '{author_id}'"
    except Exception as e:
        return f"Error getting author works: {str(e)}"


# ============ Open Library: Book Recommendations ============
@mcp.tool()
def recommend_books(interest: str, limit: int = 5) -> str:
    """
    Get book recommendations based on an interest, genre, or topic.
    This combines subject browsing with search to find popular and relevant books.

    Args:
        interest: The interest, genre, or topic (e.g., "artificial intelligence", 
                  "romantic comedy", "world war 2", "cooking", "self improvement")
        limit: Number of recommendations (default: 5, max: 10)

    Returns:
        Curated book recommendations with details
    """
    limit = min(max(1, limit), 10)
    
    # Try subject first, then fall back to search
    subject_formatted = interest.lower().replace(" ", "_")
    
    results = []
    
    # Try subject browsing
    try:
        subject_url = f"https://openlibrary.org/subjects/{subject_formatted}.json?limit={limit}"
        response = httpx.get(subject_url, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            works = data.get("works", [])
            for work in works:
                results.append({
                    "title": work.get("title", "Unknown"),
                    "authors": ", ".join([a.get("name", "Unknown") for a in work.get("authors", [])]),
                    "editions": work.get("edition_count", 0),
                    "key": work.get("key", ""),
                    "cover_id": work.get("cover_id"),
                    "has_fulltext": work.get("has_fulltext", False)
                })
    except:
        pass
    
    # If not enough results, supplement with search
    if len(results) < limit:
        try:
            search_url = f"https://openlibrary.org/search.json?q={interest}&limit={limit - len(results)}&sort=rating"
            response = httpx.get(search_url, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                for book in data.get("docs", []):
                    results.append({
                        "title": book.get("title", "Unknown"),
                        "authors": ", ".join(book.get("author_name", ["Unknown"])),
                        "editions": book.get("edition_count", 0),
                        "key": book.get("key", ""),
                        "cover_id": book.get("cover_i"),
                        "has_fulltext": book.get("has_fulltext", False),
                        "first_year": book.get("first_publish_year")
                    })
        except:
            pass
    
    if not results:
        return f"Sorry, I couldn't find recommendations for '{interest}'. Try different keywords like: science fiction, mystery, romance, history, biography, cooking, self-help"
    
    output = f"📖 **Book Recommendations for '{interest}'**\n\n"
    
    # Remove duplicates based on title
    seen_titles = set()
    unique_results = []
    for r in results:
        if r["title"].lower() not in seen_titles:
            seen_titles.add(r["title"].lower())
            unique_results.append(r)
    
    for i, book in enumerate(unique_results[:limit], 1):
        cover_url = f"https://covers.openlibrary.org/b/id/{book['cover_id']}-M.jpg" if book.get('cover_id') else "No cover"
        availability = "📗 Available online" if book.get("has_fulltext") else "📕 Print only"
        
        output += f"**{i}. {book['title']}**\n"
        output += f"   By: {book['authors']}\n"
        if book.get("first_year"):
            output += f"   Year: {book['first_year']}\n"
        output += f"   Editions: {book['editions']}\n"
        output += f"   Status: {availability}\n"
        output += f"   Link: https://openlibrary.org{book['key']}\n"
        output += f"   Cover: {cover_url}\n\n"
    
    output += "💡 **Tip:** Use search_books() for more specific searches, or browse_subject() to explore genres!"
    
    return output


# ============ Resource: Server Info ============
@mcp.resource("server://info")
def get_server_info() -> str:
    """Get information about this MCP server."""
    return """
# Tools Server

This MCP server provides the following tools:

## Open Library Book Tools
6. **search_books** - Search for books by title, author, or keyword
7. **search_authors** - Search for authors and see their works
8. **browse_subject** - Browse books by subject/genre (fantasy, romance, mystery, etc.)
9. **get_author_works** - Get all works by a specific author
10. **recommend_books** - Get book recommendations based on interests

Built with FastMCP and Python.
Powered by Open Library API (https://openlibrary.org)
"""


# ============ Prompt Template ============
@mcp.prompt()
def assistant_prompt() -> str:
    """A helpful assistant prompt that knows about available tools."""
    return """You are a helpful assistant with access to several tools:

## Book Discovery Tools (Open Library)
6. **Search Books**: Use search_books(query, limit, sort) to find books
7. **Search Authors**: Use search_authors(query, limit) to find authors
8. **Browse Subject**: Use browse_subject(subject, limit, ebooks_only) to explore genres
9. **Author Works**: Use get_author_works(author_id, limit) to get an author's bibliography
10. **Recommend Books**: Use recommend_books(interest, limit) for personalized recommendations

When users ask about books, reading recommendations, or authors, use the book tools.
Be helpful, accurate, and provide clear responses with relevant book details."""


if __name__ == "__main__":
    # Run the server with SSE transport over HTTP
    print("=" * 50)
    print("MCP Tools Server")
    print("=" * 50)
    print("Starting HTTP/SSE server...")
    print("Server URL: http://localhost:8000")
    print("SSE Endpoint: http://localhost:8000/sse")
    print("=" * 50)
    
    # Run with SSE transport (HTTP)
    mcp.run(transport="sse")
