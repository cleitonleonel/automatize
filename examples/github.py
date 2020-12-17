from __future__ import print_function
from automatize import Browser


browser = Browser()

browser.open("https://github.com", is_javascript=True)

browser.follow_link("login")
browser.select_form('#login form')

# print(browser.get_current_form().form)

browser["login"] = "cleitonleonel"
browser["password"] = "98651597a"

resp = browser.submit(is_javascript=True)

# browser.page_wiew()

# browser.get_current_form().form_summary()

page3 = browser.open("https://github.com/settings/profile")

browser.page_wiew()
