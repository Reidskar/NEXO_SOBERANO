"""
NEXO SOBERANO — OSINT MCP Servers Registry
Source: github.com/soxoj/awesome-osint-mcp-servers
These servers extend the NEXO AI agent with real-time OSINT capabilities.
The AI (via agente.py) can invoke these tools to enrich globe intelligence,
answer queries, and feed data back into the OmniGlobe layers.
"""

OSINT_MCP_SERVERS = [

    # ── SOCMINT ──────────────────────────────────────────────────────────────
    {
        "id": "maigret",
        "name": "Maigret",
        "category": "SOCMINT",
        "description": "Collect user account information from 3000+ public sources by username. "
                       "Cross-platform OSINT: social media, forums, leaks.",
        "github": "https://github.com/BurtTheCoder/mcp-maigret",
        "pricing": "open_source",
        "nexo_use": "Find social accounts of persons of interest in conflict/intelligence reports.",
        "globe_layer": "points",  # can add points to OmniGlobe when persons are geolocated
        "capabilities": ["username_search", "social_media_lookup", "profile_aggregation"],
    },
    {
        "id": "xquik",
        "name": "Xquik — X/Twitter OSINT",
        "category": "SOCMINT",
        "description": "X/Twitter OSINT platform: user lookup, follower extraction, engagement analysis, "
                       "geolocation from tweets, network mapping.",
        "github": "https://github.com/Xquik-dev/x-twitter-scraper",
        "pricing": "open_source_paid",
        "nexo_use": "Monitor geopolitical accounts, extract geotagged tweets, feed live ticker.",
        "globe_layer": "events",  # geotagged tweets -> event rings on globe
        "capabilities": ["user_lookup", "tweet_search", "follower_graph", "geo_tweets"],
    },
    {
        "id": "expose_team",
        "name": "Expose Team",
        "category": "SOCMINT",
        "description": "AI-powered OSINT at lightspeed. Entity resolution, cross-platform correlation.",
        "github": None,
        "pricing": "paid",
        "nexo_use": "Deep entity research for intelligence reports.",
        "globe_layer": None,
        "capabilities": ["entity_resolution", "cross_platform_osint"],
    },

    # ── NETWORK SCANNING ─────────────────────────────────────────────────────
    {
        "id": "shodan",
        "name": "Shodan",
        "category": "NETWORK_SCANNING",
        "description": "Query Shodan API and CVEDB for IP reconnaissance, banner grabbing, "
                       "DNS lookups, vulnerability scanning, exposure mapping.",
        "github": "https://github.com/BurtTheCoder/mcp-shodan",
        "pricing": "open_source_paid",
        "nexo_use": "Scan critical infrastructure IPs, find exposed SCADA/ICS systems, "
                    "map internet-exposed assets in conflict zones for OmniGlobe infra layer.",
        "globe_layer": "infrastructure",  # matches OmniGlobe infra points
        "capabilities": ["ip_lookup", "banner_grab", "cve_search", "dns_recon", "exposure_map"],
    },
    {
        "id": "zoomeye",
        "name": "ZoomEye",
        "category": "NETWORK_SCANNING",
        "description": "Network asset intelligence: query ZoomEye with dorks to discover "
                       "exposed devices, services, and vulnerabilities globally.",
        "github": "https://github.com/zoomeye-ai/mcp_zoomeye",
        "pricing": "open_source_paid",
        "nexo_use": "Discover internet-exposed military/industrial assets in monitored regions.",
        "globe_layer": "infrastructure",
        "capabilities": ["dork_search", "device_discovery", "geo_search", "vulnerability_scan"],
    },
    {
        "id": "dnstwist",
        "name": "DNSTwist",
        "category": "NETWORK_SCANNING",
        "description": "DNS fuzzing: detect typosquatting, phishing domains, brand impersonation. "
                       "Generates permutations and checks registration.",
        "github": "https://github.com/BurtTheCoder/mcp-dnstwist",
        "pricing": "open_source",
        "nexo_use": "Monitor elanarcocapital.com for impersonation/phishing domains.",
        "globe_layer": None,
        "capabilities": ["dns_fuzzing", "typosquatting_detection", "domain_monitoring"],
    },
    {
        "id": "contrastapi",
        "name": "ContrastAPI",
        "category": "NETWORK_SCANNING",
        "description": "Security intelligence server with 20 tools: domain recon, IP reputation, "
                       "CVE/EPSS lookup, threat scoring, passive DNS.",
        "github": "https://github.com/UPinar/contrastapi",
        "pricing": "open_source",
        "nexo_use": "Rapid threat assessment of domains/IPs appearing in intelligence feeds.",
        "globe_layer": None,
        "capabilities": ["domain_recon", "ip_reputation", "cve_lookup", "threat_score", "passive_dns"],
    },
    {
        "id": "osint_toolkit",
        "name": "OSINT Toolkit",
        "category": "NETWORK_SCANNING",
        "description": "Unified interface for OSINT reconnaissance with parallel execution: "
                       "whois, DNS, geolocation, social, breaches.",
        "github": None,
        "pricing": "open_source",
        "nexo_use": "Parallel OSINT on persons/domains surfacing in conflict intelligence.",
        "globe_layer": None,
        "capabilities": ["whois", "dns", "geolocation", "breach_check", "parallel_recon"],
    },

    # ── WEB SCRAPING ─────────────────────────────────────────────────────────
    {
        "id": "brightdata",
        "name": "Bright Data",
        "category": "WEB_SCRAPING",
        "description": "Real-time web search, scraping, and structured data extraction from 60+ sources: "
                       "Google Maps, LinkedIn, Amazon, social platforms.",
        "github": "https://github.com/brightdata/brightdata-mcp",
        "pricing": "open_source_paid",
        "nexo_use": "Scrape live geopolitical news, energy prices, shipping rates for dashboard.",
        "globe_layer": "events",
        "capabilities": ["web_search", "structured_extraction", "60_plus_sources", "real_time"],
    },
    {
        "id": "anysite",
        "name": "AnySite",
        "category": "WEB_SCRAPING",
        "description": "Structured data access to 115+ endpoints across 40+ platforms without API keys.",
        "github": None,
        "pricing": "paid",
        "nexo_use": "Extract structured shipping/aviation/market data for OmniGlobe feeds.",
        "globe_layer": "arcs",
        "capabilities": ["115_endpoints", "40_platforms", "no_api_key"],
    },

    # ── THREAT INTELLIGENCE ───────────────────────────────────────────────────
    {
        "id": "virustotal",
        "name": "VirusTotal",
        "category": "THREAT_INTELLIGENCE",
        "description": "Analyze URLs, file hashes, IPs, and domains. Detailed relationship mapping, "
                       "sandbox results, community votes, behavior analysis.",
        "github": "https://github.com/BurtTheCoder/mcp-virustotal",
        "pricing": "open_source",
        "nexo_use": "Assess malware threats, verify suspicious domains/IPs from SIGINT feeds.",
        "globe_layer": None,
        "capabilities": ["url_scan", "file_hash", "ip_analysis", "domain_reputation", "sandbox"],
    },
]

