from automatize import Browser

browser = Browser()
browser.open("https://duckduckgo.com/", is_javascript=True)
browser.follow_link("html/")

browser.select_form('#search_form_homepage')
browser["q"] = "automatize cleitonleonel"
browser.submit(is_javascript=True)

browser.get_current_form().form_summary()

browser.page_wiew()
