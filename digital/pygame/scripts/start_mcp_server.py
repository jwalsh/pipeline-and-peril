#!/usr/bin/env python3
"""
Start the Pipeline & Peril MCP Server
"""

import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from integration.mcp_server import main

if __name__ == "__main__":
    print("Starting Pipeline & Peril MCP Server...")
    print("This server provides tools for interactive gameplay through Claude.")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)