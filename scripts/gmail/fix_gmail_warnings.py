#!/usr/bin/env python3
"""
Fix Gmail API warnings
"""

import warnings
import os

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
warnings.filterwarnings("ignore", message=".*file_cache is only supported with oauth2client.*")

# Set environment variable to fix cache issue
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

# Apply to googleapiclient
try:
    import googleapiclient.discovery_cache
    googleapiclient.discovery_cache.cache = None
except:
    pass

print("Gmail warnings suppressed")