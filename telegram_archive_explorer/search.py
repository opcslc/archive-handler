"""
Search functionality for stored data.

This module provides search capabilities for the stored data, allowing
users to search by URL, email, username, or password with advanced pattern matching.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import csv
import json
from datetime import datetime

from sqlalchemy import or_, and_, not_, func, select
from sqlalchemy.orm import Session, joinedload

from .database import URL, Credential, Source, db
from .logging_setup import stats

logger = logging.getLogger(__name__)

class SearchResult:
    """Class representing search results with formatting options."""
    
    def __init__(self, results: List[Dict[str, Any]], query: str, search_type: str, 
                 total_count: Optional[int] = None, page: Optional[int] = None, 
                 page_size: Optional[int] = None):
        """
        Initialize search results.
        
        Args:
            results: List of result dictionaries
            query: Original search query
            search_type: Type of search performed
            total_count: Total number of results (before pagination)
            page: Current page number (1-based)
            page_size: Number of results per page
        """
        self.results = results
        self.query = query
        self.search_type = search_type
        self.total_count = total_count or len(results)
        self.page = page
        self.page_size = page_size
        self.total_pages = (self.total_count + (page_size - 1)) // page_size if page_size else 1
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert search results to a dictionary.
        
        Returns:
            Dictionary representation of search results including pagination info
        """
        result = {
            "query": self.query,
            "search_type": self.search_type,
            "total_count": self.total_count,
            "results": self.results
        }
        
        if self.page is not None:
            result.update({
                "page": self.page,
                "page_size": self.page_size,
                "total_pages": self.total_pages,
                "has_next": self.page < self.total_pages,
                "has_previous": self.page > 1
            })
        
        return result
    
    def to_json(self, pretty: bool = False) -> str:
        """
        Convert search results to JSON.
        
        Args:
            pretty: Whether to format the JSON for readability
            
        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(self.to_dict(), indent=2, default=str)
        return json.dumps(self.to_dict(), default=str)
    
    def to_csv(self) -> str:
        """
        Convert search results to CSV.
        
        Returns:
            CSV string
        """
        if not self.results:
            return ""
            
        output = []
        
        # Get all possible fields from the results
        fieldnames = set()
        for result in self.results:
            fieldnames.update(result.keys())
        
        fieldnames = sorted(list(fieldnames))
        
        # Write header and rows
        import io
        output_buffer = io.StringIO()
        writer = csv.DictWriter(output_buffer, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in self.results:
            writer.writerow(result)
            
        return output_buffer.getvalue()
    
    def to_table(self) -> str:
        """
        Format search results as a text table.
        
        Returns:
            Formatted table string
        """
        if not self.results:
            return "No results found."
            
        # Determine columns based on search type
        if self.search_type == "url":
            columns = ["url", "username", "email", "password", "source"]
        elif self.search_type in ["username", "email"]:
            columns = ["username", "email", "password", "url", "source"]
        elif self.search_type == "password":
            columns = ["password", "username", "email", "url", "source"]
        else:
            columns = ["url", "username", "email", "password", "source"]
        
        # Calculate column widths
        widths = {col: len(col) for col in columns}
        
        for result in self.results:
            for col in columns:
                if col in result and result[col]:
                    widths[col] = max(widths[col], min(len(str(result[col])), 50))
        
        # Format header
        header = " | ".join(col.ljust(widths[col]) for col in columns)
        separator = "-+-".join("-" * widths[col] for col in columns)
        
        # Format rows
        rows = []
        for result in self.results:
            row = " | ".join(
                str(result.get(col, "")).ljust(widths[col])[:widths[col]] 
                for col in columns
            )
            rows.append(row)
        
        # Assemble table
        table = [
            header,
            separator,
            *rows
        ]
        
        # Add pagination and total info
        summary = []
        summary.append(f"\nTotal results: {self.total_count}")
        if self.page is not None:
            summary.append(f"Page {self.page} of {self.total_pages}")
            if self.has_previous:
                summary.append("Use --page N to view other pages")
            if self.has_next:
                summary.append("Use --page N to view next pages")
        table.extend(summary)
        
        return "\n".join(table)
    
    def __str__(self) -> str:
        """
        String representation of search results.
        
        Returns:
            Formatted string
        """
        return self.to_table()

class SearchEngine:
    """Search engine for querying the database."""
    
    def __init__(self, session: Optional[Session] = None):
        """
        Initialize the search engine.
        
        Args:
            session: Optional database session.
                    If None, creates a new session.
        """
        self.session = session or db.get_session()
    
    def _pattern_to_sql(self, pattern: str) -> Tuple[str, List[Any]]:
        """
        Convert a wildcard pattern to SQL LIKE pattern and parameters.
        
        Args:
            pattern: Search pattern with wildcards (*)
            
        Returns:
            Tuple of (SQL condition string, parameters list)
        """
        if '*' in pattern:
            # Convert wildcard pattern to SQL LIKE pattern
            sql_pattern = pattern.replace('*', '%')
            return "LIKE ?", [sql_pattern]
        else:
            # Exact match
            return "= ?", [pattern]
    
    def _build_url_query(self, query: str, use_pattern: bool = True):
        """
        Build a query for searching URLs.
        
        Args:
            query: Search query
            use_pattern: Whether to treat query as a pattern
            
        Returns:
            SQLAlchemy query object
        """
        if use_pattern and '*' in query:
            # Wildcard search
            return URL.url.like(query.replace('*', '%'))
        else:
            # Exact match or partial match
            if not use_pattern:
                return URL.url == query
            else:
                return URL.url.contains(query)
    
    def _build_domain_query(self, query: str, use_pattern: bool = True):
        """
        Build a query for searching domains.
        
        Args:
            query: Search query
            use_pattern: Whether to treat query as a pattern
            
        Returns:
            SQLAlchemy query object
        """
        if use_pattern and '*' in query:
            # Wildcard search
            return URL.domain.like(query.replace('*', '%'))
        else:
            # Exact match or partial match
            if not use_pattern:
                return URL.domain == query
            else:
                return URL.domain.contains(query)
    
    def _build_username_query(self, query: str, use_pattern: bool = True):
        """
        Build a query for searching usernames.
        
        Args:
            query: Search query
            use_pattern: Whether to treat query as a pattern
            
        Returns:
            SQLAlchemy query object
        """
        if use_pattern and '*' in query:
            # Wildcard search
            return Credential.username.like(query.replace('*', '%'))
        else:
            # Exact match or partial match
            if not use_pattern:
                return Credential.username == query
            else:
                return Credential.username.contains(query)
    
    def _build_email_query(self, query: str, use_pattern: bool = True):
        """
        Build a query for searching emails.
        
        Args:
            query: Search query
            use_pattern: Whether to treat query as a pattern
            
        Returns:
            SQLAlchemy query object
        """
        if use_pattern and '*' in query:
            # Wildcard search
            return Credential.email.like(query.replace('*', '%'))
        else:
            # Exact match or partial match
            if not use_pattern:
                return Credential.email == query
            else:
                return Credential.email.contains(query)
    
    def _build_password_query(self, query: str, use_pattern: bool = True):
        """
        Build a query for searching passwords.
        
        Args:
            query: Search query
            use_pattern: Whether to treat query as a pattern
            
        Returns:
            SQLAlchemy query object
        """
        if use_pattern and '*' in query:
            # Wildcard search
            return Credential.password.like(query.replace('*', '%'))
        else:
            # Exact match or partial match
            if not use_pattern:
                return Credential.password == query
            else:
                return Credential.password.contains(query)
    
    def search_url(self, query: str, limit: int = 100, offset: int = 0, exact: bool = False) -> SearchResult:
        """
        Search for a URL pattern.
        
        Args:
            query: URL to search for (can include wildcards)
            limit: Maximum number of results to return
            offset: Offset for pagination
            exact: Whether to perform an exact match (no partial matching)
            
        Returns:
            SearchResult object
        """
        try:
            # Check if query is a domain search
            if query.startswith('domain:'):
                domain_query = query[7:]  # Remove 'domain:' prefix
                sql_query = self._build_domain_query(domain_query, not exact)
                search_type = "domain"
            else:
                sql_query = self._build_url_query(query, not exact)
                search_type = "url"
            
            # Execute query
            query_results = (
                self.session.query(URL)
                .filter(sql_query)
                .options(joinedload(URL.source), joinedload(URL.credentials))
                .limit(limit)
                .offset(offset)
                .all()
            )
            
            # Format results
            results = []
            for url in query_results:
                for credential in url.credentials:
                    results.append({
                        "url": url.url,
                        "domain": url.domain,
                        "username": credential.username,
                        "email": credential.email,
                        "password": credential.password,
                        "source": url.source.telegram_channel if url.source else None,
                        "collected_date": url.source.collected_date if url.source else None
                    })
                
                # If URL has no credentials, add just the URL
                if not url.credentials:
                    results.append({
                        "url": url.url,
                        "domain": url.domain,
                        "username": None,
                        "email": None,
                        "password": None,
                        "source": url.source.telegram_channel if url.source else None,
                        "collected_date": url.source.collected_date if url.source else None
                    })
            
            # Log the search
            logger.info(f"URL search for '{query}' returned {len(results)} results")
            stats.increment("searches_performed")
            
            return SearchResult(results, query, search_type)
            
        except Exception as e:
            logger.error(f"Error searching for URL '{query}': {e}")
            return SearchResult([], query, "url")
    
    def search_username(self, query: str, limit: int = 100, offset: int = 0, exact: bool = False) -> SearchResult:
        """
        Search for a username pattern.
        
        Args:
            query: Username to search for (can include wildcards)
            limit: Maximum number of results to return
            offset: Offset for pagination
            exact: Whether to perform an exact match (no partial matching)
            
        Returns:
            SearchResult object
        """
        try:
            sql_query = self._build_username_query(query, not exact)
            
            # Execute query
            query_results = (
                self.session.query(Credential)
                .filter(sql_query)
                .options(joinedload(Credential.source), joinedload(Credential.urls))
                .limit(limit)
                .offset(offset)
                .all()
            )
            
            # Format results
            results = []
            for credential in query_results:
                # Add a result for each URL associated with this credential
                if credential.urls:
                    for url in credential.urls:
                        results.append({
                            "username": credential.username,
                            "email": credential.email,
                            "password": credential.password,
                            "url": url.url,
                            "domain": url.domain,
                            "source": credential.source.telegram_channel if credential.source else None,
                            "collected_date": credential.source.collected_date if credential.source else None
                        })
                else:
                    # Credential with no URL
                    results.append({
                        "username": credential.username,
                        "email": credential.email,
                        "password": credential.password,
                        "url": None,
                        "domain": None,
                        "source": credential.source.telegram_channel if credential.source else None,
                        "collected_date": credential.source.collected_date if credential.source else None
                    })
            
            # Log the search
            logger.info(f"Username search for '{query}' returned {len(results)} results")
            stats.increment("searches_performed")
            
            return SearchResult(results, query, "username")
            
        except Exception as e:
            logger.error(f"Error searching for username '{query}': {e}")
            return SearchResult([], query, "username")
    
    def search_email(self, query: str, limit: int = 100, offset: int = 0, exact: bool = False) -> SearchResult:
        """
        Search for an email pattern.
        
        Args:
            query: Email to search for (can include wildcards)
            limit: Maximum number of results to return
            offset: Offset for pagination
            exact: Whether to perform an exact match (no partial matching)
            
        Returns:
            SearchResult object
        """
        try:
            sql_query = self._build_email_query(query, not exact)
            
            # Execute query
            query_results = (
                self.session.query(Credential)
                .filter(sql_query)
                .options(joinedload(Credential.source), joinedload(Credential.urls))
                .limit(limit)
                .offset(offset)
                .all()
            )
            
            # Format results
            results = []
            for credential in query_results:
                # Add a result for each URL associated with this credential
                if credential.urls:
                    for url in credential.urls:
                        results.append({
                            "email": credential.email,
                            "username": credential.username,
                            "password": credential.password,
                            "url": url.url,
                            "domain": url.domain,
                            "source": credential.source.telegram_channel if credential.source else None,
                            "collected_date": credential.source.collected_date if credential.source else None
                        })
                else:
                    # Credential with no URL
                    results.append({
                        "email": credential.email,
                        "username": credential.username,
                        "password": credential.password,
                        "url": None,
                        "domain": None,
                        "source": credential.source.telegram_channel if credential.source else None,
                        "collected_date": credential.source.collected_date if credential.source else None
                    })
            
            # Log the search
            logger.info(f"Email search for '{query}' returned {len(results)} results")
            stats.increment("searches_performed")
            
            return SearchResult(results, query, "email")
            
        except Exception as e:
            logger.error(f"Error searching for email '{query}': {e}")
            return SearchResult([], query, "email")
    
    def search_password(self, query: str, limit: int = 100, offset: int = 0, exact: bool = False) -> SearchResult:
        """
        Search for a password pattern.
        
        Args:
            query: Password to search for (can include wildcards)
            limit: Maximum number of results to return
            offset: Offset for pagination
            exact: Whether to perform an exact match (no partial matching)
            
        Returns:
            SearchResult object
        """
        try:
            sql_query = self._build_password_query(query, not exact)
            
            # Execute query
            query_results = (
                self.session.query(Credential)
                .filter(sql_query)
                .options(joinedload(Credential.source), joinedload(Credential.urls))
                .limit(limit)
                .offset(offset)
                .all()
            )
            
            # Format results
            results = []
            for credential in query_results:
                # Add a result for each URL associated with this credential
                if credential.urls:
                    for url in credential.urls:
                        results.append({
                            "password": credential.password,
                            "username": credential.username,
                            "email": credential.email,
                            "url": url.url,
                            "domain": url.domain,
                            "source": credential.source.telegram_channel if credential.source else None,
                            "collected_date": credential.source.collected_date if credential.source else None
                        })
                else:
                    # Credential with no URL
                    results.append({
                        "password": credential.password,
                        "username": credential.username,
                        "email": credential.email,
                        "url": None,
                        "domain": None,
                        "source": credential.source.telegram_channel if credential.source else None,
                        "collected_date": credential.source.collected_date if credential.source else None
                    })
            
            # Log the search
            logger.info(f"Password search for '{query}' returned {len(results)} results")
            stats.increment("searches_performed")
            
            return SearchResult(results, query, "password")
            
        except Exception as e:
            logger.error(f"Error searching for password '{query}': {e}")
            return SearchResult([], query, "password")
    
    def search(self, query: str, search_type: str = "all", limit: int = 100, 
               offset: int = 0, exact: bool = False) -> SearchResult:
        """
        Search for a pattern across all fields or a specific field.
        
        Args:
            query: Search query (can include wildcards)
            search_type: Type of search (url, username, email, password, or all)
            limit: Maximum number of results to return
            offset: Offset for pagination
            exact: Whether to perform an exact match (no partial matching)
            
        Returns:
            SearchResult object
        """
        search_type = search_type.lower()
        
        if search_type == "url" or (search_type == "all" and query.startswith('http')):
            return self.search_url(query, limit, offset, exact)
        elif search_type == "domain" or (search_type == "all" and query.startswith('domain:')):
            return self.search_url(query, limit, offset, exact)
        elif search_type == "username" or (search_type == "all" and not '@' in query and not query.startswith('http')):
            return self.search_username(query, limit, offset, exact)
        elif search_type == "email" or (search_type == "all" and '@' in query):
            return self.search_email(query, limit, offset, exact)
        elif search_type == "password":
            return self.search_password(query, limit, offset, exact)
        elif search_type == "all":
            # Search all fields and combine results
            url_results = self.search_url(query, limit, 0, exact)
            username_results = self.search_username(query, limit, 0, exact)
            email_results = self.search_email(query, limit, 0, exact)
            password_results = self.search_password(query, limit, 0, exact)
            
            # Combine and deduplicate results
            all_results = []
            seen = set()
            
            for result_set in [url_results, username_results, email_results, password_results]:
                for result in result_set.results:
                    # Create a key for deduplication
                    key = (
                        result.get('url', ''),
                        result.get('username', ''),
                        result.get('email', ''),
                        result.get('password', '')
                    )
                    
                    if key not in seen:
                        seen.add(key)
                        all_results.append(result)
            
            # Apply pagination
            paginated_results = all_results[offset:offset+limit]
            
            return SearchResult(paginated_results, query, "all")
        else:
            logger.error(f"Invalid search type: {search_type}")
            return SearchResult([], query, search_type)
    
    def close(self):
        """Close the database session."""
        self.session.close()
