import requests
import logging
import subprocess
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


def get_website_title(url):
    """Get the title of a website."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find("title").string.strip()
        return title
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred: {e}")
        return None

def is_snap_installed():
    """Check if Snap is installed on the system."""
    return subprocess.call(["which", "snap"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

def is_firefox_snap():
    """Check if Firefox is installed as a Snap package."""
    try:
        result = subprocess.run(["snap", "list", "firefox"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0 and "firefox" in result.stdout
    except FileNotFoundError:
        return False

def is_firefox_esr_installed():
    """Check if firefox-esr is installed on the system."""
    return subprocess.call(["which", "firefox-esr"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
