
from playwright.sync_api import sync_playwright, expect

def verify_spotify_display(page):
    # Navigate to the app
    page.goto("http://localhost:3000")

    # We need to simulate a logged-in state or ensure the component renders.
    # Based on the component code:
    # if (!isLoggedIn) return <SpotifyLoginButton ... />

    # Since we can't easily fake next-auth login in a simple script without mocking,
    # we might see the login button.
    # However, the mute button is ONLY visible if logged in.

    # Let's check what we see.
    page.screenshot(path="verification/initial_load.png")

    # If we see the login button, we can't verify the mute button directly without mocking session.
    # But wait, we can try to mock the session in the page context if we were running component tests.
    # For e2e, we might be stuck unless we have a mock auth setup.

    # Let's see if we can use the 'mock' page mentioned in file list: app/client/mock/page.tsx
    # Maybe that exposes components in a testable state?

    try:
        page.goto("http://localhost:3000/client/mock")
        page.screenshot(path="verification/mock_page.png")
    except Exception as e:
        print(f"Mock page failed: {e}")

    # Alternatively, we can try to bypass auth if possible, or just check the code staticly (which we did).
    # But the instruction says "You must attempt to visually verify".

    # Let's try to navigate to a page that might render the footer if possible.
    # But SpotifyDisplay is used in... let's check where it is used.

    # Searching for usage of SpotifyDisplay
    # It is likely in the layout or a main page.

    # If we can't easily login, we will verify that the app builds and runs,
    # and maybe inspect the DOM of the login button which we CAN see.

    # Let's check the login button first.
    expect(page.get_by_role("button", name="Login with Spotify")).to_be_visible()

    # If we can't get to the mute button, we will document that limitation.

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_spotify_display(page)
        finally:
            browser.close()
