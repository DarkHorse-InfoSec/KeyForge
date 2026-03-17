"""API detection patterns and code analysis utilities for KeyForge."""

import re
from pathlib import Path
from typing import List, Dict

# API Detection Patterns
API_PATTERNS = {
    "openai": {
        "name": "OpenAI",
        "category": "AI/ML",
        "patterns": [
            r"import\s+openai",
            r"from\s+openai",
            r"openai\.api_key",
            r"OPENAI_API_KEY",
            r"gpt-3\.5|gpt-4",
            r"text-davinci|text-curie",
            r"OpenAI\("
        ],
        "files": [".py", ".js", ".ts", ".jsx", ".tsx"],
        "auth_type": "api_key",
        "scopes": ["completions", "chat", "embeddings", "fine-tuning"]
    },
    "stripe": {
        "name": "Stripe",
        "category": "Payments",
        "patterns": [
            r"import\s+stripe",
            r"from\s+stripe",
            r"stripe\.api_key",
            r"STRIPE_SECRET_KEY|STRIPE_PUBLISHABLE_KEY",
            r"stripe\.Customer|stripe\.PaymentIntent",
            r"sk_test_|pk_test_|sk_live_|pk_live_"
        ],
        "files": [".py", ".js", ".ts", ".jsx", ".tsx"],
        "auth_type": "api_key",
        "scopes": ["payments", "customers", "subscriptions", "webhooks"]
    },
    "github": {
        "name": "GitHub",
        "category": "Authentication",
        "patterns": [
            r"github\.com/login/oauth",
            r"GITHUB_CLIENT_ID|GITHUB_CLIENT_SECRET",
            r"github\.com/apps",
            r"octokit",
            r"@octokit/rest",
            r"github-api"
        ],
        "files": [".py", ".js", ".ts", ".jsx", ".tsx", ".yml", ".yaml"],
        "auth_type": "oauth",
        "scopes": ["user", "repo", "admin:org", "notifications"]
    },
    "supabase": {
        "name": "Supabase",
        "category": "Backend",
        "patterns": [
            r"@supabase/supabase-js",
            r"createClient",
            r"SUPABASE_URL|SUPABASE_ANON_KEY",
            r"supabase\.from\("
        ],
        "files": [".js", ".ts", ".jsx", ".tsx"],
        "auth_type": "api_key",
        "scopes": ["database", "auth", "storage", "edge_functions"]
    },
    "firebase": {
        "name": "Firebase",
        "category": "Backend",
        "patterns": [
            r"firebase/app",
            r"firebase/firestore",
            r"FIREBASE_CONFIG",
            r"initializeApp",
            r"getFirestore"
        ],
        "files": [".js", ".ts", ".jsx", ".tsx"],
        "auth_type": "config",
        "scopes": ["firestore", "auth", "storage", "functions"]
    },
    "vercel": {
        "name": "Vercel",
        "category": "Deployment",
        "patterns": [
            r"vercel\.json",
            r"VERCEL_TOKEN",
            r"@vercel/node"
        ],
        "files": [".json", ".js", ".ts"],
        "auth_type": "token",
        "scopes": ["deployments", "projects", "teams"]
    }
}


def analyze_code_content(content: str, filename: str) -> List[Dict]:
    """Analyze file content for API patterns"""
    detected = []

    for api_id, api_config in API_PATTERNS.items():
        # Check if file extension matches
        file_ext = Path(filename).suffix
        if file_ext not in api_config["files"]:
            continue

        matches = []
        for pattern in api_config["patterns"]:
            if re.search(pattern, content, re.IGNORECASE):
                matches.append(pattern)

        if matches:
            confidence = min(len(matches) * 0.3, 1.0)  # Cap at 100%
            detected.append({
                "api_id": api_id,
                "name": api_config["name"],
                "category": api_config["category"],
                "auth_type": api_config["auth_type"],
                "scopes": api_config["scopes"],
                "confidence": confidence,
                "matched_patterns": matches[:3],  # Show top 3 matches
                "file": filename
            })

    return detected