# ── HELPER FUNCTIONS ──────────────────────────────────────────────────────────

def get_by_category(category: str):
    return [s for s in OSINT_MCP_SERVERS if s["category"] == category]

def get_globe_servers(layer: str = None):
    """Return servers that can feed data into a specific OmniGlobe layer."""
    if layer:
        return [s for s in OSINT_MCP_SERVERS if s.get("globe_layer") == layer]
    return [s for s in OSINT_MCP_SERVERS if s.get("globe_layer")]

def get_free_servers():
    return [s for s in OSINT_MCP_SERVERS if s["pricing"] == "open_source"]

CATEGORIES = {
    "SOCMINT": "Social media & identity intelligence",
    "NETWORK_SCANNING": "Network reconnaissance & exposure mapping",
    "WEB_SCRAPING": "Structured data extraction from live web",
    "THREAT_INTELLIGENCE": "Malware, IOC, and threat analysis",
}

# ── MCP TOOL MANIFEST (for NEXO AI agent integration) ─────────────────────────
# Format compatible with Claude MCP tool definitions
MCP_TOOL_MANIFEST = [
    {
        "name": f"osint_{s['id']}",
        "description": f"[OSINT:{s['category']}] {s['description']} NEXO use: {s['nexo_use']}",
        "server_id": s["id"],
        "github": s.get("github"),
    }
    for s in OSINT_MCP_SERVERS if s.get("github")
]
