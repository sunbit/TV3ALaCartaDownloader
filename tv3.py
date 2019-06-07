# -*- coding: utf-8 -*-
import requests
from pyquery import PyQuery
import re
import sys
from sh import wget

BASE_URL = 'http://www.ccma.cat'
MAIN_URL = '{}/tv3/alacarta'.format(BASE_URL)
BROADCASTS_URL = '{}/programes'.format(MAIN_URL)
METADATA_URL = 'http://dinamics.ccma.cat/pvideo/media.jsp'


class Tv3Alacarta(object):
    def __init__(self):
        self.programes = []

    def get_broadcasts_list(self):
        data = requests.get(BROADCASTS_URL)
        pq = PyQuery(data.content)

        self.programes = [(a.attr('href'), a.text()) for a in pq('.R-abcProgrames li a').items()]

    def search_broadcast(self, name):
        regex = r'{}'.format(name.lower().replace(' ', '.*'))
        results = []

        for url, programa in self.programes:
            if re.search(regex, programa, re.IGNORECASE | re.UNICODE | re.DOTALL):
                results.append((url, programa))

        return results

    def get_episodes_list(self, url, items=15, page=1):
        if 'fitxa-programa' in url:
            broadcast_url = url.replace('fitxa-programa', 'fitxa-programa/ultims-programes')
        else:
            broadcast_url = url + 'ultims-programes/'
        data = requests.get(BASE_URL + broadcast_url, dict(items_pagina=items, pagina=page))
        pq = PyQuery(data.content)

        # episode_count = int(pq('.resultatsDades strong').text().strip())

        results = []
        for result in pq('.R-resultats .F-llistat-item .F-info'):
            ipq = PyQuery(result)
            url = ipq.find('h3 a').attr('href')
            title = ipq.find('h3 a').text()
            date = ipq.find('time').attr('datetime')
            entradeta = ipq.find('entradeta').text()
            video_code = re.search(r'\/(\d+)\/$', url).groups()[0]
            results.append(dict(
                title=title,
                entradeta=entradeta,
                video_code=video_code,
                date=date))

        return results

    def get_episode_metadata(self, code):
        data = requests.get(METADATA_URL, dict(media='video', version='0s', idint=code, profile='pc'))
        return data.json()

if __name__ == '__main__':
    tv3 = Tv3Alacarta()
    print
    print 'Carregant llista de programes ...'
    print
    tv3.get_broadcasts_list()
    programa = raw_input('Quin programa vols descarregar? ')
    results = tv3.search_broadcast(programa)

    print
    if not results:
        print "No s'han trobat programes que concordin amb \"{}\"".format(programa)
        sys.exit(1)

    for num, programa in enumerate(results, start=1):
        url, name = programa
        print u'{:>2} - {}'.format(num, name)
    print

    value = str(raw_input('Tria un programa [1]: ')).strip()
    selection = int(value) - 1 if value else 0
    selected_program = results[selection]

    selection = None
    page = 1
    all_episodes = []

    print
    print 'Buscant emisions ...'
    print

    while selection is None or selection == '+':
        episodes = tv3.get_episodes_list(selected_program[0], page=page)

        for num, episode in enumerate(episodes, start=1):
            print u'{:>2} - {} ({})'.format(len(all_episodes) + num, episode['title'], episode['date'])
        print

        all_episodes += episodes
        if page == 1:
            print 'Aquests són els primers 15 resultats, escriu + per obtenir una altra pàgina'
        print
        selection = str(raw_input('Tria un episodi [1]: ')).strip()
        if selection == '+':
            page += 1
        else:
            selection = int(selection) - 1 if selection else 0

    print
    print "Buscant vídeo de l'emissió"
    print

    selected_episode = all_episodes[selection]
    metadata = tv3.get_episode_metadata(selected_episode['video_code'])
    urls = metadata['media']['url']
    download_url = sorted(urls, key=lambda url: int(re.sub(r'\D', '', url['label'])))[-1]['file']

    def log(text):
        if '%' in text:
            print '\r' + text.rstrip('\n') + '     ',

    print
    print "Descarregant {title}".format(**selected_episode)
    print "URL: {}".format(download_url)
    print

    wget("-O", u"{} - {}.mp4".format(selected_program[1], selected_episode['title']).encode('utf-8'), download_url, _out=log, _err=log)
