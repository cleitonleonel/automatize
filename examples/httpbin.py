from automatize import Browser

browser = Browser()
browser.open("http://httpbin.org/")

# print(browser.get_current_url())
browser.follow_link("forms")
# print(browser.get_current_url())
# print(browser.get_current_page())

browser.select_form('form[action="/post"]')
browser["custname"] = "Cleiton leonel"
browser["custtel"] = "+55 27 995772291"
browser["custemail"] = "cleiton.leonel@gmail.com"
browser["size"] = "medium"
browser["topping"] = "onion"
browser["topping"] = ("bacon", "cheese")
browser["comments"] = "Essa Pizza é muito saborosa :-)"

browser.page_wiew()

# browser.get_current_form().print_summary()

response = browser.submit()
print(response.text)
