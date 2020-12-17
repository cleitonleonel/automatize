#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
import re
import bs4
import copy
import urllib
import requests
import tempfile
import webbrowser
from six.moves import urllib
from six import string_types
from bs4 import BeautifulSoup
from requests_html import HTMLSession


class ProxyRequests(object):
    def __init__(self):
        self.sockets = []
        self.acquire_sockets()
        self.proxies = self.mount_proxies()

    def acquire_sockets(self):
        r = requests.get('https://www.sslproxies.org/')
        matches = re.findall(r"<td>\d+.\d+.\d+.\d+</td><td>\d+</td>", r.text)
        revised = [m.replace('<td>', '') for m in matches]
        self.sockets = [s[:-5].replace('</td>', ':') for s in revised]

    def mount_proxies(self):
        current_socket = self.sockets.pop(0)
        proxies = {
            'http': 'http://' + current_socket,
            'https': 'https://' + current_socket
        }
        return proxies


class Form(object):

    def __init__(self, form):
        self.form = form
        self._submit_chosen = False
        self.attach = self.set_input
        self.input = self.set_input
        self.textarea = self.set_textarea

    def set_input(self, data):
        for (name, value) in data.items():
            i = self.form.find("input", {"name": name})
            if not i:
                return "No input field named " + name
            i["value"] = value

    def uncheck_all(self, name):
        for option in self.form.find_all("input", {"name": name}):
            if "checked" in option.attrs:
                del option.attrs["checked"]

    def check(self, data):
        for (name, value) in data.items():
            if not self.set_checkbox({name: value}, uncheck_other_boxes=False):
                continue
            if not self.set_radio({name: value}):
                continue
            return "No input checkbox/radio named " + name

    def set_checkbox(self, data, uncheck_other_boxes=True):
        for (name, value) in data.items():
            checkboxes = self.find_by_type("input", "checkbox", {'name': name})
            if not checkboxes:
                return "No input checkbox named " + name

            if uncheck_other_boxes:
                self.uncheck_all(name)

            if not isinstance(value, list) and not isinstance(value, tuple):
                value = (value,)

            for choice in value:
                choice_str = str(choice)
                for checkbox in checkboxes:
                    if checkbox.attrs.get("value", "on") == choice_str:
                        checkbox["checked"] = ""
                        break
                    elif choice is True:
                        checkbox["checked"] = ""
                        break
                    elif choice is False:
                        if "checked" in checkbox.attrs:
                            del checkbox.attrs["checked"]
                        break
                else:
                    return "No input checkbox named %s with choice %s" % (name, choice)

    def set_radio(self, data):
        for (name, value) in data.items():
            radios = self.find_by_type("input", "radio", {'name': name})
            if not radios:
                return "No input radio named " + name

            self.uncheck_all(name)

            for radio in radios:
                if radio.attrs.get("value", "on") == str(value):
                    radio["checked"] = ""
                    break
            else:
                return "No input radio named %s with choice %s" % (name, value)

    def set_textarea(self, data):
        for (name, value) in data.items():
            t = self.form.find("textarea", {"name": name})
            if not t:
                return "No textarea named " + name
            t.string = value

    def set_select(self, data):
        for (name, value) in data.items():
            select = self.form.find("select", {"name": name})
            if not select:
                return "No select named " + name

            for option in select.find_all("option"):
                if "selected" in option.attrs:
                    del option.attrs["selected"]

            if not isinstance(value, list) and not isinstance(value, tuple):
                value = (value,)
            elif "multiple" not in select.attrs:
                return "Cannot select multiple options!"

            for choice in value:
                option = select.find("option", {"value": choice})

                if not option:
                    option = select.find("option", string=choice)

                if not option:
                    return 'Option %s not found for select %s' % (choice, name)

                option.attrs["selected"] = "selected"

    def __setitem__(self, name, value):
        return self.set(name, value)

    def set(self, name, value, force=False):
        for func in ("checkbox", "radio", "input", "textarea", "select"):
            if not getattr(self, "set_" + func)({name: value}):
                return
        if force:
            self.update_form('text', name, value=value)
            return
        return "No valid element named " + name

    def choose_submit(self, submit):
        if self._submit_chosen:
            if submit is None:
                return
            else:
                raise Exception('Submit already chosen. Cannot change submit!')

        inps = (self.find_by_type("input", "submit", dict()) +
                self.form.find_all("button"))
        inps = [i for i in inps
                if i.get('type', '').lower() not in ('button', 'reset')]

        if submit is None and inps:
            submit = inps[0]

        found = False
        for inp in inps:
            if inp.has_attr('name') and inp['name'] == submit:
                if found:
                    return "Multiple submit elements match: {0}".format(submit)
                found = True
            elif inp == submit:
                if found:
                    del inp['name']
                found = True
            else:
                del inp['name']

        if not found and submit is not None:
            return "Specified submit element not found: {0}".format(submit)
        self._submit_chosen = True

    def find_by_type(self, tag_name, type_attr, attrs):
        attrs_dict = attrs.copy()
        attrs_dict['type'] = lambda x: x and x.lower() == type_attr
        return self.form.find_all(tag_name, attrs=attrs_dict)

    def update_form(self, type, name, value, **kwargs):
        old_input = self.form.find_all('input', {'name': name})
        for old in old_input:
            old.decompose()
        old_textarea = self.form.find_all('textarea', {'name': name})
        for old in old_textarea:
            old.decompose()
        update = BeautifulSoup("", "html.parser").new_tag('input')
        update['type'] = type
        update['name'] = name
        update['value'] = value
        for k, v in kwargs.items():
            update[k] = v
        self.form.append(update)
        return self.form

    def form_summary(self, ignore_hidden=False, expected=None):
        for input_tag in self.form.find_all(("input", "textarea", "select", "button")):
            if ignore_hidden:
                if input_tag['type'] != 'hidden' or input_tag['type'] == expected:
                    print(input_tag)
            else:
                input_copy = copy.copy(input_tag)
                for subtag in input_copy.find_all() + [input_copy]:
                    if subtag.string:
                        subtag.string = subtag.string.strip()
                print(input_copy)


