import time
import random

def human_delay(min_sec=4, max_sec=15):
    """Pause execution for a random amount of time to simulate human behavior."""
    time.sleep(random.uniform(min_sec, max_sec))

def random_mouse_move(page):
    """Simulate random mouse movements."""
    width = page.viewport_size["width"] if page.viewport_size else 1920
    height = page.viewport_size["height"] if page.viewport_size else 1080
    x = random.randint(0, width)
    y = random.randint(0, height)
    page.mouse.move(x, y)

def slow_scroll(page):
    """Scroll the page down slowly."""
    page.evaluate("window.scrollBy(0, window.innerHeight / 2);")
    human_delay(2, 4)