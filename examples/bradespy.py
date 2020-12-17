#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
import os
from automatize import Browser

try:
    from PIL import Image
except ImportError:
    import Image

URL_BASE = 'https://www.ib12.bradesco.com.br/'


class Authentication:

    def __init__(self):
        pass

    def login(self):
        pass

    def main(self):
        br = Browser()
        url = URL_BASE + 'ibpfsegundaviaboleto/segundaViaBoletoPesquisarLinhaDigitavel.do'

        br.open(url, is_javascript=True)

        forms = br.get_forms()

        br.select_form(nr=0)

        captcha_url = br.find_captcha()
        print(captcha_url)

        img_response = br.session.get(captcha_url)

        image = open_image(img_response)

        form = br.forms()

        text = input('Por favor digite os dados da imagem: ')

        form['continuar.x'] = 87
        form['continuar.y'] = 5
        form['jcaptcha_response'] = text
        image.close()

        print(form)

        # br.get_current_form().form_summary()

        br.submit(**form, is_javascript=True)
        # print(br.get_current_url())

        page = br.get_current_page()
        print(page.find('form'))

        # summary = br.get_current_form().form_summary()

        br.select_form(nr=0)

        captcha_url = br.find_captcha()
        print(captcha_url)

        img_response = br.session.get(captcha_url)

        image = open_image(img_response)
        image.close()

        text = input('Por favor digite os dados da imagem: ')

        br['cdTipoArquivo'] = 'IMG'
        br['jcaptcha_response'] = text

        os.remove('file.jpg')
        os.remove('imgCaptcha.jpg')


def open_image(image):
    open('imgCaptcha.jpg', 'wb').write(image.content)
    os.system('convert imgCaptcha.jpg -resize 300% file.jpg')
    img = Image.open('file.jpg')
    img.show()
    return img


if __name__ == '__main__':
    auth = Authentication()
    auth.main()