class State(object):

    def __init__(self, page=None, url=None, form=None):
        self.page = page
        self.url = url
        self.form = form


class Browser(object):

    def __init__(self, session=None, args=None, **kwargs):
        super(Browser, self).__init__(**kwargs)

        browser_args = ["--no-sandbox", '--user-agent=Mozilla/5.0 (Windows NT 5.1; rv:7.0.1) Gecko/20100101 Firefox/7.0.1']

        if args:
            for key, value in args.items():
                command = f'{key}={value}'
                browser_args.append(command)

        self.soup_parser = {'features': 'html5lib'}
        self.session = session or requests.Session()
        self.js_session = HTMLSession(browser_args=browser_args)
        self.state = State()
        self.headers = self.get_headers()
        self.proxies = None
        self.response = None
        self.verify = None
        self.debug = False

    def debugging(self):
        return self.debug

    def forms(self):
        result_dict = {}
        return result_dict

    def get_current_form(self):
        return self.state.form

    def get_current_page(self):
        return self.state.page

    def form_upgrade(self, type, name, value, **kwargs):
        return self.get_current_form().update_form(type, name, value, **kwargs)

    def __setitem__(self, name, value):
        try:
            self.get_current_form()[name] = value
        except:
            return self.form_upgrade(type='input', name=name, value=value)

    def mount_forms(self, data):
        result_dict = {}
        for arg in data:
            result_dict[arg[0]] = arg[1]
        return result_dict

    def get_forms(self, page=None):
        if not page:
            page = self.state.page
        else:
            self.state.page = page
        soup = page
        forms = soup.find_all('form')
        if len(forms) > 1:
            self.state.form = Form(soup.find_all('form'))
        else:
            self.state.form = Form(soup.find('form'))
        return forms

    def select_form(self, selector="form", nr=0):
        if isinstance(selector, bs4.element.Tag):
            if selector.name != "form":
                return 'Error'
            self.state.form = Form(selector)
        else:
            found_forms = self.get_current_page().select(selector, limit=nr + 1)
            if len(found_forms) != nr + 1:
                return 'Error'
            self.state.form = Form(found_forms[-1])

        return self.get_current_form()

    def get_headers(self):
        headers = {
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36',
        }
        return headers

    def set_headers(self, **kwargs):
        self.headers = kwargs
        return self.headers

    def set_parser(self, parser):
        self.soup_parser = parser
        return self.soup_parser

    def get_proxies(self):
        proxies = self.proxies
        return proxies

    def set_proxies(self, **kwargs):
        if kwargs:
            self.proxies = kwargs
            return self.proxies
        else:
            self.proxies = ProxyRequests().proxies

    def set_enable_js(self):
        self.session = self.js_session

    def set_args_browser_html(self, *args):
        if args:
            parameter = args[0]
            self.js_session = HTMLSession(browser_args=parameter)

    def send_request(self, method, url, **kwargs):
        response = self.session.request(method, url, **kwargs)
        if response.status_code == 200:
            return response

        return None

    def open(self, url, referer=None, proxies=None, verify=None, is_javascript=False, **kwargs):
        if verify is not None:
            self.verify = verify

        if referer is not None:
            self.headers['referer'] = self.get_current_url() or referer

        if is_javascript:
            self.set_enable_js()
            response = self.send_request('GET', url)
            response.html.render()
            self.state.page = self.format_html(response.html.html)
            self.state.url = response.html.url
            return self.state.page
        else:
            response = self.send_request('GET', url, headers=self.headers, proxies=proxies, verify=verify, **kwargs)
            self.state.page = self.format_html(response.text)
            self.state.url = response.url
            return self.state.page

    def open_custom_page(self, page_text, url=None):
        self.state.page = self.format_html(page_text)
        self.state.url = url

    def format_html(self, response, soup_config=None):
        self.soup_parser = soup_config or self.soup_parser
        soup = BeautifulSoup(response, **self.soup_parser)
        return soup

    def page_wiew(self, page=None):
        if page is not None:
            html = page
        else:
            html = str(self.state.page)

        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
            url = 'file://' + f.name
            f.write(html)
        webbrowser.open(url)

    def submit(self, btn_name=None, update_state=True, is_javascript=False, script=None, **kwargs):
        referer = self.get_current_url()
        if btn_name:
            self.get_current_form().choose_submit(btn_name)
        if referer is not None:
            headers = self.get_headers()
            headers['referer'] = referer
        else:
            headers = self.get_headers()

        if kwargs:
            response_get = self.send_request('GET', self.state.url, headers=headers)
            self.state.form = self.format_form(response_get.text, kwargs)
            response = self.click(self.state.form, is_javascript=is_javascript, url=self.state.url, script=script)
        else:
            response = self.click(self.state.form, is_javascript=is_javascript, url=self.state.url, script=script)

        if update_state:
            if is_javascript:
                self.response = self.format_html(response.html)
            else:
                self.response = self.format_html(response.text)
            self.state.page = self.response
            self.state.url = response.url
        return self.response

    def click(self, form, is_javascript=False, url=None, script=None):
        if isinstance(form, Form):
            form = form.form
        response = self.send(form, url, is_javascript=is_javascript, script=script)
        return response

    def get_current_url(self):
        return self.state.url

    def absolute_url(self, url):
        if url.endswith('/'):
            url = url[:-1]
        return urllib.parse.urljoin(self.get_current_url(), url)

    def open_relative(self, url, is_js=False, *args, **kwargs):
        return self.open(self.absolute_url(url), is_javascript=is_js, *args, **kwargs)

    def find_link(self, url_regex=None, link_text=None, real_link=False, *args, **kwargs):
        all_links = self.get_current_page().find_all(
            'a', href=True, *args, **kwargs)

        if url_regex is not None:
            all_links = [a for a in all_links
                         if re.search(url_regex, a['href'])]
        if link_text is not None:
            all_links = [a for a in all_links
                         if a.text == link_text]
        elif len(all_links) == 0:
            link = self.get_current_page().find('form')['action']
            return {"href": link}

        links = all_links

        if len(links) == 0:
            return links
        else:
            if real_link:
                return links[0]['href']
            else:
                return links[0]

    def find_link_internal(self, link, args, kwargs):
        if hasattr(link, 'attrs') and 'href' in link.attrs:
            return link

        if link and 'url_regex' in kwargs:
            raise ValueError('link parameter cannot be treated as '
                             'url_regex because url_regex is already '
                             'present in keyword arguments')
        elif link:
            kwargs['url_regex'] = link

            return self.find_link(*args, **kwargs)

    def follow_link(self, link=None, *args, **kwargs):
        link = self.find_link_internal(link, args, kwargs)
        return self.open_relative(link['href'])

    def format_form(self, page, data):
        soup = self.format_html(page)
        form = soup.find('form')
        for field, value in data.items():
            i = form.find("input", {"name": field})
            if i:
                i["value"] = value
            else:
                form = self.form_upgrade(type='input', name=field, value=value)
        return form

    def find_captcha(self):
        form = self.get_current_form().form
        attrs = ['img', 'iframe']
        url_captcha = None
        for attr in attrs:
            if attr == 'img':
                start = None
                end = -1
            if attr == 'iframe':
                start = None
                end = 3
            captcha = form.find_all(attr)
            for query in captcha:
                if query and 'captcha' in str(query) or 'Captcha' in str(query) or 'capcha' in str(query) or 'Capcha' in str(query):
                    if query['src'].startswith('/'):
                        query = query['src'][1:]
                    else:
                        query = query['src']
                    url_captcha = '/'.join(self.state.url.split('/')[start:end]) + '/' + query
                    if attr == 'iframe':
                        response = self.session.get(url_captcha)
                        query = self.format_html(response.text).find('img')
                        url_captcha = '/'.join(self.state.url.split('/')[start:end]) + '/' + query['src']
        return url_captcha

    def send(self, form, url, is_javascript=False, script=None, **kwargs):
        method = str(form.get("method", "get"))
        action = form.get("action")
        parse_url = urllib.parse.urljoin(url, action)
        data = kwargs.pop("data", dict())
        files = kwargs.pop("files", dict())
        data = [(k, v) for k, v in data.items()]
        multipart = form.get("enctype", "") == "multipart/form-data"

        selector = ",".join("{}[name]".format(i) for i in
                            ("input", "button", "textarea", "select"))

        if parse_url != self.state.url:
            url = parse_url
        else:
            url = url
        if url:
            self.state.url = url

        for tag in form.select(selector):
            name = tag.get("name")

            if tag.has_attr('disabled'):
                continue

            if tag.name == "input":
                if tag.get("type", "").lower() in ("radio", "checkbox"):
                    if "checked" not in tag.attrs:
                        continue
                    value = tag.get("value", "on")
                else:
                    value = tag.get("value", "")

                if tag.get("type", "").lower() == "file" and multipart:
                    filename = value
                    if filename != "" and isinstance(filename, string_types):
                        content = open(filename, "rb")
                    else:
                        content = ""
                    files[name] = (filename, content)
                else:
                    data.append((name, value))

            elif tag.name == "button":
                if tag.get("type", "").lower() in ("button", "reset"):
                    continue
                else:
                    data.append((name, tag.get("value", "")))

            elif tag.name == "textarea":
                data.append((name, tag.text))

            elif tag.name == "select":
                options = tag.select("option")
                selected_values = [i.get("value", i.text) for i in options
                                   if "selected" in i.attrs]
                if "multiple" in tag.attrs:
                    for value in selected_values:
                        data.append((name, value))
                elif selected_values:
                    data.append((name, selected_values[-1]))
                elif options:
                    first_value = options[0].get("value", options[0].text)
                    data.append((name, first_value))
        if method.lower() == "get":
            kwargs["params"] = data
        else:
            kwargs["data"] = data

        if multipart and not files:
            class DictThatReturnsTrue(dict):
                def __bool__(self):
                    return True

                __nonzero__ = __bool__

            files = DictThatReturnsTrue()

        if self.debug:
            result_dict = {}
            result_dict['object'] = {}
            result_dict['object']['url'] = url
            result_dict['object']['form'] = kwargs
            self.debug = result_dict

        if is_javascript:
            self.set_enable_js()
            response = self.send_request(method=method, url=url, files=files, **kwargs)
            response.html.render(script=script, keep_page=True, timeout=0, reload=False)
            return response.html
        else:
            return self.send_request(method=method, url=url, files=files, **kwargs)
