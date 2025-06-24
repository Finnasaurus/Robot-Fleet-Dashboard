"""
Robot Fleet Dashboard Version Information
"""

__version__ = "2.0.0"
__app_name__ = "Robot Fleet Dashboard"
__description__ = "A comprehensive monitoring dashboard for robot fleet management with real-time status updates, motor data visualization, and dynamic configuration"
__author__ = "Built in collaboration with Claude (Anthropic)"
__license__ = "MIT"

# Development Story
__development_note__ = """
This entire project was built as a personal experiment to test Claude's 
capabilities while creating something practical for my company. Every line 
of code, architecture decision, and feature was developed through 
human-AI collaboration.
"""

# Legacy compatibility
__legacy_name__ = "PingTo"  # Original project name for reference

# Version history
VERSION_HISTORY = {
    "1.x.x": "PingTo - Original ping-based monitoring system",
    "2.0.0": "Robot Fleet Dashboard - Complete rewrite with modern web interface, motor data, and dynamic configuration (Built with Claude)"
}

# API Version
API_VERSION = "v1"

# Build info
import datetime
BUILD_DATE = datetime.datetime.now().isoformat()

def get_version_info():
    """Get complete version information"""
    return {
        "version": __version__,
        "app_name": __app_name__,
        "description": __description__,
        "api_version": API_VERSION,
        "build_date": BUILD_DATE,
        "legacy_name": __legacy_name__,
        "development_note": __development_note__,
        "author": __author__
    }

def print_version():
    """Print version information"""
    info = get_version_info()
    print(f"{info['app_name']} v{info['version']}")
    print(f"{info['description']}")
    print(f"Author: {info['author']}")
    print(f"Built: {info['build_date']}")
    print(f"\nDevelopment Note:")
    print(info['development_note'])

if __name__ == "__main__":
    print_version()
